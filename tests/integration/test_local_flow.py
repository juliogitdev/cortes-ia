import hashlib
from datetime import datetime, timedelta, timezone
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


def word_transcriber(asset, audio, model, device='cpu'):
    bundle = fake_transcriber(asset, audio, model, device)
    bundle.transcript[0].provenance.settings['words'] = [
        {'text': 'Trecho', 'start_s': .5, 'end_s': .8},
        {'text': 'de', 'start_s': .8, 'end_s': 1.},
        {'text': 'fala', 'start_s': 1., 'end_s': 1.3},
        {'text': 'conhecido', 'start_s': 1.3, 'end_s': 2.},
    ]
    return bundle


def test_subtitles_follow_analysis_into_export(local_setup):
    client, store, project, asset, _ = local_setup
    response = client.post(f"/projects/{project['project_id']}/analyses",
        headers={'Idempotency-Key': 'subtitles-1'}, json={
            'asset_id': asset['asset_id'], 'duration_mode': 'exact', 'target_s': 2.,
            'top_k': 1, 'niche': 'teste', 'subtitle_settings': {
                'enabled': True, 'style': 'yellow_pop', 'position': 'bottom',
                'max_words_per_line': 4, 'font_scale': 1.2,
                'text_color': '#F8F8F8', 'highlight_color': '#FFD900',
                'outline_color': '#101010', 'outline_width': 6}})
    assert response.status_code == 202, response.text
    analysis = run_once(store, 'unused', transcriber=word_transcriber)
    assert analysis.status == 'completed', analysis.error
    assert analysis.result['request']['subtitle_settings']['enabled']
    export = run_once(store, 'unused')
    assert export.status == 'completed', export.error
    result = export.result
    assert Path(result['local_path']).exists()
    assert result['content_hash'] == 'sha256:' + hashlib.sha256(Path(result['local_path']).read_bytes()).hexdigest()
    assert Path(result['local_path']).with_suffix('.export.json').exists()
    assert client.get(f"/exports/{result['export_id']}/download").status_code == 200
    candidate_id = analysis.result['candidates'][0]['candidate_id']
    path = f"/analyses/{analysis.job_id}/candidates/{candidate_id}/subtitles"
    review = client.get(path)
    assert review.status_code == 200 and review.json()['enabled']
    assert review.json()['settings']['highlight_color'] == '#FFD900'
    corrected = review.json()['words']
    invalid = [dict(word) for word in corrected]
    invalid[0]['start_s'] = analysis.result['candidates'][0]['start_s'] - .1
    assert client.put(path, json={'words': invalid}).status_code == 422
    corrected[0]['text'] = 'Correção'
    queued = client.put(path, json={'words': corrected})
    assert queued.status_code == 202, queued.text
    rerendered = run_once(store, 'unused')
    assert rerendered.status == 'completed', rerendered.error
    assert rerendered.result['export_id'] != result['export_id']
    assert Path(result['local_path']).exists()
    assert client.get(path).json()['words'][0]['text'] == 'Correção'
    assert client.get(f"/exports/{rerendered.result['export_id']}/download").status_code == 200
    export_dir = Path(result['local_path']).parent
    assert len(list(export_dir.glob('*.mp4'))) >= 3
    removed = client.delete(f"/analyses/{analysis.job_id}/candidates/{candidate_id}")
    assert removed.status_code == 200, removed.text
    assert not list(export_dir.glob('*.mp4'))
    assert client.get(path).status_code == 404


