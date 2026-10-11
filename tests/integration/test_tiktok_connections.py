import json
from datetime import datetime, timedelta, timezone

import httpx
from fastapi.testclient import TestClient

from clip_platform.api.app import create_app
from clip_platform.learning.tiktok import query_metrics
from clip_platform.learning.tiktok_oauth import (accounts, app_status, exchange_code,
    save_app, _account_path, _write_private)
from clip_platform.shared.contracts import Publication


def test_tiktok_app_configuration_and_oauth_state(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    with TestClient(app, base_url='https://panel.example') as client:
        assert client.get('/integrations/tiktok/app').json()['configured'] is False
        config = {'client_key': 'key_123', 'client_secret': 'private-secret',
                  'redirect_uri': 'https://panel.example/integrations/tiktok/callback'}
        response = client.put('/integrations/tiktok/app', json=config)
        assert response.status_code == 200, response.text
        assert 'private-secret' not in response.text
        assert 'private-secret' not in client.get('/integrations/tiktok/app').text
        assert app_status(tmp_path)['secret_saved']
        start = client.get('/integrations/tiktok/authorize')
        assert start.status_code == 200
        assert start.json()['url'].startswith('https://www.tiktok.com/v2/auth/authorize/')
        assert 'Secure' in start.headers['set-cookie'] and 'HttpOnly' in start.headers['set-cookie']
        assert client.get('/integrations/tiktok/callback?state=wrong&code=example', follow_redirects=False).status_code == 400
        from urllib.parse import parse_qs, urlparse
        state = parse_qs(urlparse(start.json()['url']).query)['state'][0]
        calls = []
        monkeypatch.setattr('clip_platform.api.app.exchange_code', lambda root, code: calls.append(code))
        callback = client.get('/integrations/tiktok/callback', params={'state': state, 'code': 'once'},
                              follow_redirects=False)
        assert callback.status_code == 303 and callback.headers['location'] == '/?tiktok=connected'
        assert calls == ['once']
        assert client.get('/integrations/tiktok/callback', params={'state': state, 'code': 'twice'},
                          follow_redirects=False).status_code == 400
        assert calls == ['once']


def test_two_accounts_are_separate_and_metric_query_uses_selected_account(tmp_path):
    save_app(tmp_path, 'key_123', 'private-secret',
             'https://panel.example/integrations/tiktok/callback')
    def auth_response(request):
        if request.url.path.endswith('/oauth/token/'):
            code = dict(httpx.QueryParams(request.content.decode()))['code']
            return httpx.Response(200, json={'open_id': code, 'access_token': 'token-' + code,
                'refresh_token': 'refresh-' + code, 'scope': 'user.info.basic,video.list',
                'expires_in': 86400})
        if request.url.path.endswith('/user/info/'):
            open_id = request.headers['Authorization'].removeprefix('Bearer token-')
            return httpx.Response(200, json={'error': {'code': 'ok'},
                'data': {'user': {'open_id': open_id, 'display_name': 'Conta ' + open_id}}})
        assert request.headers['Authorization'] == 'Bearer token-second'
        return httpx.Response(200, json={'error': {'code': 'ok'}, 'data': {'videos': [
            {'id': '1234567890123456789', 'view_count': 20, 'like_count': 5,
             'comment_count': 2, 'share_count': 1}]}})
    with httpx.Client(transport=httpx.MockTransport(auth_response)) as client:
        exchange_code(tmp_path, 'first', client)
        exchange_code(tmp_path, 'second', client)
        assert len(accounts(tmp_path)) == 2
        assert 'access_token' not in json.dumps(accounts(tmp_path))
        publication = Publication(publication_id='p', revision_id='r', platform='tiktok',
            account='Conta second', account_open_id='second',
            posted_at=datetime.now(timezone.utc) - timedelta(days=1),
            publication_url='https://www.tiktok.com/@second/video/1234567890123456789')
        values, _ = query_metrics(publication, tmp_path, client)
        assert values['views'] == 20
    assert _account_path(tmp_path, 'first') != _account_path(tmp_path, 'second')
