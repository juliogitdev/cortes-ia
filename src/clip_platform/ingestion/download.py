"""Download de uma gravação por provedores explícitos, com configuração versionável."""
from pathlib import Path
import ipaddress
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import Protocol
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, ConfigDict, Field

from clip_platform.ingestion.local import ingest_file
from clip_platform.media.tools import find_tool
from clip_platform.shared.contracts import MediaAsset


PROVIDERS = {
    'youtube': ('youtube.com', 'youtu.be'),
    'vimeo': ('vimeo.com',),
    'twitch': ('twitch.tv',),
    'dailymotion': ('dailymotion.com', 'dai.ly'),
    'tiktok': ('tiktok.com',),
}


class DownloadSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    quality: str = Field(default='best', pattern='^(best|up_to_height)$')
    max_height: int | None = Field(default=None, ge=144, le=4320)

    def format_selector(self):
        if self.quality == 'up_to_height':
            if self.max_height is None:
                raise ValueError('max_height é obrigatório para up_to_height')
            return f'bestvideo[height<={self.max_height}]+bestaudio/best[height<={self.max_height}]'
        if self.max_height is not None:
            raise ValueError('max_height exige quality=up_to_height')
        return 'bestvideo+bestaudio/best'


class DownloadRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    url: str = Field(min_length=1, max_length=2048)
    settings: DownloadSettings = Field(default_factory=DownloadSettings)


