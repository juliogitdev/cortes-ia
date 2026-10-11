"""A manual TikTok link is the user's explicit collection action."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from clip_platform.api.app import create_app
from clip_platform.learning.tiktok_oauth import _account_path, _write_private
from clip_platform.shared.contracts import ClipRevision, MediaAsset


def test_manual_link_collects_only_after_post_and_keeps_gets_local(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    store = app.state.store
    project = store.create_project('Live')
    asset = MediaAsset(asset_id='asset', source_uri='local:test',
        content_hash='sha256:' + '0'*64, duration_s=60,
        tracks=['audio', 'video'], local_path=str(tmp_path / 'source.mp4'))
    store.put_asset(project.project_id, asset)
    store.put_revision(ClipRevision(revision_id='revision', candidate_id='candidate',
        asset_id='asset', boundaries={'start_s': 1, 'end_s': 11}, editor_changes=[]))
    _write_private(_account_path(tmp_path, 'owner'), {
        'open_id': 'owner', 'display_name': 'Conta', 'scopes': ['video.list'],
        'access_token': 'mock', 'refresh_token': 'mock'})
    calls = []
    def fake_query(publication, root):
        calls.append((publication.publication_id, publication.account_open_id))
        return {'views': 42, 'likes': 6, 'comments': 2, 'shares': 1}, 'tiktok:1234567890123456789'
    monkeypatch.setattr('clip_platform.api.app.query_metrics', fake_query)
    body = {'revision_id': 'revision', 'platform': 'tiktok', 'account': 'Conta',
            'account_open_id': 'owner', 'posted_at': datetime.now(timezone.utc).isoformat(),
            'publication_url': 'https://www.tiktok.com/@owner/video/1234567890123456789'}
    with TestClient(app) as client:
        assert client.get('/publications').json() == []
        assert calls == []
        assert client.post('/publications', json=body).status_code == 422
        store.assign_project_account(project.project_id, 'owner')
        assert client.patch(f'/projects/{project.project_id}/tiktok-account',
                            json={'account_open_id': 'unknown'}).status_code == 422
        response = client.post('/publications', json=body)
        assert response.status_code == 201, response.text
        publication_id = response.json()['publication_id']
        assert calls == [(publication_id, 'owner')]
        record = client.get(f'/publications/{publication_id}').json()
        assert record['collections'][0]['status'] == 'completed'
        assert {item['metric_name']: item['value'] for item in record['snapshots']} == {
            'views': 42, 'likes': 6, 'comments': 2, 'shares': 1}
        assert len(client.get('/publications').json()) == 1
        assert len(calls) == 1
        detail_calls = []
        def fake_details(publication, root):
            detail_calls.append(publication.external_video_id or publication.publication_url)
            return ({'views': 11, 'likes': 2, 'comments': 1, 'shares': 0},
                    'tiktok:1234567890123456789', datetime(2026, 1, 2, tzinfo=timezone.utc))
        monkeypatch.setattr('clip_platform.api.app.query_video_details', fake_details)
        by_link = client.post('/publications', json={**body, 'posted_at': None})
        assert by_link.status_code == 201, by_link.text
        second = client.get(f"/publications/{by_link.json()['publication_id']}").json()
        assert second['publication']['posted_at'].startswith('2026-01-02')
        assert len(second['snapshots']) == 4
        assert len(detail_calls) == 1
        assert len(calls) == 1
        _write_private(_account_path(tmp_path, 'other'), {
            'open_id': 'other', 'display_name': 'Outra', 'scopes': ['video.list'],
            'access_token': 'mock', 'refresh_token': 'mock'})
        assert client.patch(f'/projects/{project.project_id}/tiktok-account',
                            json={'account_open_id': 'other'}).status_code == 422


def test_manual_link_requires_video_list_and_full_tiktok_url(tmp_path):
    app = create_app(tmp_path)
    store = app.state.store
    project = store.create_project('Live')
    asset = MediaAsset(asset_id='asset', source_uri='local:test',
        content_hash='sha256:' + '0'*64, duration_s=60,
        tracks=['audio', 'video'], local_path=str(tmp_path / 'source.mp4'))
    store.put_asset(project.project_id, asset)
    store.put_revision(ClipRevision(revision_id='revision', candidate_id='candidate',
        asset_id='asset', boundaries={'start_s': 1, 'end_s': 11}, editor_changes=[]))
    _write_private(_account_path(tmp_path, 'owner'), {
        'open_id': 'owner', 'display_name': 'Conta', 'scopes': ['video.publish'],
        'access_token': 'mock', 'refresh_token': 'mock'})
    store.assign_project_account(project.project_id, 'owner')
    body = {'revision_id': 'revision', 'platform': 'tiktok', 'account': 'Conta',
            'account_open_id': 'owner', 'posted_at': datetime.now(timezone.utc).isoformat(),
            'publication_url': 'https://www.tiktok.com/@owner/video/1234567890123456789'}
    with TestClient(app) as client:
        assert client.post('/publications', json=body).status_code == 422
        _write_private(_account_path(tmp_path, 'owner'), {
            'open_id': 'owner', 'display_name': 'Conta', 'scopes': ['video.list'],
            'access_token': 'mock', 'refresh_token': 'mock'})
        assert client.post('/publications', json={**body,
            'publication_url': 'https://vm.tiktok.com/example'}).status_code == 422
        assert client.get('/publications').json() == []
