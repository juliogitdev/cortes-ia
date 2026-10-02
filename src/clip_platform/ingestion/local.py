"""Hash-addressed copy of explicitly supplied local audiovisual file."""
from pathlib import Path
import os
import shutil
import tempfile

from clip_platform.shared import MediaAsset
from clip_platform.media.tools import MediaError, av_metadata, content_hash

ALLOWED_SUFFIXES = {'.mp4', '.mkv', '.mov', '.webm', '.avi', '.m4v', '.ts', '.mpeg', '.mpg'}


def ingest_file(path: Path, destination_dir: Path) -> MediaAsset:
    source = path.expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in ALLOWED_SUFFIXES:
        raise MediaError('Expected a local audiovisual container; playlists are not accepted')
    destination_dir = destination_dir.resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.ingest-', suffix=source.suffix.lower(), dir=destination_dir)
    os.close(fd)
    temporary = Path(temporary)
    try:
        shutil.copyfile(source, temporary)
        digest = content_hash(temporary)
        duration, tracks = av_metadata(temporary)
        target = destination_dir / (digest.split(':')[1] + source.suffix.lower())
        if target.exists():
            if content_hash(target) != digest:
                raise MediaError('Existing hash-addressed media is corrupted; preserving it for inspection')
        else:
            # Atomic hardlink publication is no-clobber, including competing ingest workers.
            try:
                os.link(temporary, target)
            except FileExistsError:
                if content_hash(target) != digest:
                    raise MediaError('Concurrent ingest target differs from expected hash')
        return MediaAsset(asset_id='asset-' + digest.split(':')[1], source_uri=source.as_uri(),
                          content_hash=digest, duration_s=duration, tracks=tracks, local_path=str(target))
    finally:
        temporary.unlink(missing_ok=True)