def identify_provider(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port or not host:
        raise ValueError('Use uma URL HTTPS pública de plataforma compatível.')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('Endereços IP não são aceitos.')
    for provider, domains in PROVIDERS.items():
        if any(host == domain or host.endswith('.' + domain) for domain in domains):
            path = parsed.path
            if provider == 'youtube':
                video_id = (parse_qs(parsed.query).get('v') or [''])[0] if path == '/watch' else path.strip('/').split('/')[-1]
                valid_path = host.endswith('youtu.be') or path == '/watch' or bool(re.fullmatch(r'/(live|shorts|embed)/[^/]+/?', path))
                if not valid_path or not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
                    raise ValueError('Informe o link de um único vídeo do YouTube.')
            elif provider == 'vimeo' and not re.fullmatch(r'/\d+/?', path):
                raise ValueError('Informe o link de um único vídeo do Vimeo.')
            elif provider == 'twitch' and not (host == 'clips.twitch.tv' or re.fullmatch(r'/(videos/\d+|[^/]+/clip/[^/]+)/?', path)):
                raise ValueError('Informe o link de um vídeo ou clipe da Twitch.')
            elif provider == 'dailymotion' and not (re.fullmatch(r'/video/[A-Za-z0-9]+/?', path) or host.endswith('dai.ly') and re.fullmatch(r'/[A-Za-z0-9]+/?', path)):
                raise ValueError('Informe o link de um único vídeo do Dailymotion.')
            elif provider == 'tiktok' and not re.fullmatch(r'/@[^/]+/video/\d+/?', path):
                raise ValueError('Informe o link de um único vídeo do TikTok.')
            return provider
    raise ValueError('Plataforma ainda não habilitada para download.')


class Downloader(Protocol):
    def download(self, request: DownloadRequest, directory: Path, provider: str, progress_callback=None) -> MediaAsset: ...


def parse_download_progress(line: str) -> float | None:
    match = re.search(r'CLIP_PROGRESS:\s*([0-9]+(?:\.[0-9]+)?)%', line)
    if not match:
        return None
    value = float(match.group(1)) / 100
    return value if 0 <= value <= 1 else None


def _run_with_progress(command, directory, progress_callback):
    command = [*command]
    command.remove('--no-progress')
    command[3:3] = ['--newline', '--color', 'no_color', '--progress-template',
                    'download:CLIP_PROGRESS:%(progress._percent_str)s:%(progress.eta)s']
    try:
        process = subprocess.Popen(command, cwd=directory, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    except FileNotFoundError as exc:
        raise RuntimeError('yt-dlp não está instalado neste ambiente.') from exc
    lines = queue.Queue()
    def read_output():
        for line in process.stdout:
            lines.put(line.strip())
        lines.put(None)
    threading.Thread(target=read_output, daemon=True).start()
    paths = []
    previous = 0.
    track = 0
    deadline = time.monotonic() + 4 * 60 * 60
    try:
        while True:
            if time.monotonic() > deadline:
                raise RuntimeError('Download excedeu o limite de quatro horas.')
            try:
                line = lines.get(timeout=.5)
            except queue.Empty:
                continue
            if line is None:
                break
            fraction = parse_download_progress(line)
            if fraction is not None:
                if previous >= .8 and fraction < previous - .3:
                    track += 1
                previous = fraction
                progress_callback(min(.9, (track + fraction) / 2), 'baixando')
            elif line and Path(line).is_absolute():
                paths.append(Path(line).resolve())
        if process.wait(timeout=max(.1, deadline-time.monotonic())):
            raise RuntimeError('Download falhou; a plataforma pode exigir acesso ou estar indisponível.')
        return paths
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


class YtDlpDownloader:
    """Adaptador compartilhado hoje; cada plataforma pode substituí-lo no registro."""

    def download(self, request: DownloadRequest, directory: Path, provider: str, progress_callback=None) -> MediaAsset:
        if provider == 'youtube' and not shutil.which('node'):
            raise RuntimeError('Node.js é necessário para obter os formatos completos do YouTube.')
        directory = Path(directory).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / 'source.%(ext)s'
        ffmpeg = Path(find_tool('ffmpeg')).parent
        command = [sys.executable, '-m', 'yt_dlp', '--no-playlist', '--no-config', '--no-progress', '--no-simulate',
                   '--restrict-filenames', '--socket-timeout', '30', '--retries', '3',
                   '--fragment-retries', '3', '--ffmpeg-location', str(ffmpeg), '-f',
                   request.settings.format_selector(), '--merge-output-format', 'mkv',
                   '-o', str(output), '--print', 'after_move:filepath', request.url]
        if provider == 'youtube':
            command[3:3] = ['--js-runtimes', 'node']
        if progress_callback:
            progress_callback(0., 'consultando plataforma')
            paths = _run_with_progress(command, directory, progress_callback)
        else:
            try:
                completed = subprocess.run(command, cwd=directory, capture_output=True, text=True,
                                           timeout=4 * 60 * 60, check=False)
            except FileNotFoundError as exc:
                raise RuntimeError('yt-dlp não está instalado neste ambiente.') from exc
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError('Download excedeu o limite de quatro horas.') from exc
            if completed.returncode:
                raise RuntimeError('Download falhou; a plataforma pode exigir acesso ou estar indisponível.')
            paths = [Path(line.strip()).resolve() for line in completed.stdout.splitlines() if line.strip()]
        if len(paths) != 1 or not paths[0].is_relative_to(directory) or not paths[0].is_file():
            raise RuntimeError('O downloader não entregou um único arquivo local válido.')
        if progress_callback:
            progress_callback(.9, 'registrando gravação')
        asset = ingest_file(paths[0], directory.parent / 'assets',
            (lambda fraction: progress_callback(.9 + .09 * fraction, 'registrando gravação')) if progress_callback else None)
        paths[0].unlink()
        return asset.model_copy(update={'source_uri': request.url})


DEFAULT_BACKEND = YtDlpDownloader()
BACKENDS: dict[str, Downloader] = {provider: DEFAULT_BACKEND for provider in PROVIDERS}


def download_video(request: DownloadRequest, directory: Path, progress_callback=None):
    request = DownloadRequest.model_validate(request)
    provider = identify_provider(request.url)
    if progress_callback:
        return BACKENDS[provider].download(request, directory, provider, progress_callback), provider
    return BACKENDS[provider].download(request, directory, provider), provider
