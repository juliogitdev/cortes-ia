"""Editorial folders and clip notes stay local and persist across requests."""
from fastapi.testclient import TestClient
from types import SimpleNamespace
from io import BytesIO
from PIL import Image

from clip_platform.api.app import create_app
from clip_platform.shared.contracts import MediaAsset


def test_profile_branding_url_and_avatar_are_local(tmp_path, monkeypatch):
    monkeypatch.setattr('httpx.get', lambda *args, **kwargs: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {'author_name': 'Canal de cortes'}))
    with TestClient(create_app(tmp_path)) as client:
        profile = client.post('/profiles', json={'name': 'Perfil', 'platforms': ['tiktok']}).json()
        profile_id = profile['profile_id']
        saved = client.put(f'/profiles/{profile_id}/branding', json={
            'tiktok_url': 'https://www.tiktok.com/@meucanal', 'brand_name': ''})
        assert saved.status_code == 200
        assert saved.json()['brand_name'] == 'Canal de cortes'
        assert client.put(f'/profiles/{profile_id}/branding', json={
            'tiktok_url': 'https://example.com/@meucanal', 'brand_name': ''}).status_code == 422
        image = Image.new('RGB', (80, 80), 'red')
        data = BytesIO(); image.save(data, format='PNG')
        uploaded = client.put(f'/profiles/{profile_id}/avatar', content=data.getvalue(),
                              headers={'content-type': 'image/png'})
        assert uploaded.status_code == 200
        assert uploaded.json()['avatar_version'] == 1
        assert client.get(f'/profiles/{profile_id}/avatar').headers['content-type'] == 'image/png'


def test_authorized_tiktok_avatar_is_cached_only_from_tiktok_cdn(tmp_path, monkeypatch):
    image = Image.new('RGB', (90, 90), 'blue')
    data = BytesIO(); image.save(data, format='JPEG')
    monkeypatch.setattr('clip_platform.api.app.account', lambda *_: {
        'avatar_url': 'https://p19-sign.tiktokcdn-us.com/photo.jpeg'})
    monkeypatch.setattr('httpx.get', lambda *args, **kwargs: SimpleNamespace(
        raise_for_status=lambda: None, content=data.getvalue()))
    with TestClient(create_app(tmp_path)) as client:
        profile = client.post('/profiles', json={'name': 'Perfil', 'platforms': ['tiktok']}).json()
        result = client.put(f"/profiles/{profile['profile_id']}", json={
            'name': 'Perfil', 'platforms': ['tiktok'], 'account_open_id': 'linked-account'})
        assert result.status_code == 200
        assert result.json()['avatar_version'] == 1
        assert client.get(f"/profiles/{profile['profile_id']}/avatar").status_code == 200


