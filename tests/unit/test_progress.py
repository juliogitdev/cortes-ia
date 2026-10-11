"""Measured progress does not claim an ETA before enough work has completed."""
from pathlib import Path

from clip_platform.ingestion.download import parse_download_progress
from clip_platform.media.tools import run_ffmpeg_progress
from clip_platform.services.store import Store
from clip_platform.worker.progress import ProgressReporter


def test_progress_and_eta_are_persisted_and_monotonic(tmp_path):
    store = Store(tmp_path)
    project = store.create_project('Live')
    queued = store.enqueue(project.project_id, 'download', 'one', {'url': 'example'})
    store.claim('owner')
    now = [0.]
    reporter = ProgressReporter(store, queued.job_id, 'owner', clock=lambda: now[0])
    reporter.update('baixando', .1, .1)
    assert store.get_job(queued.job_id).eta_s is None
    now[0] = 30.
    reporter.update('baixando', .2, .2)
    measured = store.get_job(queued.job_id)
    assert measured.progress == .2 and measured.eta_s == 240
    now[0] = 40.
    reporter.update('baixando', .15, .15, force=True)
    assert store.get_job(queued.job_id).progress == .2
    store.finish(queued.job_id, 'owner', {
        'asset_id': 'asset-1', 'source_uri': 'example',
        'content_hash': 'sha256:' + '0' * 64, 'duration_s': 1,
        'tracks': ['audio', 'video'], 'local_path': str(tmp_path / 'asset.mp4')})
    done = store.get_job(queued.job_id)
    assert done.progress == 1 and done.eta_s == 0


def test_ytdlp_percent_parser_rejects_non_progress_text():
    assert parse_download_progress('CLIP_PROGRESS:  42.5%:13') == .425
    assert parse_download_progress('warning from source') is None
    assert parse_download_progress('CLIP_PROGRESS: 145%:NA') is None


def test_ffmpeg_reports_output_timeline(tmp_path):
    output = tmp_path / 'short.mp4'
    fractions = []
    run_ffmpeg_progress(['-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
        '-f', 'lavfi', '-i', 'testsrc2=size=160x120:rate=25:duration=1',
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000:duration=1',
        '-c:v', 'libx264', '-c:a', 'aac', str(output)], 1., fractions.append, timeout=30)
    assert output.is_file() and output.stat().st_size > 0
    assert fractions and fractions[-1] == 1.
