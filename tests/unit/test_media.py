from pathlib import Path
import struct
import subprocess
import wave

import pytest
from clip_platform.ingestion.local import ingest_file
from clip_platform.media.audio import extract_audio
from clip_platform.media.export import export_clip
from clip_platform.media.tools import MediaError, content_hash, find_tool, probe, run_tool
from clip_platform.shared import ClipRevision, Interval, MediaAsset


@pytest.fixture
def synthetic(tmp_path):
    try:
        find_tool('ffmpeg')
        find_tool('ffprobe')
    except MediaError as exc:
        pytest.skip(str(exc))
    path = tmp_path / 'original with spaces.mp4'
    # Known event at t=2: red/440Hz becomes blue/880Hz.
    run_tool('ffmpeg', ['-v', 'error', '-nostdin', '-y',
        '-f', 'lavfi', '-i', 'color=c=red:s=160x120:r=25:d=2',
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000:duration=2',
        '-f', 'lavfi', '-i', 'color=c=blue:s=160x120:r=25:d=2',
        '-f', 'lavfi', '-i', 'sine=frequency=880:sample_rate=16000:duration=2',
        '-filter_complex', '[0:v][1:a][2:v][3:a]concat=n=2:v=1:a=1[v][a]',
        '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', str(path)])
    return path


def revision(asset, start=2.2, end=3.7):
    return ClipRevision(revision_id='rev-1', candidate_id='candidate-1', asset_id=asset.asset_id,
                        boundaries=Interval(start_s=start, end_s=end), editor_changes=[])


