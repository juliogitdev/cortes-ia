"""Persistent local TikTok posting queue. Run alongside the API."""
import argparse
import os
import time
from pathlib import Path

from clip_platform.learning.tiktok_oauth import account
from clip_platform.learning.tiktok_posting import direct_post, fetch_post_status, TikTokPostingError
from clip_platform.services.store import Store


def run_once(root: Path, store: Store | None = None):
    store = store or Store(root)
    attempt = store.claim_due_tiktok_publish()
    if not attempt:
        return False
    try:
        linked = account(root, attempt.account_open_id)
        if not linked or 'video.publish' not in linked.get('scopes', []):
            raise ValueError('scope_not_authorized')
        export = store.get_export(attempt.export_id)
        if export.revision_id != attempt.revision_id:
            raise ValueError('export_mismatch')
        video = Path(export.local_path).resolve()
        if not video.is_relative_to(root.resolve()) or not video.is_file():
            raise ValueError('export_unavailable')
        def initialized(publish_id):
            store.update_tiktok_publish(attempt.attempt_id, 'uploading', publish_id)
        publish_id = direct_post(root, attempt.account_open_id, str(video),
            attempt.caption, attempt.privacy_level, attempt.disable_comment,
            attempt.disable_duet, attempt.disable_stitch, on_initialized=initialized)
        store.update_tiktok_publish(attempt.attempt_id, 'processing', publish_id)
        for delay in (0, 5, 10, 20, 30, 60):
            if delay:
                time.sleep(delay)
            try:
                result = fetch_post_status(root, attempt.account_open_id, publish_id)
            except TikTokPostingError:
                continue
            if result['status'] == 'FAILED':
                store.update_tiktok_publish(attempt.attempt_id, 'failed',
                    error_code=result['fail_reason'] or 'tiktok_publish_failed')
                break
            if result['status'] == 'PUBLISH_COMPLETE':
                store.complete_tiktok_publish(attempt.attempt_id,
                    result['post_ids'][0] if result['post_ids'] else None)
                break
    except TikTokPostingError as exc:
        store.update_tiktok_publish(attempt.attempt_id, 'failed', error_code=exc.code)
    except Exception as exc:
        store.update_tiktok_publish(attempt.attempt_id, 'failed',
            error_code=str(exc) if str(exc) in {'scope_not_authorized', 'export_mismatch',
                                                 'export_unavailable'} else 'posting_failed')
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--storage', default=os.environ.get('CLIP_STORAGE', 'storage'))
    args = parser.parse_args()
    root = Path(args.storage).resolve()
    store = Store(root)
    store.mark_interrupted_tiktok_publishes()
    while True:
        if not run_once(root, store):
            time.sleep(5)


if __name__ == '__main__':
    main()
