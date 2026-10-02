import hashlib
from pathlib import Path
import threading
import time

from fastapi.testclient import TestClient
import pytest
from clip_platform.api.app import create_app
from clip_platform.media.tools import find_tool, run_tool, MediaError
from clip_platform.shared.contracts import Evidence, EvidenceBundle, Provenance
from clip_platform.worker.runner import run_once


def fake_transcriber(asset, audio, model, device='cpu'):
    provenance = Provenance(run_id='synthetic-test', source_uri='synthetic://known',
        artifact_hash=asset.content_hash, original_offset_s=0, settings={'mock': True})
    return EvidenceBundle(asset_id=asset.asset_id, transcript=[Evidence(evidence_id='known-1', asset_id=asset.asset_id,
        start_s=.5, end_s=2., observation='Trecho de fala conhecido para validar somente interfaces.', provenance=provenance)],
        visual_events=[], audio_events=[], quality=['Fala simulada no teste de integração'], provenance=[provenance])


def slow_transcriber(asset, audio, model, device='cpu'):
    time.sleep(30)
    return fake_transcriber(asset, audio, model, device)


@pytest.fixture
def local_setup(tmp_path):
    try:
        find_tool('ffmpeg')
        find_tool('ffprobe')
    except MediaError as exc:
        pytest.skip(str(exc))
    video = tmp_path / 'source.mp4'
    run_tool('ffmpeg', ['-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'testsrc2=size=160x120:rate=25:duration=4',
                       '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000:duration=4',
                       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(video)])
    app = create_app(tmp_path / 'storage')
    with TestClient(app) as client:
        project = client.post('/projects', json={'name': 'Integração'}).json()
        with video.open('rb') as handle:
            response = client.post(f"/projects/{project['project_id']}/upload", files={'file': ('video.mp4', handle, 'video/mp4')})
        assert response.status_code == 201, response.text
        yield client, app.state.store, project, response.json(), video


def enqueue(client, project, asset, key='analysis-1'):
    response = client.post(f"/projects/{project['project_id']}/analyses", headers={'Idempotency-Key': key},
        json={'asset_id': asset['asset_id'], 'duration_mode': 'exact', 'target_s': 2., 'top_k': 2, 'niche': 'teste'})
    assert response.status_code == 202, response.text
    return response.json()


def test_real_api_worker_export_download_with_simulated_speech(local_setup):
    client, store, project, asset, original = local_setup
    job = enqueue(client, project, asset)
    assert enqueue(client, project, asset)['job_id'] == job['job_id']
    done = run_once(store, 'unused', transcriber=fake_transcriber)
    assert done.status == 'completed', done.error
    result = client.get(f"/analyses/{job['job_id']}/candidates").json()
    candidate = result['candidates'][0]
    response = client.post(f"/candidates/{candidate['candidate_id']}/revisions", json={
        'analysis_id': job['job_id'], 'start_s': .6, 'end_s': 2.6, 'editor_changes': ['Ajuste conhecido']})
    assert response.status_code == 201, response.text
    revision = response.json()
    exported = client.post(f"/revisions/{revision['revision_id']}/exports", headers={'Idempotency-Key': 'export-1'})
    assert exported.status_code == 202, exported.text
    done = run_once(store, 'unused')
    assert done.status == 'completed', done.error
    response = client.get(f"/exports/{done.result['export_id']}/download")
    assert response.status_code == 200
    assert 'sha256:' + hashlib.sha256(response.content).hexdigest() == done.result['content_hash']
    assert abs(done.result['duration_s'] - 2.) <= .2
    # Reabrir banco/API mantém resultados, sem disparar processamento.
    reopened = create_app(store.root)
    assert reopened.state.store.get_analysis(job['job_id']).candidates[0].candidate_id == candidate['candidate_id']
    assert run_once(store, 'unused') is None
    assert original.exists()


