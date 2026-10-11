from pathlib import Path
import subprocess

import pytest
from fastapi.testclient import TestClient

from clip_platform.api.app import create_app
from clip_platform.ingestion.download import DownloadRequest, DownloadSettings, identify_provider, download_video
from clip_platform.media.tools import run_tool


@pytest.mark.parametrize(('url', 'provider'), [
    ('https://www.youtube.com/watch?v=y-KdHRZ9Ggo', 'youtube'),
    ('https://youtu.be/y-KdHRZ9Ggo', 'youtube'),
    ('https://vimeo.com/123', 'vimeo'),
    ('https://clips.twitch.tv/example', 'twitch'),
    ('https://www.dailymotion.com/video/123', 'dailymotion'),
    ('https://www.tiktok.com/@creator/video/123', 'tiktok'),
])
def test_provider_registry(url, provider):
    assert identify_provider(url) == provider


@pytest.mark.parametrize('url', [
    'http://youtube.com/watch?v=x', 'https://youtube.com.evil.test/watch?v=x',
    'https://127.0.0.1/video', 'https://localhost/video', 'file:///secret.mp4',
    'https://user:pass@youtube.com/watch?v=x', 'https://example.com/video',
    'https://youtube.com/redirect?q=http://127.0.0.1/',
])
def test_reject_untrusted_url(url):
    with pytest.raises(ValueError):
        identify_provider(url)


def test_quality_settings():
    assert DownloadSettings().format_selector() == 'bestvideo+bestaudio/best'
    assert DownloadSettings(quality='up_to_height', max_height=1080).format_selector().startswith('bestvideo[height<=1080]')
    with pytest.raises(ValueError):
        DownloadSettings(quality='up_to_height').format_selector()


def test_download_uses_best_quality_and_ingests_file(tmp_path, monkeypatch):
    video = tmp_path / 'fixture.mp4'
    run_tool('ffmpeg', ['-v', 'error', '-nostdin', '-f', 'lavfi', '-i',
        'testsrc2=size=160x120:rate=25:duration=1', '-f', 'lavfi', '-i',
        'sine=frequency=440:sample_rate=16000:duration=1', '-c:v', 'libx264',
        '-c:a', 'aac', str(video)])
    original_run = subprocess.run
    def fake_run(command, **kwargs):
        if '-m' not in command or 'yt_dlp' not in command:
            return original_run(command, **kwargs)
        assert '-f' in command and command[command.index('-f') + 1] == 'bestvideo+bestaudio/best'
        assert '--no-playlist' in command and '--js-runtimes' in command
        target = Path(kwargs['cwd']) / 'source.mp4'
        target.write_bytes(video.read_bytes())
        return subprocess.CompletedProcess(command, 0, str(target) + '\n', '')
    monkeypatch.setattr('clip_platform.ingestion.download.subprocess.run', fake_run)
    asset, provider = download_video(DownloadRequest(url='https://youtu.be/y-KdHRZ9Ggo'), tmp_path / 'job' / 'download')
    assert provider == 'youtube' and asset.duration_s > 0
    assert asset.source_uri == 'https://youtu.be/y-KdHRZ9Ggo'
    assert Path(asset.local_path).is_file()
    assert not (tmp_path / 'job' / 'download' / 'source.mp4').exists()


def test_api_queues_download_without_network_and_persists_asset(tmp_path):
    app = create_app(tmp_path / 'storage')
    with TestClient(app) as client:
        project = client.post('/projects', json={'name': 'Vídeo por link'}).json()
        url = 'https://www.youtube.com/watch?v=y-KdHRZ9Ggo'
        endpoint = f"/projects/{project['project_id']}/downloads"
        response = client.post(endpoint, json={'url': url}, headers={'Idempotency-Key': 'link-1'})
        assert response.status_code == 202, response.text
        assert response.json()['kind'] == 'download'
        assert client.post(endpoint, json={'url': url}, headers={'Idempotency-Key': 'link-1'}).json()['job_id'] == response.json()['job_id']
        assert client.post(endpoint, json={'url': 'https://localhost/video'}, headers={'Idempotency-Key': 'bad'}).status_code == 422
        store = app.state.store
        job = store.claim('owner')
        from clip_platform.shared.contracts import MediaAsset
        asset = MediaAsset(asset_id='asset-' + project['project_id'] + '-' + 'a'*64,
            source_uri=url, content_hash='sha256:' + 'a'*64, duration_s=100,
            tracks=['audio', 'video'], local_path=str(store.root / 'dummy.mp4'))
        store.finish(job.job_id, 'owner', asset.model_dump(mode='json'))
        assert store.get_project(project['project_id']).asset_id == asset.asset_id


def test_worker_download_branch_stores_project_asset(tmp_path, monkeypatch):
    app = create_app(tmp_path / 'storage')
    with TestClient(app) as client:
        project = client.post('/projects', json={'name': 'worker'}).json()
        url = 'https://youtu.be/y-KdHRZ9Ggo'
        response = client.post(f"/projects/{project['project_id']}/downloads",
            json={'url': url}, headers={'Idempotency-Key': 'worker-test'})
        assert response.status_code == 202
        store = app.state.store
        job = store.claim('owner')
        from clip_platform.shared.contracts import MediaAsset
        from clip_platform.worker.runner import process_job
        asset = MediaAsset(asset_id='temporary', source_uri=url,
            content_hash='sha256:' + 'b'*64, duration_s=10,
            tracks=['video', 'audio'], local_path=str(store.root / 'test.mp4'))
        monkeypatch.setattr('clip_platform.worker.runner.download_video', lambda request, directory, progress_callback=None: (asset, 'youtube'))
        result = process_job(store, job, 'owner', 'unused', 'cpu', None)
        store.finish(job.job_id, 'owner', result)
        assert store.get_project(project['project_id']).asset_id == result['asset_id']
        assert result['asset_id'].startswith('asset-' + project['project_id'])


def test_panel_can_queue_link_without_session_key_collision(tmp_path, monkeypatch):
    import httpx
    from streamlit.testing.v1 import AppTest
    app = create_app(tmp_path / 'storage')
    with TestClient(app) as client:
        project = client.post('/projects', json={'name': 'link no painel'}).json()
        def local_http(method, url, **kwargs):
            kwargs.pop('timeout', None)
            path = str(url).split('127.0.0.1:8000', 1)[1]
            return client.request(method, path, **kwargs)
        monkeypatch.setattr(httpx, 'request', local_http)
        panel = Path(__file__).resolve().parents[2] / 'src/clip_platform/ui/app.py'
        at = AppTest.from_file(str(panel), default_timeout=20)
        at.session_state['active_project'] = project['project_id']
        at.run()
        assert not at.exception
        next(item for item in at.text_input if item.label.startswith('Link da gravação')).set_value(
            'https://www.youtube.com/watch?v=y-KdHRZ9Ggo')
        next(item for item in at.button if item.label == 'Baixar vídeo').click().run()
        assert not at.exception
        assert at.session_state['download-job-' + project['project_id']]
        assert app.state.store.list_jobs(project['project_id'])[0].kind == 'download'
