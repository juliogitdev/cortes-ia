import json
from datetime import datetime, timedelta, timezone

import httpx

from clip_platform.learning.tiktok import connection_status, query_metrics, TikTokCollectionError
from clip_platform.media.affect import affective_cues
from clip_platform.selection.baseline import select
from clip_platform.shared.contracts import AnalysisRequest, Evidence, EvidenceBundle, MediaAsset, Provenance, Publication


def test_tiktok_connector_reads_only_owned_video_and_all_counters(tmp_path):
    path = tmp_path / 'integrations' / 'tiktok.json'
    path.parent.mkdir()
    path.write_text(json.dumps({'access_token': 'test-token'}), encoding='utf-8')
    publication = Publication(publication_id='p', revision_id='r', platform='tiktok', account='@me',
        posted_at=datetime.now(timezone.utc) - timedelta(days=1),
        publication_url='https://www.tiktok.com/@me/video/1234567890123456789')
    def respond(request):
        assert str(request.url).startswith('https://open.tiktokapis.com/v2/video/query/')
        assert request.headers['Authorization'] == 'Bearer test-token'
        assert json.loads(request.content)['filters']['video_ids'] == ['1234567890123456789']
        return httpx.Response(200, json={'error': {'code': 'ok'}, 'data': {'videos': [
            {'id': '1234567890123456789', 'view_count': 12, 'like_count': 4,
             'comment_count': 2, 'share_count': 1}]}})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        values, source = query_metrics(publication, tmp_path, client)
    assert values == {'views': 12, 'likes': 4, 'comments': 2, 'shares': 1}
    assert source == 'tiktok:1234567890123456789'
    assert connection_status(tmp_path)['connected']


def test_affective_cue_keeps_observation_and_uncertainty_separate():
    asset = MediaAsset(asset_id='a', source_uri='local:a', content_hash='sha256:' + '0'*64,
                       duration_s=30, tracks=['audio', 'video'], local_path='a.mp4')
    provenance = Provenance(run_id='speech', source_uri='a', artifact_hash=asset.content_hash,
                            original_offset_s=0, settings={})
    segment = Evidence(evidence_id='speech_1', asset_id='a', start_s=2, end_s=6,
                       observation='Isso é um absurdo!', provenance=provenance)
    cues, cue_provenance = affective_cues(asset, [segment])
    assert len(cues) == 1
    assert cues[0].start_s == 2 and cues[0].end_s == 6
    assert 'indignação' in cues[0].observation
    assert 'pode' in cues[0].interpretation
    bundle = EvidenceBundle(asset_id='a', transcript=[segment], visual_events=[], audio_events=cues,
                            quality=[], provenance=[provenance, cue_provenance])
    result = select(asset, bundle, AnalysisRequest(asset_id='a', duration_mode='exact',
                                                   target_s=10, top_k=1, niche='conversa'))
    assert result.candidates[0].features['affective_cues'] == 1
    assert result.candidates[0].features['audio_energy_events'] == 0
    assert cues[0].evidence_id in result.candidates[0].evidence_ids
