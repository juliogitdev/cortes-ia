"""Local CPU media tools. All subprocess arguments are separated; no shell."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

AV_DEMUXERS = 'mov,matroska,webm,avi,mpegts,mpeg'


class MediaError(ValueError):
    pass


def find_tool(name: str) -> str:
    if name not in {'ffmpeg', 'ffprobe'}:
        raise ValueError('Unsupported media tool')
    configured = os.environ.get(f'CLIP_{name.upper()}')
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.is_file():
            raise MediaError(f'Configured {name} not found: {path}')
        return str(path)
    found = shutil.which(name)
    if found:
        return found
    root = Path(__file__).resolve().parents[3] / 'storage' / 'tools'
    filename = f'{name}.exe' if os.name == 'nt' else name
    matches = sorted(root.glob(f'*/bin/{filename}'))
    if matches:
        return str(matches[-1].resolve())
    raise MediaError(f'{name} unavailable. Run scripts/bootstrap_media.ps1 or configure CLIP_{name.upper()}.')


def run_tool(name: str, arguments: list[str], timeout: float = 300) -> str:
    try:
        result = subprocess.run([find_tool(name), *arguments], capture_output=True,
                                text=True, encoding='utf-8', errors='replace',
                                timeout=timeout, check=True)
        return result.stdout
    except subprocess.TimeoutExpired as exc:
        raise MediaError(f'{name} timed out after {timeout}s') from exc
    except subprocess.CalledProcessError as exc:
        raise MediaError(f'{name} failed: {exc.stderr[-2000:]}') from exc
    except OSError as exc:
        raise MediaError(f'{name} could not start: {exc}') from exc


def probe(path: Path, demuxers: str = AV_DEMUXERS) -> dict:
    path = path.resolve(strict=True)
    raw = run_tool('ffprobe', ['-v', 'error', '-protocol_whitelist', 'file,pipe',
                             '-format_whitelist', demuxers,
                             '-show_format', '-show_streams', '-of', 'json', str(path)], timeout=30)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MediaError('Invalid ffprobe JSON') from exc


def content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return 'sha256:' + digest.hexdigest()


def av_metadata(path: Path) -> tuple[float, list[str]]:
    import math
    info = probe(path)
    try:
        duration = float(info['format']['duration'])
    except (KeyError, TypeError, ValueError) as exc:
        raise MediaError('Media duration unavailable') from exc
    tracks = [kind for kind in ('video', 'audio')
              if any(s.get('codec_type') == kind for s in info.get('streams', []))]
    if not math.isfinite(duration) or duration <= 0 or set(tracks) != {'audio', 'video'}:
        raise MediaError('Local input must have positive duration, video and audio')
    return duration, tracks
