import json
from pathlib import Path
from clip_platform.shared.jobs import Job, Project, Export
from clip_platform.api.app import create_app

def test_generated_w1_schemas_and_openapi_are_current(tmp_path):
    root = Path(__file__).resolve().parents[2] / 'docs/contracts/w1'
    for model in (Job, Project, Export):
        assert json.loads((root / (model.__name__.lower() + '.schema.json')).read_text(encoding='utf-8')) == model.model_json_schema()
    assert json.loads((root / 'openapi.json').read_text(encoding='utf-8')) == create_app(tmp_path).openapi()