def test_existing_clip_can_gain_subtitles_without_reanalysis(local_setup):
    client, store, project, asset, _ = local_setup
    queued = enqueue(client, project, asset, key='old-analysis')
    analysis = run_once(store, 'unused', transcriber=word_transcriber)
    assert analysis.status == 'completed', analysis.error
    original = run_once(store, 'unused')
    assert original.status == 'completed', original.error
    candidate_id = analysis.result['candidates'][0]['candidate_id']
    path = f"/analyses/{queued['job_id']}/candidates/{candidate_id}/subtitles"
    review = client.get(path).json()
    assert review['enabled'] is False and review['words']
    request = {'words': review['words'], 'settings': {
        'enabled': True, 'style': 'yellow_pop', 'position': 'bottom',
        'max_words_per_line': 4, 'font_scale': 1.0,
        'text_color': '#FFFFFF', 'highlight_color': '#00FF00',
        'outline_color': '#111111', 'outline_width': 4}}
    response = client.put(path, json=request)
    assert response.status_code == 202, response.text
    subtitled = run_once(store, 'unused')
    assert subtitled.status == 'completed', subtitled.error
    assert subtitled.result['export_id'].startswith('export-subtitle-')
    versions_url = f"/analyses/{queued['job_id']}/candidates/{candidate_id}/media-versions"
    versions = client.get(versions_url)
    assert versions.status_code == 200, versions.text
    variants = versions.json()['variants']
    assert {item['kind'] for item in variants} == {'original', 'captioned'}
    assert versions.json()['selected_export_id'] == subtitled.result['export_id']
    original_id = next(item['export_id'] for item in variants if item['kind'] == 'original')
    assert client.get(f'/exports/{original_id}/download').status_code == 200
    selected = client.put(versions_url.replace('/media-versions', '/media-selection'),
                          json={'export_id': original_id})
    assert selected.status_code == 200 and selected.json()['selected_export_id'] == original_id
    assert client.get(f"/projects/{project['project_id']}/media-versions").json()[0]['selected_export_id'] == original_id
    removed = client.delete(versions_url + '/' + subtitled.result['export_id'])
    assert removed.status_code == 200, removed.text
    assert removed.json()['selected_export_id'] == original_id
    assert client.get(f"/exports/{subtitled.result['export_id']}/download").status_code == 404
    assert client.get(f'/exports/{original_id}/download').status_code == 200
    assert client.delete(versions_url + '/' + original_id).status_code == 422
    assert client.get(path).json()['enabled'] is True
    assert client.get(path).json()['settings']['highlight_color'] == '#00FF00'
    review['words'][0]['text'] = 'Depois'
    assert client.put(path, json={'words': review['words']}).status_code == 202
    assert run_once(store, 'unused').status == 'completed'


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
    automatic = client.post(f"/analyses/{job['job_id']}/exports")
    assert automatic.status_code == 200 and len(automatic.json()) == 1
    assert client.post(f"/analyses/{job['job_id']}/exports").json()[0]['job_id'] == automatic.json()[0]['job_id']
    auto_done = run_once(store, 'unused')
    assert auto_done.status == 'completed', auto_done.error
    assert auto_done.job_id == automatic.json()[0]['job_id']
    preview = client.get(f"/exports/{auto_done.result['export_id']}/media")
    assert preview.status_code == 200 and preview.headers['content-type'].startswith('video/mp4')
    thumbnail = client.get(f"/exports/{auto_done.result['export_id']}/thumbnail")
    assert thumbnail.status_code == 200 and thumbnail.content.startswith(b'\xff\xd8\xff')
    assert client.get(f"/exports/{auto_done.result['export_id']}/thumbnail").content == thumbnail.content
    assert abs(auto_done.result['duration_s'] - 2.) <= .2
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


def test_publication_and_manual_metric_do_not_collect_automatically(local_setup):
    client, store, project, asset, _ = local_setup
    analysis = enqueue(client, project, asset)
    assert run_once(store, 'unused', transcriber=fake_transcriber).status == 'completed'
    export_job = client.post(f"/analyses/{analysis['job_id']}/exports").json()[0]
    revision_id = export_job['payload']['revision_id']
    posted_at = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    response = client.post('/publications', json={'revision_id': revision_id,
        'platform': 'youtube', 'account': 'canal', 'posted_at': posted_at,
        'publication_url': 'https://youtube.com/watch?v=example'})
    assert response.status_code == 201, response.text
    publication_id = response.json()['publication_id']
    record = client.get(f'/publications/{publication_id}').json()
    assert record['collections'] == [] and record['snapshots'] == []
    assert client.get('/publications').json()[0]['publication_id'] == publication_id
    metric = client.post(f'/publications/{publication_id}/metrics', json={
        'metric_name': 'views', 'value': 123, 'reviewer': 'operador'})
    assert metric.status_code == 201, metric.text
    assert metric.json()['source'] == 'manual' and metric.json()['age_hours'] >= 48
    assert client.get(f'/publications/{publication_id}').json()['snapshots'][0]['value'] == 123
    assert client.post(f'/publications/{publication_id}/metrics', json={
        'metric_name': 'views', 'value': -1, 'reviewer': 'operador'}).status_code == 422
    assert client.post('/publications', json={'revision_id': revision_id,
        'platform': 'youtube', 'account': 'canal', 'posted_at': posted_at,
        'publication_url': 'file:///local'}).status_code == 422


