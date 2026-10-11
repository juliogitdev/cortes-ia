"""Word timed ASS captions. All evidence times remain on the original video timeline."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import re
import tempfile
from typing import TYPE_CHECKING

from clip_platform.media.tools import MediaError, av_metadata, content_hash, run_tool, run_ffmpeg_progress
from clip_platform.shared.contracts import EvidenceBundle
from clip_platform.shared.jobs import Export
from clip_platform.speech.transcribe import _repetition_loop

if TYPE_CHECKING:
    from clip_platform.shared.contracts import SubtitleSettings


@dataclass(frozen=True)
class Caption:
    start_s: float  # local time inside the exported clip
    end_s: float
    words: tuple[str, ...]
    active_word: int
    timing_quality: str  # word or approximate


@dataclass(frozen=True)
class SubtitleRenderResult:
    export: Export
    local_path: str
    content_hash: str
    duration_s: float
    caption_count: int
    timing_quality: str


def _tokens(text: str) -> list[str]:
    return [word for word in re.split(r'\s+', text.strip()) if word]


def _timed_words(bundle: EvidenceBundle, start: float, end: float, word_overrides=None):
    if word_overrides is not None:
        output = []
        previous_end = start
        for entry in word_overrides:
            ws, we, token = float(entry['start_s']), float(entry['end_s']), str(entry['text']).strip()
            if (not token or not math.isfinite(ws) or not math.isfinite(we)
                    or ws < previous_end or ws < start or we > end or we - ws < .025):
                raise MediaError('Correção de legenda com horários inválidos')
            previous_end = we
            output.append((ws - start, we - start, token, 'word'))
        return output
    output = []
    for item in sorted(bundle.transcript, key=lambda item: item.start_s):
        if item.end_s <= start or item.start_s >= end:
            continue
        if _repetition_loop(item.observation):
            continue
        raw = item.provenance.settings.get('words')
        words = []
        if isinstance(raw, list):
            for entry in raw:
                if not isinstance(entry, dict):
                    continue
                try:
                    ws, we = float(entry['start_s']), float(entry['end_s'])
                    token = str(entry['text']).strip()
                except (KeyError, ValueError, TypeError):
                    continue
                if token and math.isfinite(ws) and math.isfinite(we) and item.start_s <= ws < we <= item.end_s:
                    words.append((ws, we, token, 'word'))
        if not words:
            if _tokens(item.observation):
                raise MediaError('Transcrição sem horários por palavra neste corte; reprocessar ou revisar a transcrição')
            continue
        for ws, we, token, quality in words:
            ws, we = max(ws, start), min(we, end)
            if we - ws >= .025:
                output.append((ws - start, we - start, token, quality))
    output.sort(key=lambda item: (item[0], item[1]))
    return output


def build_captions(bundle: EvidenceBundle, clip_start_s: float, clip_end_s: float,
                   max_words_per_line: int = 3, word_overrides=None,
                   time_map=None) -> list[Caption]:
    """Build stable two-line groups, changing the highlight at observed word times."""
    if not (math.isfinite(clip_start_s) and math.isfinite(clip_end_s)
            and 0 <= clip_start_s < clip_end_s):
        raise ValueError('Invalid clip interval')
    if not 2 <= max_words_per_line <= 6:
        raise ValueError('max_words_per_line must be between 2 and 6')
    words = _timed_words(bundle, clip_start_s, clip_end_s, word_overrides)
    if time_map is not None:
        mapped = []
        offset = 0.
        for keep_start, keep_end in time_map:
            for ws, we, token, quality in words:
                left, right = max(ws, keep_start), min(we, keep_end)
                if right - left >= .025:
                    mapped.append((offset + left - keep_start, offset + right - keep_start, token, quality))
            offset += keep_end - keep_start
        words = mapped
    output_duration = (sum(end - start for start, end in time_map) if time_map is not None
                       else clip_end_s - clip_start_s)
    captions: list[Caption] = []
    group_size = 2 * max_words_per_line
    for group_start in range(0, len(words), group_size):
        group = words[group_start:group_start + group_size]
        following_group_start = (words[group_start + group_size][0]
                                 if group_start + group_size < len(words) else None)
        texts = tuple(word[2] for word in group)
        for index, (ws, we, _text, quality) in enumerate(group):
            # Keep the words on screen through natural pauses but never overlap
            # the next highlight or the clip boundary.
            next_start = group[index + 1][0] if index + 1 < len(group) else None
            if next_start is not None:
                we = next_start
            else:
                we = min(output_duration, max(we, ws + .08))
                if following_group_start is not None:
                    we = min(we, following_group_start)
            if we - ws < .025:
                continue
            captions.append(Caption(ws, we, texts, index, quality))
    return captions


def _ass_time(seconds: float) -> str:
    centiseconds = round(max(0, seconds) * 100)
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, cs = divmod(remainder, 100)
    return f'{hours}:{minutes:02}:{secs:02}.{cs:02}'


def _safe_text(text: str) -> str:
    # Transcript is untrusted data, including ASS override syntax.
    text = ''.join(char if char.isprintable() else ' ' for char in text)
    return text.replace('\\', '＼').replace('{', '｛').replace('}', '｝')


def _ass_color(value: str) -> str:
    if not re.fullmatch(r'#[0-9A-Fa-f]{6}', value):
        raise ValueError('Cor de legenda inválida')
    red, green, blue = value[1:3], value[3:5], value[5:7]
    return f'&H00{blue}{green}{red}'.upper()


def _ass_document(captions: list[Caption], settings: SubtitleSettings) -> str:
    position = getattr(settings, 'position', 'bottom')
    alignment = 5 if position == 'middle' else 2
    scale = float(getattr(settings, 'font_scale', 1.0))
    font_size = max(58, min(132, round(90 * scale)))
    words_per_line = int(getattr(settings, 'max_words_per_line', 3))
    text_color = _ass_color(getattr(settings, 'text_color', '#FFFFFF'))
    highlight_color = _ass_color(getattr(settings, 'highlight_color', '#FFFF00'))
    outline_color = _ass_color(getattr(settings, 'outline_color', '#000000'))
    outline_width = int(getattr(settings, 'outline_width', 5))
    if not 0 <= outline_width <= 8:
        raise ValueError('Contorno fora da faixa')
    header = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
              "ScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\n"
              "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
              "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
              "Alignment, MarginL, MarginR, MarginV, Encoding\n"
              f"Style: Pop,Arial,{font_size},{text_color},{text_color},{outline_color},&H80000000,"
              f"1,0,0,0,100,100,0,0,1,{outline_width},3,{alignment},64,64,240,1\n\n"
              "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = [header]
    for caption in captions:
        display = []
        for index, word in enumerate(caption.words):
            safe = _safe_text(word)
            if index == caption.active_word:
                # A short elastic scale settles after the spoken word begins.
                safe = ('{\\c' + highlight_color + r'&\fscx125\fscy125\t(0,140,\fscx100\fscy100)}' +
                        safe + r'{\r}')
            display.append(safe)
        split = min(words_per_line, len(display))
        shown = ' '.join(display[:split])
        if len(display) > split:
            shown += r'\N' + ' '.join(display[split:])
        lines.append(f'Dialogue: 0,{_ass_time(caption.start_s)},{_ass_time(caption.end_s)},Pop,,0,0,0,,{shown}\n')
    return ''.join(lines)


def _filter_path(path: Path) -> str:
    # ffmpeg filtergraph parser consumes one escaping layer before libass.
    value = path.resolve().as_posix().replace('\\', '\\\\').replace(':', '\\:')
    value = value.replace("'", "\\'").replace(',', '\\,').replace(';', '\\;')
    return f"ass='{value}'"


def render_subtitled_clip(export: Export, evidence: EvidenceBundle, clip_start_s: float,
                          clip_end_s: float, settings: SubtitleSettings, destination_dir: Path,
                          progress_callback=None, word_overrides=None, device='cpu', time_map=None) -> SubtitleRenderResult:
    """Render a separately addressable MP4, preserving the base export and source evidence."""
    if device not in {'cpu', 'cuda'}:
        raise ValueError('Dispositivo de renderização inválido')
    source = Path(export.local_path).resolve(strict=True)
    if evidence.asset_id != export.asset_id:
        raise MediaError('Transcript belongs to another media asset')
    expected_duration = (sum(end - start for start, end in time_map) if time_map is not None
                         else clip_end_s - clip_start_s)
    if abs(expected_duration - export.duration_s) > .25:
        raise MediaError('Clip bounds do not match exported video duration')
    if not getattr(settings, 'enabled', False):
        return SubtitleRenderResult(export, str(source), export.content_hash, export.duration_s, 0, 'disabled')
    if getattr(settings, 'style', 'yellow_pop') != 'yellow_pop':
        raise ValueError('Unsupported subtitle style')
    if content_hash(source) != export.content_hash:
        raise MediaError('Base export hash mismatch')
    captions = build_captions(evidence, clip_start_s, clip_end_s,
                              int(getattr(settings, 'max_words_per_line', 3)), word_overrides, time_map)
    if not captions:
        raise MediaError('No speech in selected interval; cannot create synchronized subtitles')
    quality = 'word'
    ass = _ass_document(captions, settings)
    cache_input = f'v3|{device}|{export.content_hash}|{export.revision_id}|{clip_start_s}|{clip_end_s}|{ass}'
    key = hashlib.sha256(cache_input.encode('utf-8')).hexdigest()
    destination_dir = Path(destination_dir).resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / f'{key}.subtitled.mp4'
    manifest = target.with_suffix('.export.json')
    if target.exists() or manifest.exists():
        if not target.exists() or not manifest.exists():
            raise MediaError('Incomplete existing subtitle export')
        record = Export.model_validate_json(manifest.read_text(encoding='utf-8'))
        if record.export_id != 'export-subtitle-' + key or record.revision_id != export.revision_id or record.asset_id != export.asset_id:
            raise MediaError('Subtitle manifest mismatch')
        digest = content_hash(target)
        if digest != record.content_hash:
            raise MediaError('Subtitle output hash mismatch')
        return SubtitleRenderResult(record, str(target), digest, record.duration_s,
                                    len(captions), quality)
    fd, ass_name = tempfile.mkstemp(prefix='.subtitle-', suffix='.ass', dir=destination_dir)
    os.close(fd)
    fd, video_name = tempfile.mkstemp(prefix='.subtitle-', suffix='.mp4', dir=destination_dir)
    os.close(fd)
    ass_path, temporary = Path(ass_name), Path(video_name)
    try:
        ass_path.write_text(ass, encoding='utf-8-sig')
        command = ['-hide_banner', '-loglevel', 'error', '-nostdin', '-y']
        if device == 'cuda':
            command += ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
        command += ['-i', str(source),
                    '-vf', ('hwdownload,format=nv12,' if device == 'cuda' else '') + _filter_path(ass_path),
                    '-map', '0:v:0', '-map', '0:a?']
        if device == 'cuda':
            # libass draws glyphs in system memory; NVENC performs the expensive
            # video encode on the GPU after FFmpeg uploads those frames.
            command += ['-c:v', 'h264_nvenc', '-preset', 'p5', '-rc', 'vbr', '-cq', '18', '-b:v', '0']
        else:
            command += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p']
        command += ['-c:a', 'copy', '-movflags', '+faststart', str(temporary)]
        if progress_callback:
            run_ffmpeg_progress(command, export.duration_s, progress_callback, timeout=1800)
        else:
            run_tool('ffmpeg', command, timeout=1800)
        duration, _ = av_metadata(temporary)
        if abs(duration - export.duration_s) > .2:
            raise MediaError('Subtitled export duration differs from base clip')
        digest = content_hash(temporary)
        record = Export(export_id='export-subtitle-' + key, revision_id=export.revision_id,
                        asset_id=export.asset_id, local_path=str(target), duration_s=duration,
                        content_hash=digest)
        # Artifact first, then manifest. Partial publication remains visible to inspection.
        os.link(temporary, target)
        manifest.write_text(record.model_dump_json(indent=2), encoding='utf-8')
        return SubtitleRenderResult(record, str(target), digest, duration, len(captions), quality)
    finally:
        ass_path.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
