from types import SimpleNamespace

from scripts.evaluate_selector import temporal_iou


def _span(start, end):
    return SimpleNamespace(start_s=start, end_s=end)


def test_temporal_overlap_matches_same_event_with_shifted_boundaries():
    assert temporal_iou(_span(10, 40), _span(12, 42)) > .8
    assert temporal_iou(_span(10, 20), _span(20, 30)) == 0
