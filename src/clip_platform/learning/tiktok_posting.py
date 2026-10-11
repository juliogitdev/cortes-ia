"""TikTok public-video discovery and explicit Direct Post transport."""
from contextlib import contextmanager
from pathlib import Path
import re
from urllib.parse import urlsplit

import httpx

from clip_platform.learning.tiktok import _read_token, TikTokCollectionError
from clip_platform.learning.tiktok_oauth import account, app_config, _account_path


LIST_URL = 'https://open.tiktokapis.com/v2/video/list/'
CREATOR_URL = 'https://open.tiktokapis.com/v2/post/publish/creator_info/query/'
INIT_URL = 'https://open.tiktokapis.com/v2/post/publish/video/init/'
STATUS_URL = 'https://open.tiktokapis.com/v2/post/publish/status/fetch/'
LIST_FIELDS = 'id,title,video_description,create_time,duration,cover_image_url,share_url'
CHUNK_SIZE = 10_000_000
MAX_BYTES = 4_000_000_000


class TikTokPostingError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@contextmanager
def _client(client):
    if client is not None:
        yield client
    else:
        with httpx.Client(timeout=httpx.Timeout(30, read=120), follow_redirects=False) as created:
            yield created


def _authorized(root, open_id, scope, client):
    linked = account(root, open_id)
    if not linked:
        raise TikTokPostingError('account_not_linked')
    if scope not in linked.get('scopes', []):
        raise TikTokPostingError('scope_not_authorized')
    config = app_config(root)
    if not config:
        raise TikTokPostingError('app_not_configured')
    try:
        return _read_token(_account_path(root, open_id), client, config)
    except TikTokCollectionError as exc:
        raise TikTokPostingError(exc.code) from exc


def _post_json(client, url, token, data=None, params=None):
    try:
        response = client.post(url, headers={'Authorization': 'Bearer ' + token},
                               json=data or {}, params=params)
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise TikTokPostingError('tiktok_request_failed') from exc
    code = payload.get('error', {}).get('code')
    if code != 'ok':
        raise TikTokPostingError(code if isinstance(code, str) and
            re.fullmatch(r'[a-z][a-z0-9_]{1,70}', code) else 'tiktok_api_error')
    if not 200 <= response.status_code < 300:
        raise TikTokPostingError('tiktok_request_failed')
    return payload.get('data', {})


def _safe_public_url(raw, required_domain=None):
    if not isinstance(raw, str):
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            return None
        if required_domain and parsed.hostname not in {required_domain, 'www.' + required_domain}:
            return None
    except ValueError:
        return None
    return raw


def list_videos(root, open_id, cursor=None, client=None):
    with _client(client) as http:
        token = _authorized(root, open_id, 'video.list', http)
        data = {'max_count': 20}
        if cursor is not None:
            data['cursor'] = cursor
        result = _post_json(http, LIST_URL, token, data, {'fields': LIST_FIELDS})
        videos = []
        for item in result.get('videos', []):
            video_id = str(item.get('id', ''))
            if not re.fullmatch(r'\d{10,25}', video_id):
                continue
            videos.append({'id': video_id, 'title': str(item.get('title') or '')[:300],
                'description': str(item.get('video_description') or '')[:500],
                'create_time': item.get('create_time') if type(item.get('create_time')) is int else None,
                'duration': item.get('duration') if type(item.get('duration')) is int else None,
                'cover_image_url': _safe_public_url(item.get('cover_image_url')),
                'share_url': _safe_public_url(item.get('share_url'), 'tiktok.com')})
        return {'videos': videos, 'cursor': result.get('cursor'),
                'has_more': result.get('has_more') is True}


def creator_info(root, open_id, client=None):
    with _client(client) as http:
        token = _authorized(root, open_id, 'video.publish', http)
        result = _post_json(http, CREATOR_URL, token)
    allowed = {'PUBLIC_TO_EVERYONE', 'MUTUAL_FOLLOW_FRIENDS', 'FOLLOWER_OF_CREATOR', 'SELF_ONLY'}
    return {'creator_username': str(result.get('creator_username') or ''),
            'creator_nickname': str(result.get('creator_nickname') or ''),
            'privacy_level_options': [option for option in result.get('privacy_level_options', [])
                                      if option in allowed],
            'comment_disabled': result.get('comment_disabled') is True,
            'duet_disabled': result.get('duet_disabled') is True,
            'stitch_disabled': result.get('stitch_disabled') is True,
            'max_video_post_duration_sec': result.get('max_video_post_duration_sec')}


