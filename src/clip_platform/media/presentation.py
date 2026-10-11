"""Compose a clip for a chosen screen ratio, silence policy and text watermark."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
from statistics import median

from clip_platform.media.tools import MediaError, av_metadata, content_hash, probe, run_ffmpeg_progress, run_tool, find_tool
from clip_platform.shared.contracts import VideoSettings
from clip_platform.shared.jobs import Export


def _kept_ranges(source: Path, duration: float, enabled: bool) -> list[tuple[float, float]]:
    if not enabled:
        return [(0., duration)]
    command = [find_tool('ffmpeg'), '-hide_banner', '-nostdin', '-i', str(source),
               '-af', 'silencedetect=noise=-35dB:d=0.8', '-f', 'null', '-']
    completed = subprocess.run(command, capture_output=True, text=True, timeout=max(120, duration * 3))
    if completed.returncode:
        raise MediaError('Não foi possível detectar silêncio no corte: ' + completed.stderr[-300:])
    intervals = []
    beginning = None
    for line in completed.stderr.splitlines():
        match = re.search(r'silence_start: ([0-9.]+)', line)
        if match:
            beginning = float(match.group(1))
        match = re.search(r'silence_end: ([0-9.]+)', line)
        if match and beginning is not None:
            intervals.append((max(0., beginning + .12), min(duration, float(match.group(1)) - .12)))
            beginning = None
    if beginning is not None:
        intervals.append((max(0., beginning + .12), duration))
    ranges = []
    cursor = 0.
    for start, end in intervals:
        if end <= start or start < cursor:
            continue
        if start - cursor >= .15:
            ranges.append((cursor, start))
        cursor = end
    if duration - cursor >= .15:
        ranges.append((cursor, duration))
    if not ranges:
        raise MediaError('Todo o corte foi classificado como silêncio; ajuste a seleção.')
    return ranges


def _has_centered_web_video(frame) -> bool:
    """Recognize a vertical web player bordered by a dark recommendation gutter."""
    import cv2
    height, width = frame.shape[:2]
    if width / height < 1.5:
        return False
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    center = gray[int(height * .2):int(height * .85), int(width * .33):int(width * .52)]
    gutter = gray[int(height * .2):int(height * .85), int(width * .60):int(width * .70)]
    return bool(center.std() > 35 and center.mean() > 40 and (gutter < 30).mean() > .94)


def _face_layout(source: Path, duration: float, width: int, height: int):
    """Sample YuNet face boxes; choose a close-up or two-person stack."""
    if width / height <= 9 / 16:
        return None
    try:
        import cv2
    except ImportError as exc:
        raise MediaError('Enquadramento automático exige opencv-python-headless.') from exc
    model_path = Path(__file__).resolve().parents[3] / 'models' / 'face_detection_yunet_2023mar.onnx'
    if not model_path.exists():
        return None  # preserve the entire frame when face evidence is unavailable
    detector = cv2.FaceDetectorYN.create(str(model_path), '', (width, height), score_threshold=.75)
    capture = cv2.VideoCapture(str(source))
    boxes = []
    focus = []
    pairs = samples = crowded = 0
    embedded_video = 0
    try:
        for second in range(0, min(int(duration) + 1, 90), 2):
            capture.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
            ok, frame = capture.read()
            if not ok:
                continue
            samples += 1
            detector.setInputSize((frame.shape[1], frame.shape[0]))
            _status, faces = detector.detect(frame)
            unique = [(round(float(face[0])), round(float(face[1])),
                       round(float(face[2])), round(float(face[3])))
                      for face in faces if face[2] >= width * .04 and face[3] >= height * .08] if faces is not None else []
            crowded += len(unique) >= 3
            if _has_centered_web_video(frame):
                embedded_video += 1
            left = [face for face in unique if face[0] + face[2] / 2 < width * .43]
            right = [face for face in unique if face[0] + face[2] / 2 > width * .57]
            if left and right:
                pairs += 1
            boxes.extend(unique)
            if unique:
                chosen = max(unique, key=lambda item: item[2] * item[3])
                focus.append((float(second), chosen[0] + chosen[2] / 2))
    finally:
        capture.release()
    # Screen recordings can contain several faces inside a video being watched.
    # When a vertical player is visible, crop that player rather than the page UI.
    # Otherwise keep the whole source visible instead of chasing a random face.
    if embedded_video >= max(3, samples // 2):
        crop_width = round(width * .27) // 2 * 2
        crop_height = round(crop_width * 16 / 9) // 2 * 2
        x = max(0, min(width - crop_width, round(width * .283)))
        y = max(0, min(height - crop_height, round(height * .1)))
        return ('web_player', x, y, crop_width, crop_height)
    if len(boxes) < 2:
        return None
    if crowded >= max(2, samples // 5):
        return None
    left_faces = [face for face in boxes if face[0] + face[2] / 2 < width * .43]
    right_faces = [face for face in boxes if face[0] + face[2] / 2 > width * .57]
    if pairs >= max(2, int(samples * .7)) and len(left_faces) >= 2 and len(right_faces) >= 2:
        crop_w = min(width, int(height * .7)) // 2 * 2
        crop_h = round(crop_w * 8 / 9) // 2 * 2
        panels = []
        for faces in (left_faces, right_faces):
            face_x = median(face[0] + face[2] / 2 for face in faces)
            face_y = median(face[1] + face[3] / 2 for face in faces)
            x = max(0, min(width - crop_w, round(face_x - crop_w / 2)))
            y = max(0, min(height - crop_h, round(face_y - crop_h * .32)))
            panels.append((x, y, crop_w, crop_h))
        return ('pair', panels)
    crop_width = int(height * 9 / 16) // 2 * 2
    if len(focus) >= 2 and len(focus) >= samples * .55:
        points = [(t, max(0, min(width - crop_width, round(x - crop_width / 2))))
                  for t, x in focus]
        if max(x for _t, x in points) - min(x for _t, x in points) > crop_width * .12:
            return ('track', crop_width, points)
    left = min(x for x, _y, _w, _h in boxes)
    right = max(x + w for x, _y, w, _h in boxes)
    margin = crop_width // 4
    if right - left + margin * 2 > crop_width:
        return None
    center = (left + right) / 2
    return ('single', max(0, min(width - crop_width, int(center - crop_width / 2))), crop_width)


def _track_expression(points: list[tuple[float, int]], ranges: list[tuple[float, float]]) -> str:
    """Map source sample times to the edited clip, then interpolate focus every frame."""
    mapped = []
    offset = 0.
    for start, end in ranges:
        selected = [(offset + t - start, x) for t, x in points if start <= t < end]
        if selected:
            mapped.append((offset, selected[0][1]))
            mapped.extend(selected)
            mapped.append((offset + end - start, selected[-1][1]))
        offset += end - start
    if not mapped:
        return str(points[0][1])
    compact = []
    for t, x in sorted(mapped):
        if compact and t <= compact[-1][0] + .001:
            compact[-1] = (t, x)
        else:
            compact.append((t, x))
    expression = str(compact[-1][1])
    for (start, x0), (end, x1) in reversed(list(zip(compact, compact[1:]))):
        slope = f'{x0}+({x1-x0})*(t-{start:.3f})/{end-start:.3f}'
        expression = f'if(lt(t\\,{end:.3f})\\,{slope}\\,{expression})'
    return expression


def _watermark_image(text: str, target: Path, max_width: int) -> tuple[int, int]:
    from PIL import Image, ImageDraw, ImageFont
    fonts = [Path('C:/Windows/Fonts/arialbd.ttf'),
             Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')]
    font_path = next((font for font in fonts if font.exists()), None)
    if font_path is None:
        raise MediaError('Fonte da marca d’água não encontrada.')
    font_size = 38
    while True:
        font = ImageFont.truetype(str(font_path), font_size)
        box = ImageDraw.Draw(Image.new('RGBA', (1, 1))).textbbox((0, 0), text, font=font)
        text_width = box[2] - box[0]
        if text_width + 20 <= max_width or font_size <= 18:
            break
        font_size -= 2
    if text_width + 20 > max_width:
        raise MediaError('Marca d’água longa demais para o vídeo.')
    image = Image.new('RGBA', (text_width + 20, font_size + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((10, 10 - box[1]), text, font=font, fill=(255, 255, 255, 145),
              stroke_width=2, stroke_fill=(0, 0, 0, 110))
    image.save(target)
    return image.size


def _header_image(name: str, title: str, avatar: Path | None, target: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    image = Image.new('RGBA', (1080, 360), 'white')
    draw = ImageDraw.Draw(image)
    font_path = next((path for path in (Path('C:/Windows/Fonts/arialbd.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')) if path.exists()), None)
    if font_path is None:
        raise MediaError('Fonte do cabeçalho não encontrada.')
    name_font = ImageFont.truetype(str(font_path), 62)
    title_font = ImageFont.truetype(str(font_path), 43)
    if avatar and avatar.is_file():
        portrait = Image.open(avatar).convert('RGB')
        portrait = ImageOps.fit(portrait, (132, 132))
        mask = Image.new('L', (132, 132), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 131, 131), fill=255)
        image.paste(portrait, (62, 42), mask)
    else:
        draw.ellipse((62, 42, 194, 174), fill='#e8eef5')
        draw.text((111, 79), '@', font=ImageFont.truetype(str(font_path), 45), fill='#31516f')
    label = name.strip() or 'Criador'
    while draw.textlength(label, font=name_font) > 785 and len(label) > 4:
        label = label[:-2].rstrip() + '…'
    draw.text((225, 67), label, font=name_font, fill='#111827')
    words = title.strip().split()
    lines = []
    current = ''
    for word in words:
        trial = (current + ' ' + word).strip()
        if current and draw.textlength(trial, font=title_font) > 950:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    if len(lines) > 2:
        lines[1] = lines[1].rstrip(' .') + '…'
    for index, line in enumerate(lines[:2]):
        while draw.textlength(line, font=title_font) > 950 and len(line) > 4:
            line = line[:-2].rstrip() + '…'
        draw.text(((1080 - draw.textlength(line, font=title_font)) / 2, 210 + index * 55),
                  line, font=title_font, fill='#101820')
    image.save(target)


def compose_clip(export: Export, settings: VideoSettings, destination_dir: Path,
                 progress_callback=None, device='cpu', header_name='', header_title='',
                 header_avatar: Path | None = None) -> tuple[Export, list[tuple[float, float]]]:
    source = Path(export.local_path).resolve(strict=True)
    if content_hash(source) != export.content_hash:
        raise MediaError('O arquivo base não corresponde ao manifesto.')
    ranges = _kept_ranges(source, export.duration_s, settings.remove_silence)
    if settings.header_enabled and settings.aspect != 'vertical':
        raise MediaError('O cabeçalho branco exige vídeo vertical.')
    if settings.aspect == 'source' and not settings.watermark_text.strip() and len(ranges) == 1 and not settings.header_enabled:
        return export, ranges
    stream = next(item for item in probe(source)['streams'] if item.get('codec_type') == 'video')
    width, height = int(stream['width']), int(stream['height'])
    layout = _face_layout(source, export.duration_s, width, height) if settings.aspect == 'vertical' else None
    plan = {'ranges': ranges, 'layout': layout, 'settings': settings.model_dump(mode='json'),
            'header_name': header_name, 'header_title': header_title,
            'avatar_hash': content_hash(header_avatar) if header_avatar and header_avatar.is_file() else None}
    key = hashlib.sha256(('presentation-v9|' + export.content_hash + '|' + json.dumps(plan, sort_keys=True)).encode()).hexdigest()
    destination_dir = Path(destination_dir).resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / f'{key}.presented.mp4'
    manifest = target.with_suffix('.export.json')
    expected = sum(end - start for start, end in ranges)
    if target.exists() or manifest.exists():
        if not target.exists() or not manifest.exists():
            raise MediaError('Composição parcial preservada para inspeção.')
        record = Export.model_validate_json(manifest.read_text(encoding='utf-8'))
        if record.export_id != 'export-presentation-' + key or record.content_hash != content_hash(target):
            raise MediaError('Composição existente não corresponde ao manifesto.')
        return record, ranges
    fd, name = tempfile.mkstemp(prefix='.presentation-', suffix='.mp4', dir=destination_dir)
    os.close(fd)
    temporary = Path(name)
    watermark_path = None
    header_path = None
    try:
        graph = []
        for index, (start, end) in enumerate(ranges):
            cpu_frames = 'hwdownload,format=nv12,' if device == 'cuda' else ''
            graph.extend((f'[0:v]{cpu_frames}trim=start={start}:end={end},setpts=PTS-STARTPTS[v{index}]',
                          f'[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]'))
        graph.append(''.join(f'[v{i}][a{i}]' for i in range(len(ranges))) +
                     f'concat=n={len(ranges)}:v=1:a=1[vbase][aout]')
        video = '[vbase]'
        content_rect = (0, 0, width, height)
        if settings.aspect != 'source':
            out_w, out_h = (1080, 1920) if settings.aspect == 'vertical' else (1920, 1080)
            if layout and layout[0] == 'web_player':
                x, y, crop_w, crop_h = layout[1:]
                graph.append(f'{video}crop={crop_w}:{crop_h}:{x}:{y},scale={out_w}:{out_h}:flags=lanczos[vshape]')
                content_rect = (0, 0, out_w, out_h)
            elif layout and layout[0] == 'single':
                x, crop_w = layout[1:]
                graph.append(f'{video}crop={crop_w}:{height}:{x}:0,scale={out_w}:{out_h}:flags=lanczos[vshape]')
                content_rect = (0, 0, out_w, out_h)
            elif layout and layout[0] == 'track':
                crop_w, points = layout[1:]
                focus_x = _track_expression(points, ranges)
                graph.append(f"{video}crop={crop_w}:{height}:x='{focus_x}':y=0,"
                             f'scale={out_w}:{out_h}:flags=lanczos[vshape]')
                content_rect = (0, 0, out_w, out_h)
            elif layout and layout[0] == 'pair':
                graph.append(f'{video}split=2[vleft][vright]')
                for index, (x, y, crop_w, crop_h) in enumerate(layout[1]):
                    graph.append(f'[vleft]' if index == 0 else '[vright]')
                    graph[-1] += f'crop={crop_w}:{crop_h}:{x}:{y},scale=1080:960:flags=lanczos[vpanel{index}]'
                graph.append('[vpanel0][vpanel1]vstack=inputs=2[vshape]')
                content_rect = (0, 0, out_w, out_h)
            else:
                graph.append(f'{video}split=2[vbackground][vforeground]')
                graph.append(f'[vbackground]scale={out_w}:{out_h}:force_original_aspect_ratio=increase:flags=fast_bilinear,'
                             f'crop={out_w}:{out_h},boxblur=20:2[vblur]')
                graph.append(f'[vforeground]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:flags=lanczos[vfit]')
                graph.append('[vblur][vfit]overlay=(W-w)/2:(H-h)/2:shortest=1[vshape]')
                scale = min(out_w / width, out_h / height)
                fit_w, fit_h = round(width * scale), round(height * scale)
                content_rect = ((out_w - fit_w) // 2, (out_h - fit_h) // 2, fit_w, fit_h)
            video = '[vshape]'
        if settings.header_enabled:
            fd, name = tempfile.mkstemp(prefix='.header-', suffix='.png', dir=destination_dir)
            os.close(fd)
            header_path = Path(name)
            _header_image(header_name or settings.header_name,
                          settings.header_title or header_title, header_avatar, header_path)
            graph.append(f'{video}split=2[vheadbg][vheadfg]')
            graph.append('[vheadbg]scale=1080:1560:force_original_aspect_ratio=increase:flags=fast_bilinear,'
                         'crop=1080:1560,boxblur=18:2[vheadblur]')
            graph.append('[vheadfg]scale=1080:1560:force_original_aspect_ratio=decrease:flags=lanczos[vheadfit]')
            graph.append('[vheadblur][vheadfit]overlay=(W-w)/2:(H-h)/2:shortest=1,'
                         'pad=1080:1920:0:360:white[vheaderbase]')
            graph.append(f'[vheaderbase][1:v]overlay=0:0:shortest=1:format=auto[vheader]')
            video = '[vheader]'
            content_rect = (0, 360, 1080, 1560)
        if settings.watermark_text.strip():
            fd, name = tempfile.mkstemp(prefix='.watermark-', suffix='.png', dir=destination_dir)
            os.close(fd)
            watermark_path = Path(name)
            mark_w, mark_h = _watermark_image(settings.watermark_text.strip(), watermark_path,
                                              max(180, int(content_rect[2] * .78)))
            rect_x, rect_y, rect_w, rect_h = content_rect
            inset_x = max(36, round(rect_w * .05))
            inset_y = max(48, round(rect_h * .12))
            x = rect_x + inset_x if settings.watermark_position.endswith('left') else rect_x + rect_w - mark_w - inset_x
            y = rect_y + inset_y if settings.watermark_position.startswith('top') else rect_y + rect_h - mark_h - inset_y
            graph.append(f'{video}[{2 if header_path else 1}:v]overlay={x}:{y}:shortest=1:format=auto[vout]')
            video = '[vout]'
        args = ['-hide_banner', '-loglevel', 'error', '-nostdin', '-y']
        if device == 'cuda':
            args += ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
        args += ['-i', str(source)]
        if header_path:
            args += ['-loop', '1', '-i', str(header_path)]
        if watermark_path:
            args += ['-loop', '1', '-i', str(watermark_path)]
        args += ['-filter_complex', ';'.join(graph), '-map', video, '-map', '[aout]']
        args += (['-c:v', 'h264_nvenc', '-preset', 'p5', '-rc', 'vbr', '-cq', '18', '-b:v', '0']
                 if device == 'cuda' else ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18'])
        args += ['-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', str(temporary)]
        if progress_callback:
            run_ffmpeg_progress(args, expected, progress_callback, timeout=1800)
        else:
            run_tool('ffmpeg', args, timeout=1800)
        duration, _ = av_metadata(temporary)
        if abs(duration - expected) > .25:
            raise MediaError('Duração composta não corresponde aos trechos preservados.')
        result = Export(export_id='export-presentation-' + key, revision_id=export.revision_id,
                        asset_id=export.asset_id, local_path=str(target), duration_s=duration,
                        content_hash=content_hash(temporary))
        os.link(temporary, target)
        manifest.write_text(result.model_dump_json(indent=2), encoding='utf-8')
        return result, ranges
    finally:
        temporary.unlink(missing_ok=True)
        if watermark_path:
            watermark_path.unlink(missing_ok=True)
        if header_path:
            header_path.unlink(missing_ok=True)
