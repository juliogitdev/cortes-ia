from pathlib import Path
import hashlib

import pytest

from clip_platform.media.tools import MediaError, find_tool, run_tool
from clip_platform.shared.contracts import Evidence, EvidenceBundle, Provenance, SubtitleSettings
from clip_platform.shared.jobs import Export
from clip_platform.subtitles.render import build_captions, render_subtitled_clip, _ass_document


class Settings:
    enabled = True
    style = 'yellow_pop'
    position = 'bottom'
    font_scale = 1.0
    max_words_per_line = 2


def bundle(words=True):
    provenance = Provenance(run_id='speech-1', source_uri='local',
                            artifact_hash='sha256:' + '0' * 64, original_offset_s=0,
                            settings={'words': [
                                {'start_s': 10.5, 'end_s': 11.0, 'text': 'Olá'},
                                {'start_s': 11.1, 'end_s': 11.5, 'text': 'mundo'},
                                {'start_s': 12.0, 'end_s': 12.5, 'text': 'agora'},
                            ] if words else []})
    evidence = Evidence(evidence_id='e-1', asset_id='a-1', start_s=10, end_s=13,
                        observation='Olá mundo agora', provenance=provenance)
    return EvidenceBundle(asset_id='a-1', transcript=[evidence], visual_events=[],
                          audio_events=[], quality=[], provenance=[provenance])


def test_original_offsets_and_end_exclusive():
    captions = build_captions(bundle(), 11, 12, 2)
    assert len(captions) == 1
    assert captions[0].start_s == pytest.approx(.1)
    assert captions[0].end_s == pytest.approx(.5)
    assert captions[0].words[captions[0].active_word] == 'mundo'


def test_removed_pause_remaps_words_to_export_clock():
    captions = build_captions(bundle(), 10, 13, 2, time_map=[(0, 1), (1.8, 3)])
    assert [caption.words[caption.active_word] for caption in captions] == ['Olá', 'agora']
    assert captions[1].start_s == pytest.approx(1.2)


def test_missing_word_timestamps_fail():
    with pytest.raises(MediaError, match='sem horários por palavra'):
        build_captions(bundle(words=False), 10, 13)
    corrected = build_captions(bundle(words=False), 10, 13, 2,
        [{'start_s': 10.5, 'end_s': 11., 'text': 'Revisado'}])
    assert corrected[0].words == ('Revisado',)


def test_old_repetition_is_not_rendered_without_manual_correction():
    data = bundle()
    data.transcript[0].observation = 'Pão de queijo? ' * 12
    assert build_captions(data, 10, 13) == []
    corrected = build_captions(data, 10, 13, word_overrides=[
        {'start_s': 10.5, 'end_s': 11., 'text': 'Fala revisada'}])
    assert corrected[0].words == ('Fala revisada',)


def test_ass_escapes_untrusted_text_and_limits_two_lines():
    data = bundle()
    data.transcript[0].provenance.settings['words'][0]['text'] = r'{\r} attack'
    captions = build_captions(data, 10, 13, 2)
    ass = _ass_document(captions, Settings())
    assert r'{\r} attack' not in ass
    assert '｛＼r｝' in ass
    assert r'\N' in ass
    assert r'\t(0,140,\fscx100\fscy100)' in ass


def test_custom_colors_size_and_outline_change_ass_and_are_validated():
    settings = SubtitleSettings(enabled=True, text_color='#123456',
        highlight_color='#EEAA11', outline_color='#010203', outline_width=7,
        font_scale=1.4, position='middle')
    ass = _ass_document(build_captions(bundle(), 10, 13, 2), settings)
    assert 'Pop,Arial,126,&H00563412,&H00563412,&H00030201' in ass
    assert r'\c&H0011AAEE&' in ass
    assert ',1,7,3,5,' in ass
    with pytest.raises(ValueError):
        SubtitleSettings(enabled=True, highlight_color='yellow')
    with pytest.raises(ValueError):
        SubtitleSettings(enabled=True, outline_width=9)


def test_render_synthetic_video(tmp_path):
    try:
        find_tool('ffmpeg')
    except MediaError:
        pytest.skip('ffmpeg unavailable')
    source = tmp_path / 'source.mp4'
    run_tool('ffmpeg', ['-y', '-f', 'lavfi', '-i', 'color=c=black:s=320x576:r=24:d=3',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                        '-shortest', str(source)], timeout=30)
    digest = 'sha256:' + hashlib.sha256(source.read_bytes()).hexdigest()
    base = Export(export_id='base', revision_id='rev', asset_id='a-1',
                  local_path=str(source), duration_s=3, content_hash=digest)
    result = render_subtitled_clip(base, bundle(), 10, 13, Settings(), tmp_path)
    assert Path(result.local_path).is_file()
    assert result.caption_count == 3
    assert result.timing_quality == 'word'
    assert Path(result.local_path).with_suffix('.export.json').is_file()
    assert render_subtitled_clip(base, bundle(), 10, 13, Settings(), tmp_path) == result
    different = render_subtitled_clip(base, bundle(), 10, 13,
        SubtitleSettings(enabled=True, highlight_color='#00FF00', font_scale=1.3), tmp_path)
    assert different.export.export_id != result.export.export_id
