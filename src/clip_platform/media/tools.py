"""Local CPU media tools. All subprocess arguments are separated; no shell."""
import hashlib
import json
import os
import queue
from pathlib import Path
import shutil
import subprocess
import threading
import time

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


def run_ffmpeg_progress(arguments: list[str], duration_s: float, on_progress, timeout: float):
    """Run ffmpeg and report output timeline progress without a shell."""
    command = [find_tool('ffmpeg'), *arguments[:-1], '-progress', 'pipe:1',
               '-nostats', arguments[-1]]
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    except OSError as exc:
        raise MediaError(f'ffmpeg could not start: {exc}') from exc
    lines = queue.Queue()
    def read_output():
        for line in process.stdout:
            lines.put(line.rstrip())
        lines.put(None)
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    errors = []
    try:
        while True:
            if time.monotonic() > deadline:
                raise MediaError(f'ffmpeg timed out after {timeout}s')
            try:
                line = lines.get(timeout=.5)
            except queue.Empty:
                continue
            if line is None:
                break
            if line.startswith('out_time='):
                try:
                    hours, minutes, seconds = line[9:].split(':')
                    elapsed = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    if duration_s > 0:
                        on_progress(min(1., max(0., elapsed / duration_s)))
                except (ValueError, TypeError):
                    pass
            elif line and not line.startswith(('frame=', 'fps=', 'stream_', 'bitrate=',
                    'total_size=', 'out_time_us=', 'out_time_ms=', 'dup_frames=',
                    'drop_frames=', 'speed=', 'progress=')):
                errors.append(line)
                errors = errors[-20:]
        result = process.wait(timeout=max(.1, deadline - time.monotonic()))
        if result:
            raise MediaError(f'ffmpeg failed: {" ".join(errors)[-2000:]}')
        on_progress(1.)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


def probe(path: Path, demuxers: str = AV_DEMUXERS) -> dict:
    path = path.resolve(strict=True)
    raw = run_tool('ffprobe', ['-v', 'error', '-protocol_whitelist', 'file,pipe',
                             '-format_whitelist', demuxers,
                             '-show_format', '-show_streams', '-of', 'json', str(path)], timeout=30)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MediaError('Invalid ffprobe JSON') from exc


def content_hash(path: Path, progress_callback=None) -> str:
    digest = hashlib.sha256()
    total = path.stat().st_size if progress_callback else 0
    processed = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
            if progress_callback:
                processed += len(chunk)
                progress_callback(min(1., processed / total) if total else 1.)
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