def test_profiles_organize_lives_without_social_connection(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        profile = client.post('/profiles', json={
            'name': 'Canal principal', 'platforms': ['tiktok', 'instagram'],
            'account_open_id': None}).json()
        assert profile['platforms'] == ['instagram', 'tiktok']
        project = client.post('/projects', json={'name': 'Live de sábado'}).json()
        assigned = client.patch(f"/projects/{project['project_id']}/profile",
            json={'profile_id': profile['profile_id']})
        assert assigned.status_code == 200
        assert assigned.json()['profile_id'] == profile['profile_id']
        assert client.get('/projects').json()[0]['profile_id'] == profile['profile_id']
        assert len(client.get('/profiles').json()) == 1
        assert client.patch(f"/projects/{project['project_id']}/profile",
            json={'profile_id': 'missing'}).status_code == 404
        assert client.put(f"/profiles/{profile['profile_id']}", json={
            'name': 'Canal atualizado', 'platforms': ['instagram'],
            'account_open_id': None}).json()['name'] == 'Canal atualizado'
        deleted = client.delete(f"/profiles/{profile['profile_id']}")
        assert deleted.status_code == 200
        assert deleted.json()['lives_untouched'] is True
        assert client.get('/profiles').json() == []
        assert client.get('/projects').json()[0]['profile_id'] is None


def test_source_thumbnail_is_cached_inside_media_directory(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    store = app.state.store
    project = store.create_project('Live')
    source = tmp_path / 'projects' / project.project_id / 'assets' / 'source.mp4'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'media')
    asset = MediaAsset(asset_id='source-asset', source_uri='local:test',
        content_hash='sha256:' + '0' * 64, duration_s=30,
        tracks=['audio', 'video'], local_path=str(source))
    store.put_asset(project.project_id, asset)
    calls = []
    def fake_ffmpeg(_, args, timeout):
        calls.append(args)
        from pathlib import Path
        Path(args[-1]).write_bytes(b'jpeg')
    monkeypatch.setattr('clip_platform.api.app.run_tool', fake_ffmpeg)
    with TestClient(app) as client:
        for _ in range(2):
            response = client.get('/assets/source-asset/thumbnail')
            assert response.status_code == 200 and response.content == b'jpeg'
    assert len(calls) == 1


def test_clip_editorial_persists_and_rejects_unknown_candidate(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    monkeypatch.setattr(app.state.store, 'get_analysis', lambda _id: SimpleNamespace(
        candidates=[SimpleNamespace(candidate_id='clip-1')]))
    with TestClient(app) as client:
        path = '/analyses/analysis-1/candidates/clip-1/editorial'
        assert client.get(path).json()['status'] == 'draft'
        saved = client.put(path, json={'analysis_id': 'analysis-1',
            'candidate_id': 'clip-1', 'caption': 'Texto para publicação',
            'status': 'review'})
        assert saved.status_code == 200, saved.text
        assert client.get(path).json()['caption'] == 'Texto para publicação'
        assert client.get('/analyses/analysis-1/candidates/other/editorial').status_code == 404
        assert client.put(path, json={'analysis_id': 'wrong',
            'candidate_id': 'clip-1', 'caption': '', 'status': 'draft'}).status_code == 422


def test_repeated_download_request_reuses_active_job(tmp_path):
    app = create_app(tmp_path)
    store = app.state.store
    project = store.create_project('Live')
    request = {'url': 'https://www.youtube.com/watch?v=ZpmIotBzW-o',
               'settings': {'quality': 'best', 'max_height': None}}
    first = store.enqueue(project.project_id, 'download', 'first-click', request)
    second = store.enqueue(project.project_id, 'download', 'second-click', request)
    assert first.job_id == second.job_id
    assert len(store.list_jobs(project.project_id)) == 1


def test_new_live_inherits_profile_and_account_atomically(tmp_path):
    app = create_app(tmp_path)
    store = app.state.store
    profile = store.create_profile('Canal A', ['tiktok'], 'tiktok-a')
    with TestClient(app) as client:
        response = client.post('/projects', json={'name': 'Live A',
            'profile_id': profile.profile_id})
        assert response.status_code == 201
        assert response.json()['profile_id'] == profile.profile_id
        assert response.json()['account_open_id'] == 'tiktok-a'
        assert client.post('/projects', json={'name': 'Inválida',
            'profile_id': 'missing'}).status_code == 404
        assert len(client.get('/projects').json()) == 1
    store.update_profile(profile.profile_id, 'Canal A', ['tiktok'], 'tiktok-b')
    assert store.get_project(response.json()['project_id']).account_open_id == 'tiktok-b'


def test_metric_collection_is_limited_to_selected_profile(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    store = app.state.store
    profile = store.create_profile('Canal A', ['tiktok'])
    project = store.create_project('Live A', profile_id=profile.profile_id)
    monkeypatch.setattr('clip_platform.api.app.connection_status', lambda _root: {'connected': True})
    monkeypatch.setattr(store, 'list_publications', lambda: [SimpleNamespace(
        revision_id='revision-a', publication_id='post-a', platform='tiktok',
        external_video_id='1234567890123456789', publication_url='https://example.org')])
    monkeypatch.setattr(store, 'project_for_revision', lambda _id: project)
    with TestClient(app) as client:
        response = client.post('/publications/collect-session', json={
            'request_id': 'scope-test', 'trigger': 'explicit_user_action',
            'profile_id': 'another-profile'})
        assert response.status_code == 202
        assert response.json() == []
