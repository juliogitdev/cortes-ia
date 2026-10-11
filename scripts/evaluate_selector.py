"""Read-only comparison of stored selection and current rules; no training or media export."""
import argparse
import json
from pathlib import Path

from clip_platform.selection.baseline import select
from clip_platform.services.store import Store


def temporal_iou(left, right) -> float:
    overlap = max(0., min(left.end_s, right.end_s) - max(left.start_s, right.start_s))
    union = max(left.end_s, right.end_s) - min(left.start_s, right.start_s)
    return overlap / union if union else 0.


def compare(store: Store, analysis_id: str) -> dict:
    stored = store.get_analysis(analysis_id)
    proposed = select(stored.asset, stored.evidence, stored.request)
    matched = sum(max((temporal_iou(new, old) for old in stored.candidates), default=0.) >= .5
                  for new in proposed.candidates)
    feedback = []
    for old in stored.candidates:
        for item in store.list_feedback(analysis_id, old.candidate_id):
            feedback.append({'rating': item.rating,
                             'max_overlap_with_new': round(max((temporal_iou(old, new)
                                 for new in proposed.candidates), default=0.), 3)})
    return {'analysis_id': analysis_id, 'old_count': len(stored.candidates),
            'new_count': len(proposed.candidates), 'matched_events_iou_ge_0_5': matched,
            'feedback_count': len(feedback), 'feedback_overlap': feedback,
            'old_rules': stored.candidates[0].versions.rules_version if stored.candidates else None,
            'new_rules': proposed.candidates[0].versions.rules_version if proposed.candidates else None,
            'note': 'Temporal overlap is continuity, not editorial quality or viral probability.'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis_ids', nargs='+')
    parser.add_argument('--storage', type=Path, default=Path('storage'))
    args = parser.parse_args()
    store = Store(args.storage)
    print(json.dumps([compare(store, analysis_id) for analysis_id in args.analysis_ids],
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
