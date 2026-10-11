"""Local deletion never calls TikTok or discards publication history."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from clip_platform.api.app import create_app
from clip_platform.shared.contracts import ClipRevision, MediaAsset
from clip_platform.shared.jobs import Export


def test_delete_project_removes_local_media_but_keeps_publication(tmp_path):
    app = create_app(tmp_path)
    store = app.state.store
    project = store.create_project('Live')
    directory = tmp_path / 'projects' / project.project_id
    source = directory / 'assets' / 'original.mp4'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'original')
    exported_path = directory / 'exports' / 'cut.mp4'
    exported_path.parent.mkdir()
    exported_path.write_bytes(b'clip')
    outside = tmp_path / 'outside.mp4'
    outside.write_bytes(b'keep')
    asset = MediaAsset(asset_id='asset', source_uri='local:test',
        content_hash='sha256:' + '0'*64, duration_s=60,
        tracks=['audio', 'video'], local_path=str(source))
    store.put_asset(project.project_id, asset)
    store.put_revision(ClipRevision(revision_id='revision', candidate_id='candidate',
        asset_id='asset', boundaries={'start_s': 1, 'end_s': 11}, editor_changes=[]))
    store.put_export(Export(export_id='export', revision_id='revision', asset_id='asset',
        local_path=str(exported_path), duration_s=10, content_hash=asset.content_hash))
    publication = store.create_publication('revision', 'tiktok', 'Conta',
        datetime.now(timezone.utc), 'https://www.tiktok.com/@owner/video/1234567890123456789',
        account_open_id='owner')
    with TestClient(app) as client:
        response = client.delete(f'/projects/{project.project_id}')
        assert response.status_code == 200, response.text
        assert response.json()['tiktok_publications_untouched'] is True
        assert not directory.exists()
        assert outside.read_bytes() == b'keep'
        assert client.get('/projects').json() == []
        assert client.get(f'/projects/{project.project_id}/jobs').status_code == 404
        assert client.post(f'/projects/{project.project_id}/analyses', json={},
                           headers={'Idempotency-Key': 'again'}).status_code in {404, 422}
        assert client.delete(f'/projects/{project.project_id}').status_code == 200
    assert store.get_publication_record(publication.publication_id).publication.publication_url


def test_delete_project_refuses_pending_job(tmp_path):
    app = create_app(tmp_path)
    store = app.state.store
    project = store.create_project('Live')
    directory = tmp_path / 'projects' / project.project_id
    directory.mkdir(parents=True)
    (directory / 'keep.txt').write_text('local')
    job = store.enqueue(project.project_id, 'analysis', 'pending', {'asset_id': 'asset'})
    with TestClient(app) as client:
        response = client.delete(f'/projects/{project.project_id}')
        assert response.status_code == 422
        assert directory.is_dir()
        assert len(client.get('/projects').json()) == 1
        store.cancel(job.job_id)
        assert client.delete(f'/projects/{project.project_id}').status_code == 200
