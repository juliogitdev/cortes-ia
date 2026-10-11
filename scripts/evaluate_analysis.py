"""Report measurable cut properties without exporting private transcript text."""
import argparse
import json
from pathlib import Path

from clip_platform.selection.baseline import _repetitive
from clip_platform.services.store import Store


def summarize(store, analysis_id):
    result = store.get_analysis(analysis_id)
    return {
        'analysis_id': analysis_id,
        'duration_mode': result.request.duration_mode,
        'speech_model': (result.evidence.provenance[0].settings.get('model_identity', {})
                         .get('repo', 'unknown')),
        'asset_duration_s': round(result.asset.duration_s, 2),
        'transcript_segments': len(result.evidence.transcript),
        'repetitive_segments': sum(_repetitive(item.observation) for item in result.evidence.transcript),
        'visual_events': len(result.evidence.visual_events),
        'audio_events': len(result.evidence.audio_events),
        'quality_notes': result.evidence.quality,
        'candidates': [{
            'candidate_id': item.candidate_id,
            'start_s': round(item.start_s, 2),
            'end_s': round(item.end_s, 2),
            'duration_s': round(item.end_s - item.start_s, 2),
            'boundary_signals': item.features.get('boundary_signals', 0),
            'opening_signal': item.features.get('opening_signal'),
            'continuation_suggested': item.features.get('continuation_suggested'),
            'visual_changes': item.features.get('visual_changes', 0),
            'audio_energy_events': item.features.get('audio_energy_events', 0),
        } for item in result.candidates],
        'scope': 'automated measurements only; editorial quality needs human review',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis_ids', nargs='+')
    parser.add_argument('--storage', type=Path, default=Path('storage'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = {'analyses': [summarize(Store(args.storage), identifier) for identifier in args.analysis_ids]}
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding='utf-8')
    else:
        print(encoded)


if __name__ == '__main__':
    main()
