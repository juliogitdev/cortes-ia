"""Server-side TikTok Login Kit configuration and per-account credentials."""
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import time
from threading import RLock
from urllib.parse import urlencode, urlparse

import httpx


AUTHORIZE_URL = 'https://www.tiktok.com/v2/auth/authorize/'
TOKEN_URL = 'https://open.tiktokapis.com/v2/oauth/token/'
USER_URL = 'https://open.tiktokapis.com/v2/user/info/'
_LOCK = RLock()


@contextmanager
def token_file_lock(path):
    """Serialize refreshes across local and tunnel API processes."""
    lock_path = path.with_suffix('.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+b') as handle:
        handle.seek(0)
        if not handle.read(1):
            handle.seek(0)
            handle.write(b'0')
            handle.flush()
        if os.name == 'nt':
            import msvcrt
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(.05)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class TikTokOAuthError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _integration_dir(root):
    return Path(root) / 'integrations'


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None


def _write_private(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def app_config(root):
    return _read_json(_integration_dir(root) / 'tiktok-app.json')


def app_status(root):
    config = app_config(root)
    return {'configured': bool(config),
            'client_key': config.get('client_key', '') if config else '',
            'redirect_uri': config.get('redirect_uri', '') if config else '',
            'secret_saved': bool(config and config.get('client_secret')),
            'request_publish_scope': bool(config and config.get('request_publish_scope'))}


def save_app(root, client_key, client_secret, redirect_uri, request_publish_scope=False):
    parsed = urlparse(redirect_uri)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or
            parsed.query or parsed.fragment or parsed.path != '/integrations/tiktok/callback' or
            len(redirect_uri) >= 512):
        raise TikTokOAuthError('invalid_redirect_uri')
    if not re.fullmatch(r'[A-Za-z0-9_-]{3,150}', client_key):
        raise TikTokOAuthError('invalid_client_key')
    existing = app_config(root) or {}
    if existing.get('client_key') != client_key and not client_secret:
        raise TikTokOAuthError('client_secret_required')
    secret = client_secret or existing.get('client_secret')
    if not secret or len(secret) > 500:
        raise TikTokOAuthError('client_secret_required')
    with _LOCK:
        _write_private(_integration_dir(root) / 'tiktok-app.json', {
            'client_key': client_key, 'client_secret': secret,
            'redirect_uri': redirect_uri, 'request_publish_scope': bool(request_publish_scope)})
    return app_status(root)


def _account_path(root, open_id):
    return _integration_dir(root) / 'tiktok-accounts' / (sha256(open_id.encode()).hexdigest() + '.json')


def account(root, open_id):
    if not open_id or len(open_id) > 200:
        return None
    data = _read_json(_account_path(root, open_id))
    return data if data and data.get('open_id') == open_id else None


def accounts(root):
    directory = _integration_dir(root) / 'tiktok-accounts'
    results = []
    for path in directory.glob('*.json'):
        data = _read_json(path)
        if data and data.get('open_id'):
            results.append({'open_id': data['open_id'],
                            'display_name': data.get('display_name') or data['open_id'],
                            'scopes': data.get('scopes', []),
                            'connected_at': data.get('connected_at')})
    return sorted(results, key=lambda item: item['display_name'].casefold())


def authorization_url(root, state):
    config = app_config(root)
    if not config:
        raise TikTokOAuthError('app_not_configured')
    scopes = ['user.info.basic', 'video.list']
    if config.get('request_publish_scope'):
        scopes.append('video.publish')
    return AUTHORIZE_URL + '?' + urlencode({
        'client_key': config['client_key'], 'response_type': 'code',
        'scope': ','.join(scopes), 'redirect_uri': config['redirect_uri'], 'state': state})


def exchange_code(root, code, client=None):
    config = app_config(root)
    if not config:
        raise TikTokOAuthError('app_not_configured')
    owned = client is None
    client = client or httpx.Client(timeout=12, follow_redirects=False)
    try:
        try:
            response = client.post(TOKEN_URL, data={
                'client_key': config['client_key'], 'client_secret': config['client_secret'],
                'code': code, 'grant_type': 'authorization_code',
                'redirect_uri': config['redirect_uri']})
            response.raise_for_status()
            token = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TikTokOAuthError('token_exchange_failed') from exc
        if not all(token.get(key) for key in ('open_id', 'access_token', 'refresh_token')):
            raise TikTokOAuthError('token_exchange_failed')
        scopes = [scope.strip() for scope in token.get('scope', '').split(',') if scope.strip()]
        if 'user.info.basic' not in scopes:
            raise TikTokOAuthError('profile_scope_missing')
        try:
            profile_response = client.get(USER_URL, params={'fields': 'open_id,display_name,avatar_url'},
                                          headers={'Authorization': 'Bearer ' + token['access_token']})
            profile_response.raise_for_status()
            profile = profile_response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TikTokOAuthError('profile_request_failed') from exc
        if profile.get('error', {}).get('code') != 'ok':
            raise TikTokOAuthError('profile_request_failed')
        user = profile.get('data', {}).get('user', {})
        if user.get('open_id') != token['open_id']:
            raise TikTokOAuthError('profile_mismatch')
        now = datetime.now(timezone.utc)
        entry = {'open_id': token['open_id'], 'display_name': user.get('display_name') or token['open_id'],
                 'avatar_url': user.get('avatar_url') or '',
                 'scopes': scopes, 'access_token': token['access_token'],
                 'refresh_token': token['refresh_token'],
                 'expires_at': (now + timedelta(seconds=int(token.get('expires_in', 86400)))).isoformat(),
                 'connected_at': now.isoformat()}
        with _LOCK:
            _write_private(_account_path(root, entry['open_id']), entry)
        return {'open_id': entry['open_id'], 'display_name': entry['display_name'],
                'scopes': scopes, 'connected_at': entry['connected_at']}
    finally:
        if owned:
            client.close()


def disconnect(root, open_id):
    data = account(root, open_id)
    if not data:
        raise TikTokOAuthError('account_not_found')
    with _LOCK:
        _account_path(root, open_id).unlink(missing_ok=True)
