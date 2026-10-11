"""Consulta autorizada das métricas de vídeos próprios via TikTok Display API."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

import httpx
from clip_platform.learning.tiktok_oauth import account, accounts, app_config, _account_path, _write_private, _LOCK, token_file_lock

VIDEO_URL = re.compile(r'^https://(?:www\.)?tiktok\.com/@[A-Za-z0-9._]+/video/(\d{10,25})(?:[/?#].*)?$')
QUERY_URL = 'https://open.tiktokapis.com/v2/video/query/'
TOKEN_URL = 'https://open.tiktokapis.com/v2/oauth/token/'
FIELDS = 'id,create_time,view_count,like_count,comment_count,share_count'
METRICS = {'view_count': 'views', 'like_count': 'likes',
           'comment_count': 'comments', 'share_count': 'shares'}


class TikTokCollectionError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def auth_path(storage_root: Path) -> Path:
    return Path(storage_root) / 'integrations' / 'tiktok.json'


def connection_status(storage_root: Path) -> dict:
    linked = [item for item in accounts(storage_root) if 'video.list' in item['scopes']]
    if linked:
        return {'connected': True, 'reason': None, 'accounts': len(linked)}
    path = auth_path(storage_root)
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {'connected': False,
                'reason': 'authorization_required' if app_config(storage_root) else 'developer_app_required',
                'accounts': 0}
    connected = bool(data.get('access_token') or
                     all(data.get(key) for key in ('client_key', 'client_secret', 'refresh_token')))
    return {'connected': connected, 'reason': None if connected else 'authorization_required', 'accounts': 0}


def _read_token(path: Path, client: httpx.Client, credentials=None) -> str:
    with _LOCK, token_file_lock(path):
        return _read_token_locked(path, client, credentials)


def _read_token_locked(path: Path, client: httpx.Client, credentials=None) -> str:
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise TikTokCollectionError('not_connected') from exc
    expires_at = data.get('expires_at')
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except ValueError as exc:
            raise TikTokCollectionError('invalid_token_config') from exc
        if exp.tzinfo is None:
            raise TikTokCollectionError('invalid_token_config')
        expired = exp <= datetime.now(timezone.utc) + timedelta(minutes=2)
    else:
        expired = False
    if expired:
        credentials = credentials or data
        if not all(credentials.get(key) for key in ('client_key', 'client_secret')) or not data.get('refresh_token'):
            raise TikTokCollectionError('token_expired')
        try:
            response = client.post(TOKEN_URL, data={
                'client_key': credentials['client_key'], 'client_secret': credentials['client_secret'],
                'grant_type': 'refresh_token', 'refresh_token': data['refresh_token'],
            })
            response.raise_for_status()
            refreshed = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TikTokCollectionError('token_refresh_failed') from exc
        if not refreshed.get('access_token') or not refreshed.get('refresh_token'):
            raise TikTokCollectionError('token_refresh_failed')
        if data.get('open_id') and refreshed.get('open_id') != data['open_id']:
            raise TikTokCollectionError('token_refresh_failed')
        data.update(access_token=refreshed['access_token'],
                    refresh_token=refreshed['refresh_token'],
                    expires_at=(datetime.now(timezone.utc) +
                                timedelta(seconds=int(refreshed.get('expires_in', 86400)))).isoformat())
        _write_private(path, data)
    token = data.get('access_token')
    if not isinstance(token, str) or not token:
        raise TikTokCollectionError('not_connected')
    return token


def query_video_details(publication, storage_root: Path, client: httpx.Client | None = None) -> tuple[dict[str, int], str, datetime | None]:
    if publication.platform.lower() != 'tiktok':
        raise TikTokCollectionError('unsupported_platform')
    if publication.external_video_id and re.fullmatch(r'\d{10,25}', publication.external_video_id):
        video_id = publication.external_video_id
    else:
        match = VIDEO_URL.fullmatch(publication.publication_url or '')
        if not match:
            raise TikTokCollectionError('video_id_unavailable')
        video_id = match.group(1)
    owned = client is None
    client = client or httpx.Client(timeout=12, follow_redirects=False)
    try:
        if publication.account_open_id:
            linked = account(storage_root, publication.account_open_id)
            if not linked:
                raise TikTokCollectionError('account_not_linked')
            if 'video.list' not in linked.get('scopes', []):
                raise TikTokCollectionError('scope_not_authorized')
            token = _read_token(_account_path(storage_root, publication.account_open_id),
                                client, app_config(storage_root))
        elif accounts(storage_root):
            raise TikTokCollectionError('account_not_linked')
        else:
            token = _read_token(auth_path(storage_root), client)
        try:
            response = client.post(QUERY_URL, params={'fields': FIELDS},
                headers={'Authorization': f'Bearer {token}'},
                json={'filters': {'video_ids': [video_id]}})
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TikTokCollectionError('tiktok_request_failed') from exc
        if payload.get('error', {}).get('code') != 'ok':
            raise TikTokCollectionError('tiktok_api_error')
        videos = payload.get('data', {}).get('videos', [])
        video = next((item for item in videos if str(item.get('id')) == video_id), None)
        if video is None:
            raise TikTokCollectionError('video_not_accessible')
        values = {name: video[key] for key, name in METRICS.items()
                  if type(video.get(key)) is int and video[key] >= 0}
        if not values:
            raise TikTokCollectionError('metrics_unavailable')
        create_time = video.get('create_time')
        posted_at = None
        if type(create_time) is int and create_time > 0:
            try:
                posted_at = datetime.fromtimestamp(create_time, timezone.utc)
            except (OverflowError, OSError, ValueError):
                pass
        return values, 'tiktok:' + video_id, posted_at
    finally:
        if owned:
            client.close()


def query_metrics(publication, storage_root: Path, client: httpx.Client | None = None) -> tuple[dict[str, int], str]:
    values, reference, _ = query_video_details(publication, storage_root, client)
    return values, reference
