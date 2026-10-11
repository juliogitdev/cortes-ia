import json
from pathlib import Path
from clip_platform.shared.jobs import Job, Project, Export, CandidateFeedback
from clip_platform.api.app import create_app
from clip_platform.ingestion.download import DownloadRequest
from clip_platform.shared.contracts import Publication, TikTokPublishAttempt, SubtitleSettings, SubtitleWord, ClipRevision

def test_generated_current_schemas_and_openapi(tmp_path):
    contracts = Path(__file__).resolve().parents[2] / 'docs/contracts'
    for model in (Project, Export):
        assert json.loads((contracts / 'w1' / (model.__name__.lower() + '.schema.json')).read_text(encoding='utf-8')) == model.model_json_schema()
    assert json.loads((contracts / 'w2/job.schema.json').read_text(encoding='utf-8')) == Job.model_json_schema()
    assert json.loads((contracts / 'w2/download_request.schema.json').read_text(encoding='utf-8')) == DownloadRequest.model_json_schema()
    assert json.loads((contracts / 'w2/candidate_feedback.schema.json').read_text(encoding='utf-8')) == CandidateFeedback.model_json_schema()
    DownloadRequest.model_validate_json((contracts / 'w2/download_request.json').read_text(encoding='utf-8'))
    CandidateFeedback.model_validate_json((contracts / 'w2/candidate_feedback.json').read_text(encoding='utf-8'))
    assert json.loads((contracts / 'w2/openapi.json').read_text(encoding='utf-8')) == create_app(tmp_path).openapi()
    for model in (SubtitleSettings, SubtitleWord, ClipRevision):
        path = contracts / 'w15' / (model.__name__.lower() + '.schema.json')
        assert json.loads(path.read_text(encoding='utf-8')) == model.model_json_schema()
    Publication.model_validate_json((contracts / 'w3/tiktok_connected_publication.json').read_text(encoding='utf-8'))
    Publication.model_validate_json((contracts / 'w3/tiktok_automatic_publication.json').read_text(encoding='utf-8'))
    TikTokPublishAttempt.model_validate_json((contracts / 'w3/tiktok_publish_attempt.json').read_text(encoding='utf-8'))
