import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from clip_platform.shared.contracts import (
    AnalysisRequest, AnalysisResult, Feedback, Interval, MetricSnapshot, SubtitleSettings,
    PublicationCollectionRun, PublicationRecord,
)

FIXTURES = Path(__file__).resolve().parents[2] / "docs/contracts/v1"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_official_examples_roundtrip():
    for name, model in [("analysis_input", AnalysisRequest), ("analysis_output", AnalysisResult), ("publication_partial", PublicationRecord)]:
        parsed = model.model_validate(fixture(name))
        assert model.model_validate_json(parsed.model_dump_json()) == parsed


@pytest.mark.parametrize("change", [
    {"target_s": None}, {"min_s": 10}, {"max_s": 40}, {"target_s": -1},
    {"duration_mode": "range"}, {"duration_mode": "range", "target_s": None, "min_s": 40, "max_s": 20},
])
def test_duration_modes_reject_ambiguous_requests(change):
    data = fixture("analysis_input")
    data.update(change)
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(data)


def test_range_request():
    data = fixture("analysis_input")
    data.update(duration_mode="range", target_s=None, min_s=20, max_s=40)
    assert AnalysisRequest.model_validate(data).min_s == 20


def test_subtitle_request_keeps_legacy_off_and_validates_style():
    old_payload = fixture("analysis_input")
    old_payload.pop("subtitle_settings")
    old_payload["schema_version"] = "1.0.0"
    legacy = AnalysisRequest.model_validate(old_payload)
    assert not legacy.subtitle_settings.enabled
    enabled = legacy.model_copy(update={"subtitle_settings": SubtitleSettings(enabled=True,
        style="yellow_pop", position="bottom", max_words_per_line=4)})
    assert AnalysisRequest.model_validate_json(enabled.model_dump_json()).subtitle_settings.enabled
    with pytest.raises(ValidationError):
        SubtitleSettings(enabled=True, style="unknown")
    old_style = SubtitleSettings.model_validate({'schema_version': '1.0.0',
        'enabled': True, 'style': 'yellow_pop', 'position': 'bottom',
        'max_words_per_line': 4, 'font_scale': 1.0})
    assert old_style.highlight_color == '#FFFF00' and old_style.outline_width == 5


@pytest.mark.parametrize("start,end", [(0, 0), (3, 2), (-1, 2), (0, float("nan")), (0, float("inf"))])
def test_invalid_intervals(start, end):
    with pytest.raises(ValidationError):
        Interval(start_s=start, end_s=end)


@pytest.mark.parametrize("case", ["asset", "missing", "outside", "unrelated", "duration", "evidence_outside", "duplicate", "nan_score"])
def test_result_context_prevents_promoting_invalid_proposals(case):
    data = fixture("analysis_output")
    candidate = data["candidates"][0]
    if case == "asset":
        candidate["asset_id"] = "other"
    elif case == "missing":
        candidate["evidence_ids"] = ["invented"]
    elif case == "outside":
        candidate.update(start_s=110, end_s=140)
    elif case == "unrelated":
        candidate.update(start_s=70, end_s=100)
    elif case == "duration":
        candidate["end_s"] = 66
    elif case == "evidence_outside":
        data["evidence"]["transcript"][0]["end_s"] = 130
    elif case == "duplicate":
        data["evidence"]["transcript"].append(copy.deepcopy(data["evidence"]["transcript"][0]))
    else:
        candidate["rank_score"] = float("nan")
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_alternative_duration_requires_visible_limitation():
    data = fixture("analysis_output")
    candidate = data["candidates"][0]
    candidate.update(end_s=66, duration_compliance="alternative")
    assert AnalysisResult.model_validate(data).candidates[0].end_s == 66
    candidate["limitations"] = []
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_missing_metrics_are_null_and_age_is_actual():
    record = PublicationRecord.model_validate(fixture("publication_partial"))
    assert record.snapshots[1].value is None
    assert record.snapshots[0].age_hours > 48


@pytest.mark.parametrize("case", ["age", "publication", "collection", "zero", "manual", "timestamp"])
def test_publication_context_rejects_untraceable_metrics(case):
    data = fixture("publication_partial")
    snapshot = data["snapshots"][1]
    if case == "age":
        snapshot["age_hours"] = 24
    elif case == "publication":
        snapshot["publication_id"] = "other"
    elif case == "collection":
        snapshot["collection_id"] = "unknown"
    elif case == "zero":
        snapshot["value"] = 0
    elif case == "manual":
        snapshot["source"] = "manual"
    else:
        snapshot["observed_at"] = "2026-10-02T12:00:02"
    with pytest.raises(ValidationError):
        PublicationRecord.model_validate(data)


def test_collection_requires_explicit_action_and_terminal_timestamps():
    data = fixture("publication_partial")["collections"][0]
    data["trigger"] = "scheduled"
    with pytest.raises(ValidationError):
        PublicationCollectionRun.model_validate(data)
    data["trigger"] = "explicit_user_action"
    data["finished_at"] = None
    with pytest.raises(ValidationError):
        PublicationCollectionRun.model_validate(data)


def test_feedback_preference_requires_distinct_comparison():
    with pytest.raises(ValidationError):
        Feedback(target_id="a", label="preferred", reason="Contexto", reviewer="operator", created_at="2026-10-02T12:00:00Z", comparison_target="a")


@pytest.mark.parametrize("case", ["active", "snapshot", "before_post", "requested_started"])
def test_publication_history_invariants(case):
    data = fixture("publication_partial")
    if case == "active":
        run = data["collections"][0]
        run.update(status="requested", started_at=None, finished_at=None)
        other = copy.deepcopy(run)
        other.update(collection_id="collection_2", request_id="action_2")
        data["collections"].append(other)
        data["snapshots"] = []
    elif case == "snapshot":
        data["snapshots"].append(copy.deepcopy(data["snapshots"][0]))
    elif case == "before_post":
        data["collections"][0]["requested_at"] = "2026-09-29T12:00:00Z"
    else:
        data["collections"][0].update(status="requested", finished_at=None)
    with pytest.raises(ValidationError):
        PublicationRecord.model_validate(data)