def _checked_upload_url(raw):
    try:
        parsed = urlsplit(raw)
        valid = (parsed.scheme == 'https' and not parsed.username and not parsed.password and
            not parsed.port and parsed.hostname and re.fullmatch(
                r'(?:open-upload|upload(?:\.[a-z0-9-]+)?)\.tiktokapis\.com', parsed.hostname))
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise TikTokPostingError('invalid_upload_url')
    return raw


def direct_post(root, open_id, file_path, caption, privacy_level,
                disable_comment=False, disable_duet=False, disable_stitch=False,
                client=None, on_initialized=None):
    file_path = Path(file_path)
    size = file_path.stat().st_size
    if size <= 0 or size > MAX_BYTES or file_path.suffix.lower() != '.mp4':
        raise TikTokPostingError('invalid_video_file')
    if len(caption.encode('utf-16-le')) // 2 > 2200:
        raise TikTokPostingError('caption_too_long')
    with _client(client) as http:
        token = _authorized(root, open_id, 'video.publish', http)
        info = creator_info(root, open_id, http)
        if privacy_level not in info['privacy_level_options']:
            raise TikTokPostingError('privacy_level_option_mismatch')
        if type(info['max_video_post_duration_sec']) is int:
            from clip_platform.media.tools import av_metadata
            duration, _ = av_metadata(file_path)
            if duration > info['max_video_post_duration_sec']:
                raise TikTokPostingError('video_too_long_for_account')
        chunk = min(size, CHUNK_SIZE)
        count = max(1, size // chunk)
        result = _post_json(http, INIT_URL, token, {
            'post_info': {'title': caption, 'privacy_level': privacy_level,
                          'disable_comment': disable_comment or info['comment_disabled'],
                          'disable_duet': disable_duet or info['duet_disabled'],
                          'disable_stitch': disable_stitch or info['stitch_disabled'],
                          'brand_content_toggle': False, 'brand_organic_toggle': False},
            'source_info': {'source': 'FILE_UPLOAD', 'video_size': size,
                            'chunk_size': chunk, 'total_chunk_count': count}})
        publish_id = result.get('publish_id')
        if not isinstance(publish_id, str) or not publish_id:
            raise TikTokPostingError('publish_id_missing')
        if on_initialized:
            on_initialized(publish_id)
        upload_url = _checked_upload_url(result.get('upload_url', ''))
        with file_path.open('rb') as handle:
            for index in range(count):
                start = index * chunk
                length = size - start if index == count - 1 else chunk
                data = handle.read(length)
                if len(data) != length:
                    raise TikTokPostingError('video_file_changed')
                try:
                    response = http.put(upload_url, content=data, headers={
                        'Content-Type': 'video/mp4', 'Content-Length': str(length),
                        'Content-Range': f'bytes {start}-{start + length - 1}/{size}'})
                except httpx.HTTPError as exc:
                    raise TikTokPostingError('upload_failed') from exc
                expected = 201 if index == count - 1 else 206
                if response.status_code != expected:
                    raise TikTokPostingError('upload_failed')
        return publish_id


def fetch_post_status(root, open_id, publish_id, client=None):
    with _client(client) as http:
        token = _authorized(root, open_id, 'video.publish', http)
        result = _post_json(http, STATUS_URL, token, {'publish_id': publish_id})
    raw_ids = result.get('publicaly_available_post_id') or []
    ids = [str(item) for item in raw_ids if re.fullmatch(r'\d{10,25}', str(item))]
    status = result.get('status')
    if status not in {'PROCESSING_UPLOAD', 'PROCESSING_DOWNLOAD', 'SEND_TO_USER_INBOX',
                      'PUBLISH_COMPLETE', 'FAILED'}:
        raise TikTokPostingError('unknown_publish_status')
    reason = result.get('fail_reason')
    return {'status': status, 'post_ids': ids,
            'fail_reason': reason if isinstance(reason, str) and
            re.fullmatch(r'[a-z][a-z0-9_]{1,70}', reason) else None}
