from fastapi.testclient import TestClient

from clip_platform.api.app import create_app
from clip_platform.learning.tiktok_oauth import _account_path, _write_private
from clip_platform.shared.contracts import ClipRevision, MediaAsset
from clip_platform.shared.jobs import Export


def test_explicit_post_creates_automatic_publication_and_gets_are_local(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    store = app.state.store
    project = store.create_project('Live')
    asset = MediaAsset(asset_id='asset', source_uri='local:test',
        content_hash='sha256:' + '0'*64, duration_s=60,
        tracks=['audio', 'video'], local_path=str(tmp_path / 'source.mp4'))
    store.put_asset(project.project_id, asset)
    revision = ClipRevision(revision_id='revision', candidate_id='candidate',
        asset_id='asset', boundaries={'start_s': 1, 'end_s': 11}, editor_changes=[])
    store.put_revision(revision)
    file_path = tmp_path / 'export.mp4'
    file_path.write_bytes(b'mock-mp4')
    exported = Export(export_id='export', revision_id='revision', asset_id='asset',
        local_path=str(file_path), duration_s=10, content_hash=asset.content_hash)
    store.put_export(exported)
    _write_private(_account_path(tmp_path, 'owner'), {
        'open_id': 'owner', 'display_name': 'Conta 1',
        'scopes': ['video.publish'], 'access_token': 'mock', 'refresh_token': 'mock'})
    store.assign_project_account(project.project_id, 'owner')
    calls = []
    def fake_post(root, open_id, path, caption, privacy, *settings, on_initialized=None):
        calls.append('send')
        on_initialized('publish-1')
        return 'publish-1'
    def fake_status(root, open_id, publish_id):
        calls.append('status')
        return {'status': 'PUBLISH_COMPLETE', 'post_ids': ['1234567890123456789'],
                'fail_reason': None}
    monkeypatch.setattr('clip_platform.api.app.direct_post', fake_post)
    monkeypatch.setattr('clip_platform.api.app.fetch_post_status', fake_status)
    with TestClient(app) as client:
        body = {'request_id': 'explicit-1', 'revision_id': 'revision', 'export_id': 'export',
                'account_open_id': 'owner', 'caption': 'Legenda',
                'privacy_level': 'SELF_ONLY', 'consent': False}
        assert client.post('/tiktok-posts', json=body).status_code == 422
        assert calls == []
        body['consent'] = True
        assert client.post('/tiktok-posts', json=body).status_code == 202
        attempts = client.get('/tiktok-posts').json()
        assert len(attempts) == 1 and attempts[0]['status'] == 'completed'
        publications = client.get('/publications').json()
        assert len(publications) == 1
        assert publications[0]['link_type'] == 'automatic'
        assert publications[0]['external_video_id'] == '1234567890123456789'
        assert client.post('/tiktok-posts', json=body).status_code == 202
        assert len(client.get('/publications').json()) == 1
        assert calls == ['send', 'status']
