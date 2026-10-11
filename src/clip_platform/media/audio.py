"""PCM mono 16 kHz extraction for speech backend; preserves original source."""
from pathlib import Path
import os
import tempfile
from clip_platform.shared import MediaAsset
from .tools import AV_DEMUXERS, MediaError, content_hash, probe, run_tool, run_ffmpeg_progress


def extract_audio(asset: MediaAsset, output: Path, progress_callback=None) -> Path:
    source = Path(asset.local_path).resolve(strict=True)
    output = output.resolve()
    if output == source:
        raise MediaError('Audio output cannot replace original media')
    if 'audio' not in asset.tracks:
        raise MediaError('Asset has no audio track')
    digest = content_hash(source, (lambda fraction: progress_callback(.12 * fraction)) if progress_callback else None)
    if digest != asset.content_hash:
        raise MediaError('Source media differs from registered asset hash')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.audio-', suffix='.wav', dir=output.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        command = ['-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                           '-protocol_whitelist', 'file,pipe', '-format_whitelist', AV_DEMUXERS,
                           '-i', str(source), '-map', '0:a:0',
                           '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(temporary)]
        if progress_callback:
            run_ffmpeg_progress(command, asset.duration_s,
                lambda fraction: progress_callback(.12 + .83 * fraction), timeout=1800)
        else:
            run_tool('ffmpeg', command, timeout=1800)
        streams = probe(temporary, demuxers='wav').get('streams', [])
        if not streams or streams[0].get('codec_name') != 'pcm_s16le' or int(streams[0].get('sample_rate', 0)) != 16000 or streams[0].get('channels') != 1:
            raise MediaError('Extracted audio does not meet PCM mono 16 kHz contract')
        os.replace(temporary, output)
        if progress_callback:
            progress_callback(1.)
        return output
    finally:
        temporary.unlink(missing_ok=True)