def test_project_rename_and_observable_signals(local_setup):
    client, store, project, asset, original = local_setup
    renamed = client.patch(f"/projects/{project['project_id']}", json={'name': 'Nova biblioteca'})
    assert renamed.status_code == 200
    assert store.get_project(project['project_id']).name == 'Nova biblioteca'
    analysis = enqueue(client, project, asset, 'signals-analysis')
    done = run_once(store, 'unused', transcriber=fake_transcriber)
    assert done.status == 'completed', done.error
    result = store.get_analysis(analysis['job_id'])
    assert result.evidence.provenance
    assert any(item.run_id == 'audio_energy_v1' for item in result.evidence.provenance)
    assert any(item.run_id == 'frame_change_v1' for item in result.evidence.provenance)


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


def test_feedback_and_delete_cut_preserve_original_and_history(local_setup):
    client, store, project, asset, original = local_setup
    analysis = enqueue(client, project, asset, 'feedback-and-delete')
    assert run_once(store, 'unused', transcriber=fake_transcriber).status == 'completed'
    auto = run_once(store, 'unused')
    assert auto.status == 'completed', auto.error
    candidate = store.get_analysis(analysis['job_id']).candidates[0]
    feedback_path = f"/analyses/{analysis['job_id']}/candidates/{candidate.candidate_id}/feedback"
    response = client.post(feedback_path, json={'rating': 'useful', 'note': 'Bom começo, final precisa de contexto.'})
    assert response.status_code == 201, response.text
    assert client.get(feedback_path).json()[0]['rating'] == 'useful'
    export_id = auto.result['export_id']
    exported_path = Path(auto.result['local_path'])
    assert exported_path.exists()
    revised = client.post(f"/candidates/{candidate.candidate_id}/revisions", json={
        'analysis_id': analysis['job_id'], 'start_s': candidate.start_s,
        'end_s': candidate.end_s, 'editor_changes': ['Revisão manual']})
    assert revised.status_code == 201, revised.text
    manual_request = client.post(f"/revisions/{revised.json()['revision_id']}/exports",
        headers={'Idempotency-Key': 'manual-export-before-delete'})
    assert manual_request.status_code == 202, manual_request.text
    manual = run_once(store, 'unused')
    assert manual.status == 'completed', manual.error
    manual_path = Path(manual.result['local_path'])
    assert manual_path.exists() and manual_path != exported_path
    publication = store.create_publication(auto.result['revision_id'], 'tiktok', 'Conta',
        datetime.now(timezone.utc), 'https://www.tiktok.com/@conta/video/1234567890123456789')
    response = client.delete(f"/analyses/{analysis['job_id']}/candidates/{candidate.candidate_id}")
    assert response.status_code == 200, response.text
    assert response.json()['removed_exports'] == 2
    assert not exported_path.exists()
    assert not manual_path.exists()
    assert store.get_publication_record(publication.publication_id).publication.publication_url.endswith('1234567890123456789')
    assert not exported_path.with_suffix('.export.json').exists()
    assert original.exists() and Path(asset['local_path']).exists()
    assert store.get_analysis(analysis['job_id']).candidates[0].candidate_id == candidate.candidate_id
    assert client.get(feedback_path).json()[0]['note'].startswith('Bom começo')
    assert client.get(f'/exports/{export_id}/media').status_code == 404
    assert client.post(f"/analyses/{analysis['job_id']}/exports").json() == []
    assert client.delete(f"/analyses/{analysis['job_id']}/candidates/{candidate.candidate_id}").status_code == 200
    assert run_once(store, 'unused') is None


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
    assert run_once(store, 'unused').status == 'completed'  # corte automático pronto

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
    assert len(at.get('link_button')) == 1
    next(button for button in at.button if button.label == 'Detalhes').click().run()
    assert not at.exception
    next(button for button in at.button if button.label == 'Salvar feedback').click().run()
    assert not at.exception
    candidate = store.get_analysis(analysis['job_id']).candidates[0]
    assert store.list_feedback(analysis['job_id'], candidate.candidate_id)[0].rating == 'useful'
    next(radio for radio in at.radio if radio.label == 'Navegação').set_value('Visão geral').run()
    assert not at.exception
    assert len(at.metric) == 4
    next(radio for radio in at.radio if radio.label == 'Navegação').set_value('Projetos').run()
    assert not at.exception
    next(button for button in at.button if button.label == 'Renomear projeto').click().run()
    assert not at.exception
