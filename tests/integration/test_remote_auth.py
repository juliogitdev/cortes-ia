from fastapi.testclient import TestClient

from clip_platform.api.app import create_app
from clip_platform.api.remote import BasicAuthGate


def test_remote_gate_protects_panel_and_api(tmp_path):
    app = BasicAuthGate(create_app(tmp_path), 'admin', 'known-test-secret')
    with TestClient(app) as client:
        assert client.get('/projects').status_code == 401
        assert client.get('/projects', auth=('admin', 'wrong')).status_code == 401
        assert client.get('/projects', auth=('admin', 'known-test-secret')).status_code == 200
        assert client.get('/health', auth=('admin', 'known-test-secret')).status_code == 200
        assert client.post('/projects', json={'name': 'Remoto'}, auth=('admin', 'known-test-secret')).status_code == 201
        assert len(client.get('/projects', auth=('admin', 'known-test-secret')).json()) == 1