def test_input_validation_and_authorized_files(local_setup, tmp_path):
    client, store, project, asset, original = local_setup
    response = client.post(f"/projects/{project['project_id']}/analyses", json={'asset_id': asset['asset_id'],
        'duration_mode': 'exact', 'target_s': 2, 'top_k': 1, 'niche': 'teste'})
    assert response.status_code == 422  # Idempotency-Key obrigatório
    with original.open('rb') as handle:
        response = client.post(f"/projects/{project['project_id']}/upload", files={'file': ('same.mp4', handle, 'video/mp4')})
    assert response.status_code == 201  # fonte estável não depende do temporário de upload
    outside = tmp_path / 'secret.mp4'
    outside.write_bytes(b'not-served')
    from clip_platform.shared.contracts import MediaAsset
    other = store.create_project('Outro')
    store.put_asset(other.project_id, MediaAsset(asset_id='outside', source_uri='synthetic://outside',
        content_hash='sha256:' + 'a'*64, duration_s=1, tracks=['video', 'audio'], local_path=str(outside)))
    assert client.get('/assets/outside/media').status_code == 404
    assert client.post(f"/projects/{project['project_id']}/upload", files={'file': ('../../input.m3u8', b'#EXTM3U', 'text/plain')}).status_code == 422


def test_worker_failure_and_cancel_kills_execution(local_setup):
    client, store, project, asset, original = local_setup
    failing = enqueue(client, project, asset, 'missing-model')
    done = run_once(store, 'model-not-found')
    assert done.status == 'failed' and done.error
    running = enqueue(client, project, asset, 'cancel-me')
    thread = threading.Thread(target=run_once, args=(store, 'unused'), kwargs={'transcriber': slow_transcriber})
    thread.start()
    deadline = time.monotonic() + 15
    while store.get_job(running['job_id']).stage != 'transcrevendo' and time.monotonic() < deadline:
        time.sleep(.1)
    assert store.get_job(running['job_id']).stage == 'transcrevendo'
    assert client.post(f"/jobs/{running['job_id']}/cancel").status_code == 200
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert store.get_job(running['job_id']).status == 'cancelled'
    next_job = enqueue(client, project, asset, 'next')
    assert run_once(store, 'unused', transcriber=fake_transcriber).status == 'completed'


def test_panel_revision_export_and_download_against_real_api(local_setup, monkeypatch):
    import sys
    from streamlit.testing.v1 import AppTest
    import httpx
    client, store, project, asset, original = local_setup
    analysis = enqueue(client, project, asset, 'panel-analysis')
    assert run_once(store, 'unused', transcriber=fake_transcriber).status == 'completed'

    def local_http(method, url, **kwargs):
        kwargs.pop('timeout', None)
        path = str(url).split('127.0.0.1:8000', 1)[1]
        return client.request(method, path, **kwargs)

    monkeypatch.setattr(httpx, 'request', local_http)
    panel = Path(__file__).resolve().parents[2] / 'src/clip_platform/ui/app.py'
    at = AppTest.from_file(str(panel), default_timeout=20)
    entry_main = sys.modules['__main__']
    monkeypatch.setitem(sys.modules, '__main__', entry_main)
    at.session_state['active_project'] = project['project_id']
    at.session_state['analysis-' + project['project_id']] = analysis['job_id']
    at.run()
    assert not at.exception
    next(button for button in at.button if button.label == 'Salvar revisão').click().run()
    assert not at.exception
    next(button for button in at.button if button.label == 'Gerar arquivo desta revisão').click().run()
    assert not at.exception
    # AppTest substitui __main__; o worker real roda em outro terminal.
    # Restaurar entrypoint do teste antes do spawn, mantendo essa fronteira.
    sys.modules['__main__'] = entry_main
    done = run_once(store, 'unused')
    assert done.status == 'completed', done.error
    at.run()
    assert not at.exception
    assert len(at.get('download_button')) == 1