def test_real_ingest_pcm_and_export(synthetic, tmp_path):
    before = content_hash(synthetic)
    asset = ingest_file(synthetic, tmp_path / 'assets')
    duplicate = ingest_file(synthetic, tmp_path / 'assets')
    assert asset.asset_id == duplicate.asset_id
    assert asset.content_hash == before
    assert set(asset.tracks) == {'audio', 'video'}
    assert abs(asset.duration_s - 4) < .1
    pcm = extract_audio(asset, tmp_path / 'audio.wav')
    with wave.open(str(pcm)) as audio:
        assert (audio.getnchannels(), audio.getframerate(), audio.getsampwidth()) == (1, 16000, 2)
    result = export_clip(asset, revision(asset), tmp_path / 'exports')
    assert abs(result.duration_s - 1.5) <= .2
    assert result.content_hash == content_hash(Path(result.local_path))
    info = probe(Path(result.local_path))
    assert {stream['codec_type'] for stream in info['streams']} == {'audio', 'video'}
    # Verify actual event content and sound, beyond successful tool exit/duration.
    frame = subprocess.run([find_tool('ffmpeg'), '-v', 'error', '-i', result.local_path,
                            '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'],
                           capture_output=True, check=True, timeout=30).stdout
    red, green, blue = frame[:3]
    assert blue > 200 and red < 30 and green < 30
    exported_asset = MediaAsset(asset_id='cut', source_uri='file:///synthetic-cut',
        content_hash=result.content_hash, duration_s=result.duration_s,
        tracks=['video', 'audio'], local_path=result.local_path)
    sound = extract_audio(exported_asset, tmp_path / 'cut.wav')
    with wave.open(str(sound)) as audio:
        audio.setpos(3200)
        data = audio.readframes(8000)
    samples = struct.unpack('<' + 'h' * (len(data)//2), data)
    crossings = sum(a <= 0 < b for a, b in zip(samples, samples[1:]))
    frequency = crossings / (len(samples)/16000)
    assert abs(frequency - 880) < 15
    assert content_hash(synthetic) == before
    assert not list((tmp_path / 'exports').glob('.export-*'))


def test_invalid_revision_and_original_preserved(synthetic, tmp_path):
    asset = ingest_file(synthetic, tmp_path / 'assets')
    with pytest.raises(MediaError, match='outside'):
        export_clip(asset, revision(asset, end=5), tmp_path / 'exports')
    bad = revision(asset).model_copy(update={'asset_id': 'other'})
    with pytest.raises(MediaError, match='another'):
        export_clip(asset, bad, tmp_path / 'exports')
    with pytest.raises(MediaError, match='original'):
        extract_audio(asset, Path(asset.local_path))


def test_reject_playlist_and_corrupted_input(tmp_path):
    path = tmp_path / 'external.m3u8'
    path.write_text('#EXTM3U\nhttps://example.invalid/media.ts')
    with pytest.raises(MediaError, match='playlists'):
        ingest_file(path, tmp_path / 'assets')


def test_corruption_is_preserved_and_temporary_files_cleaned(synthetic, tmp_path):
    asset = ingest_file(synthetic, tmp_path / 'assets')
    target = Path(asset.local_path)
    target.write_bytes(b'corrupt')
    with pytest.raises(MediaError, match='corrupted'):
        ingest_file(synthetic, tmp_path / 'assets')
    assert target.read_bytes() == b'corrupt'
    assert not list((tmp_path / 'assets').glob('.ingest-*'))


def test_unreadable_media_fails_and_cleans_copy(tmp_path):
    try:
        find_tool('ffprobe')
    except MediaError as exc:
        pytest.skip(str(exc))
    source = tmp_path / 'invalid.mp4'
    source.write_bytes(b'not a video')
    with pytest.raises(MediaError, match='ffprobe failed'):
        ingest_file(source, tmp_path / 'assets')
    assert source.read_bytes() == b'not a video'
    assert not list((tmp_path / 'assets').iterdir())


def test_bad_tool_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv('CLIP_FFPROBE', str(tmp_path / 'missing.exe'))
    with pytest.raises(MediaError, match='Configured'):
        find_tool('ffprobe')
    with pytest.raises(ValueError, match='Unsupported'):
        find_tool('shell')


def test_export_retry_returns_same_artifact_without_reencode(synthetic, tmp_path, monkeypatch):
    asset = ingest_file(synthetic, tmp_path / 'assets')
    rev = revision(asset)
    first = export_clip(asset, rev, tmp_path / 'exports')
    target = Path(first.local_path)
    previous_mtime = target.stat().st_mtime_ns
    def unexpected(*args, **kwargs):
        pytest.fail('Retry must reuse export, not recode it')
    monkeypatch.setattr('clip_platform.media.export.run_tool', unexpected)
    second = export_clip(asset, rev, tmp_path / 'exports')
    assert second == first
    assert target.stat().st_mtime_ns == previous_mtime
    target.write_bytes(b'corrupted existing export')
    with pytest.raises(MediaError, match='differs from manifest'):
        export_clip(asset, rev, tmp_path / 'exports')
    assert target.read_bytes() == b'corrupted existing export'


def test_export_missing_manifest_preserves_existing_artifact(synthetic, tmp_path):
    asset = ingest_file(synthetic, tmp_path / 'assets')
    rev = revision(asset)
    result = export_clip(asset, rev, tmp_path / 'exports')
    target = Path(result.local_path)
    target.with_suffix('.export.json').unlink()
    digest = content_hash(target)
    previous_mtime = target.stat().st_mtime_ns
    with pytest.raises(MediaError, match='missing manifest'):
        export_clip(asset, rev, tmp_path / 'exports')
    assert content_hash(target) == digest
    assert target.stat().st_mtime_ns == previous_mtime


@pytest.mark.parametrize('playlist_kind', ['hls', 'concat'])
def test_renamed_local_playlist_is_rejected_before_ingestion(synthetic, tmp_path, playlist_kind):
    path = tmp_path / 'playlist disguised.mp4'
    if playlist_kind == 'hls':
        text = '#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:4\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:4.0,\n' + synthetic.as_uri() + '\n#EXT-X-ENDLIST\n'
    else:
        text = "ffconcat version 1.0\nfile '" + synthetic.as_posix() + "'\n"
    path.write_text(text, encoding='utf-8')
    digest = content_hash(synthetic)
    with pytest.raises(MediaError, match='ffprobe failed') as rejected:
        ingest_file(path, tmp_path / 'assets')
    if playlist_kind == 'concat':
        assert 'not on whitelist' in str(rejected.value)
    assert content_hash(synthetic) == digest
    assert path.read_text(encoding='utf-8') == text
    assert not list((tmp_path / 'assets').iterdir())
