import json

import httpx
import pytest

from clip_platform.learning.tiktok_oauth import _account_path, _write_private, save_app
from clip_platform.learning.tiktok_posting import (creator_info, direct_post, fetch_post_status,
    list_videos, TikTokPostingError)


def test_manual_video_list_and_direct_post_transport(tmp_path):
    save_app(tmp_path, 'key_123', 'private-secret',
             'https://panel.example/integrations/tiktok/callback')
    _write_private(_account_path(tmp_path, 'owner'), {
        'open_id': 'owner', 'display_name': 'Minha conta',
        'scopes': ['user.info.basic', 'video.list', 'video.publish'],
        'access_token': 'token-owner', 'refresh_token': 'refresh-owner'})
    file_path = tmp_path / 'clip.mp4'
    file_path.write_bytes(b'example-video-data')
    calls = []
    def respond(request):
        calls.append((request.method, request.url.path))
        if request.url.path == '/v2/video/list/':
            assert request.headers['Authorization'] == 'Bearer token-owner'
            return httpx.Response(200, json={'error': {'code': 'ok'}, 'data': {
                'videos': [{'id': '1234567890123456789', 'title': 'Meu corte',
                            'share_url': 'https://www.tiktok.com/@owner/video/1234567890123456789',
                            'create_time': 1_750_000_000}], 'has_more': False}})
        if request.url.path == '/v2/post/publish/creator_info/query/':
            return httpx.Response(200, json={'error': {'code': 'ok'}, 'data': {
                'creator_username': 'owner', 'creator_nickname': 'Minha conta',
                'privacy_level_options': ['SELF_ONLY'], 'comment_disabled': True,
                'duet_disabled': False, 'stitch_disabled': False}})
        if request.url.path == '/v2/post/publish/video/init/':
            payload = json.loads(request.content)
            assert payload['source_info']['source'] == 'FILE_UPLOAD'
            assert payload['post_info']['privacy_level'] == 'SELF_ONLY'
            assert payload['post_info']['disable_comment'] is True
            return httpx.Response(200, json={'error': {'code': 'ok'}, 'data': {
                'publish_id': 'publish-1',
                'upload_url': 'https://open-upload.tiktokapis.com/video/?upload_id=123'}})
        if request.url.path == '/video/':
            assert request.method == 'PUT'
            assert request.headers['Content-Range'] == f'bytes 0-{file_path.stat().st_size - 1}/{file_path.stat().st_size}'
            assert request.content == file_path.read_bytes()
            return httpx.Response(201)
        if request.url.path == '/v2/post/publish/status/fetch/':
            return httpx.Response(200, json={'error': {'code': 'ok'}, 'data': {
                'status': 'PUBLISH_COMPLETE',
                'publicaly_available_post_id': [1234567890123456789]}})
        raise AssertionError(str(request.url))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        videos = list_videos(tmp_path, 'owner', client=client)
        assert videos['videos'][0]['title'] == 'Meu corte'
        assert creator_info(tmp_path, 'owner', client)['privacy_level_options'] == ['SELF_ONLY']
        initialized = []
        assert direct_post(tmp_path, 'owner', file_path, 'Legenda', 'SELF_ONLY',
                           client=client, on_initialized=initialized.append) == 'publish-1'
        assert initialized == ['publish-1']
        assert fetch_post_status(tmp_path, 'owner', 'publish-1', client)['post_ids'] == ['1234567890123456789']
    assert ('PUT', '/video/') in calls


def test_direct_post_rejects_untrusted_upload_target(tmp_path):
    save_app(tmp_path, 'key_123', 'private-secret',
             'https://panel.example/integrations/tiktok/callback')
    _write_private(_account_path(tmp_path, 'owner'), {
        'open_id': 'owner', 'display_name': 'Minha conta',
        'scopes': ['video.publish'], 'access_token': 'token-owner',
        'refresh_token': 'refresh-owner'})
    video = tmp_path / 'clip.mp4'
    video.write_bytes(b'mp4-bytes')
    def respond(request):
        if request.url.path.endswith('/creator_info/query/'):
            return httpx.Response(200, json={'error': {'code': 'ok'}, 'data': {
                'privacy_level_options': ['SELF_ONLY']}})
        return httpx.Response(200, json={'error': {'code': 'ok'}, 'data': {
            'publish_id': 'publish-1', 'upload_url': 'http://127.0.0.1/private'}})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(TikTokPostingError, match='invalid_upload_url'):
            direct_post(tmp_path, 'owner', video, '', 'SELF_ONLY', client=client)
