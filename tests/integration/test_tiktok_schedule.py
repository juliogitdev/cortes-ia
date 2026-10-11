from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from clip_platform.api.app import create_app
from clip_platform.learning.tiktok_oauth import _account_path, _write_private
from clip_platform.learning.tiktok_scheduler import run_once
from clip_platform.shared.contracts import ClipRevision, MediaAsset
from clip_platform.shared.jobs import Export


def test_bulk_schedule_claim_and_cancel(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    store = app.state.store
    project = store.create_project('Live')
    asset = MediaAsset(asset_id='asset', source_uri='local:test',
        content_hash='sha256:' + '0'*64, duration_s=60,
        tracks=['audio', 'video'], local_path=str(tmp_path / 'source.mp4'))
    store.put_asset(project.project_id, asset)
    for index in (1, 2):
        revision = ClipRevision(revision_id=f'revision-{index}', candidate_id=f'candidate-{index}',
            asset_id='asset', boundaries={'start_s': index, 'end_s': index + 10}, editor_changes=[])
        store.put_revision(revision)
        path = tmp_path / f'export-{index}.mp4'
        path.write_bytes(b'mock-mp4')
        store.put_export(Export(export_id=f'export-{index}', revision_id=revision.revision_id,
            asset_id='asset', local_path=str(path), duration_s=10, content_hash=asset.content_hash))
    _write_private(_account_path(tmp_path, 'owner'), {
        'open_id': 'owner', 'display_name': 'Conta 1', 'scopes': ['video.publish'],
        'access_token': 'mock', 'refresh_token': 'mock'})
    store.assign_project_account(project.project_id, 'owner')
    start = datetime.now(timezone.utc) + timedelta(hours=2)
    body = {'batch_id': 'batch-1', 'account_open_id': 'owner', 'mode': 'interval',
            'start_at': start.isoformat(), 'interval_hours': 2, 'consent': True,
            'items': [{'revision_id': f'revision-{index}', 'export_id': f'export-{index}',
                       'caption': f'Parte {index}', 'privacy_level': 'SELF_ONLY'}
                      for index in (1, 2)]}
    with TestClient(app) as client:
        assert client.post('/tiktok-posts/schedule', json={**body, 'consent': False}).status_code == 422
        response = client.post('/tiktok-posts/schedule', json=body)
        assert response.status_code == 202, response.text
        items = response.json()
        assert len(items) == 2
        assert datetime.fromisoformat(items[1]['scheduled_at']) - datetime.fromisoformat(items[0]['scheduled_at']) == timedelta(hours=2)
        assert client.post('/tiktok-posts/schedule', json=body).json() == items
        assert client.delete(f'/projects/{project.project_id}').status_code == 422
        assert run_once(tmp_path, store) is False
        assert client.post(f"/tiktok-posts/{items[1]['attempt_id']}/cancel").json()['status'] == 'cancelled'
        assert client.post(f"/tiktok-posts/{items[1]['attempt_id']}/cancel").status_code == 422
    store._clock = lambda: start.timestamp() + 1
    sent = []
    def fake_post(root, open_id, path, caption, privacy, *settings, on_initialized=None):
        sent.append((path, caption))
        on_initialized('publish-1')
        return 'publish-1'
    monkeypatch.setattr('clip_platform.learning.tiktok_scheduler.direct_post', fake_post)
    monkeypatch.setattr('clip_platform.learning.tiktok_scheduler.fetch_post_status',
                        lambda *args: {'status': 'PUBLISH_COMPLETE', 'post_ids': ['1234567890123456789']})
    assert run_once(tmp_path, store) is True
    assert len(sent) == 1 and sent[0][1] == 'Parte 1'
    assert run_once(tmp_path, store) is False
    assert store.get_tiktok_publish(items[0]['attempt_id']).status == 'completed'
