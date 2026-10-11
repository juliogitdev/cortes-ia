"""H.264/AAC cut from original timeline; CUDA uses NVDEC and NVENC."""
from pathlib import Path
import hashlib
import os
import tempfile
from clip_platform.shared import MediaAsset, ClipRevision
from clip_platform.shared.jobs import Export
from .tools import AV_DEMUXERS, MediaError, av_metadata, content_hash, run_tool, run_ffmpeg_progress


def _cached_export(target: Path, manifest: Path, asset: MediaAsset, revision: ClipRevision,
                   key: str, requested_duration: float) -> Export:
    if not target.exists() or not manifest.exists():
        raise MediaError('Incomplete existing export or missing manifest; preserving artifacts for inspection')
    try:
        result = Export.model_validate_json(manifest.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise MediaError('Invalid existing export manifest; preserving artifacts') from exc
    if (result.export_id != 'export-' + key or result.revision_id != revision.revision_id
            or result.asset_id != asset.asset_id or Path(result.local_path) != target
            or content_hash(target) != result.content_hash):
        raise MediaError('Existing export differs from manifest or requested revision; preserving artifacts')
    duration, _ = av_metadata(target)
    if abs(duration-result.duration_s) > .001 or abs(duration-requested_duration) > .2:
        raise MediaError('Existing export duration differs from manifest/request; preserving artifacts')
    return result


def export_clip(asset: MediaAsset, revision: ClipRevision, destination_dir: Path,
                progress_callback=None, device='cpu') -> Export:
    if device not in {'cpu', 'cuda'}:
        raise ValueError('Dispositivo de exportação inválido')
    if revision.asset_id != asset.asset_id:
        raise MediaError('Revision belongs to another asset')
    start, end = revision.boundaries.start_s, revision.boundaries.end_s
    if not 0 <= start < end <= asset.duration_s:
        raise MediaError('Revision interval outside original media')
    source = Path(asset.local_path).resolve(strict=True)
    digest = content_hash(source, (lambda fraction: progress_callback(.10 * fraction, 'verificando gravação')) if progress_callback else None)
    if digest != asset.content_hash:
        raise MediaError('Source media differs from registered asset hash')
    real_duration, _ = av_metadata(source)
    if end > real_duration + .001:
        raise MediaError('Revision interval exceeds actual source duration')
    destination_dir = destination_dir.resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f'{device}-h264-aac-hq-v4|{asset.content_hash}|{revision.revision_id}|{start}|{end}'.encode()).hexdigest()
    target = destination_dir / f'{key}.mp4'
    if target == source:
        raise MediaError('Export cannot replace original media')
    manifest = target.with_suffix('.export.json')
    if target.exists() or manifest.exists():
        if progress_callback:
            progress_callback(.98, 'validando corte existente')
        return _cached_export(target, manifest, asset, revision, key, end-start)
    fd, name = tempfile.mkstemp(prefix='.export-', suffix='.mp4', dir=destination_dir)
    os.close(fd)
    temporary = Path(name)
    manifest_temporary = None
    try:
        seek_before_input = max(0, start - 3)
        seek_after_input = start - seek_before_input
        command = ['-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                   '-protocol_whitelist', 'file,pipe', '-format_whitelist', AV_DEMUXERS]
        if device == 'cuda':
            command += ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda']
        command += ['-ss', str(seek_before_input), '-i', str(source), '-ss', str(seek_after_input),
                    '-t', str(end-start), '-map', '0:v:0', '-map', '0:a:0']
        if device == 'cuda':
            command += ['-c:v', 'h264_nvenc', '-preset', 'p5', '-rc', 'vbr', '-cq', '18', '-b:v', '0']
        else:
            command += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p']
        command += ['-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', str(temporary)]
        if progress_callback:
            run_ffmpeg_progress(command, end-start,
                lambda fraction: progress_callback(.10 + .75 * fraction,
                    'codificando corte na GPU' if device == 'cuda' else 'codificando corte'), timeout=1800)
        else:
            run_tool('ffmpeg', command, timeout=1800)
        duration, _ = av_metadata(temporary)
        if abs(duration - (end-start)) > .2:
            raise MediaError(f'Export duration {duration}s differs from requested {end-start}s')
        digest = content_hash(temporary, (lambda fraction: progress_callback(.85 + .13 * fraction, 'validando corte')) if progress_callback else None)
        result = Export(export_id='export-' + key, revision_id=revision.revision_id,
                      asset_id=asset.asset_id, local_path=str(target), duration_s=duration, content_hash=digest)
        fd, name = tempfile.mkstemp(prefix='.export-manifest-', suffix='.json', dir=destination_dir)
        manifest_temporary = Path(name)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(result.model_dump_json(indent=2))
            stream.flush()
            os.fsync(stream.fileno())
        # No-clobber atomic publication: retries never replace an earlier artifact.
        # A crash between these two links leaves a preserved incomplete pair.
        try:
            os.link(temporary, target)
        except FileExistsError:
            return _cached_export(target, manifest, asset, revision, key, end-start)
        try:
            os.link(manifest_temporary, manifest)
        except FileExistsError:
            return _cached_export(target, manifest, asset, revision, key, end-start)
        if progress_callback:
            progress_callback(.99, 'finalizando corte')
        return result
    finally:
        temporary.unlink(missing_ok=True)
        if manifest_temporary is not None:
            manifest_temporary.unlink(missing_ok=True)
