"""PCM mono 16 kHz extraction for speech backend; preserves original source."""
from pathlib import Path
import os
import tempfile
from clip_platform.shared import MediaAsset
from .tools import AV_DEMUXERS, MediaError, content_hash, probe, run_tool


def extract_audio(asset: MediaAsset, output: Path) -> Path:
    source = Path(asset.local_path).resolve(strict=True)
    output = output.resolve()
    if output == source:
        raise MediaError('Audio output cannot replace original media')
    if 'audio' not in asset.tracks:
        raise MediaError('Asset has no audio track')
    if content_hash(source) != asset.content_hash:
        raise MediaError('Source media differs from registered asset hash')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.audio-', suffix='.wav', dir=output.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        run_tool('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                           '-protocol_whitelist', 'file,pipe', '-format_whitelist', AV_DEMUXERS,
                           '-i', str(source), '-map', '0:a:0',
                           '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(temporary)], timeout=1800)
        streams = probe(temporary, demuxers='wav').get('streams', [])
        if not streams or streams[0].get('codec_name') != 'pcm_s16le' or int(streams[0].get('sample_rate', 0)) != 16000 or streams[0].get('channels') != 1:
            raise MediaError('Extracted audio does not meet PCM mono 16 kHz contract')
        os.replace(temporary, output)
        return output
    finally:
        temporary.unlink(missing_ok=True)
