"""Prova real CPU: upload → fala → baseline → revisão → FFmpeg → download via API."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from clip_platform.api.app import create_app
from clip_platform.worker.runner import run_once

def checked(response):
    response.raise_for_status()
    return response.json()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, default=Path('storage/demo/demo.mp4'))
    parser.add_argument('--model', type=Path, default=Path('models/whisper-tiny'))
    parser.add_argument('--storage', type=Path, default=Path('storage/smoke-local'))
    parser.add_argument('--duration', type=float, default=20.)
    parser.add_argument('--output', type=Path, default=Path('runtime/diagnostics/local-smoke.json'))
    args = parser.parse_args()
    started = time.perf_counter()
    report = {'observed_at': datetime.now(timezone.utc).isoformat(), 'device': 'cpu',
              'fixture': 'synthetic speech and test video; not editorial benchmark', 'status': 'failed',
              'versions': {p: importlib.metadata.version(p) for p in ['faster-whisper', 'ctranslate2', 'fastapi', 'streamlit']},
              'gpu_validation': 'pending on PC; no VRAM used/measured', 'memory_measurement': None}
    try:
        app = create_app(args.storage)
        with TestClient(app) as client:
            project = checked(client.post('/projects', json={'name': 'Prova CPU sintética'}))
            with args.video.open('rb') as video:
                asset = checked(client.post(f"/projects/{project['project_id']}/upload", files={'file': ('demo.mp4', video, 'video/mp4')}))
            request = {'asset_id': asset['asset_id'], 'duration_mode': 'exact', 'target_s': args.duration,
                       'top_k': 1, 'niche': 'teste-sintetico'}
            analysis = checked(client.post(f"/projects/{project['project_id']}/analyses", json=request, headers={'Idempotency-Key': 'analyze-1'}))
            job = run_once(app.state.store, args.model, 'cpu')
            if job.status != 'completed':
                raise RuntimeError(job.error or job.status)
            result = checked(client.get(f"/analyses/{analysis['job_id']}/candidates"))
            report['asset_hash'] = asset['content_hash']
            report['speech_provenance'] = result['evidence']['provenance'][0]['settings']
            report['memory_measurement'] = report['speech_provenance'].get('memory_measurement')
            report['recognized_segments'] = len(result['evidence']['transcript'])
            report['candidate_count'] = len(result['candidates'])
            if not result['candidates']:
                raise RuntimeError('Nenhum candidato na prova pequena: ' + str(result['limitations']))
            candidate = result['candidates'][0]
            revision = checked(client.post(f"/candidates/{candidate['candidate_id']}/revisions", json={'analysis_id': analysis['job_id'],
                'start_s': candidate['start_s'], 'end_s': candidate['end_s'], 'editor_changes': ['Prova técnica sintética']}))
            export = checked(client.post(f"/revisions/{revision['revision_id']}/exports", headers={'Idempotency-Key': 'export-1'}))
            job = run_once(app.state.store, args.model, 'cpu')
            if job.status != 'completed':
                raise RuntimeError(job.error or job.status)
            downloaded = client.get(f"/exports/{job.result['export_id']}/download")
            downloaded.raise_for_status()
            output = args.storage / 'downloaded-cut.mp4'
            output.write_bytes(downloaded.content)
            assert 'sha256:' + hashlib.sha256(downloaded.content).hexdigest() == job.result['content_hash']
            report['export'] = job.result
            report['download_bytes'] = len(downloaded.content)
            report['downloaded_path'] = str(output.resolve())
            report['status'] = 'passed'
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        report['total_elapsed_s'] = time.perf_counter() - started
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"{report['status']}: {args.output}", flush=True)
    return 0 if report['status'] == 'passed' else 1

if __name__ == '__main__':
    raise SystemExit(main())
