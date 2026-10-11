"""Observable language cues, not an inference about the speaker's inner state."""
import re

from clip_platform.shared.contracts import Evidence, MediaAsset, Provenance


PATTERNS = {
    'riso': re.compile(r'\b(?:risos|rindo|gargalhada|haha(?:ha)+|kkk+)\b', re.I),
    'surpresa': re.compile(r'\b(?:surpresa|surpreso|surpreendente|inacredit[aá]vel|n[aã]o acredito)\b', re.I),
    'entusiasmo': re.compile(r'\b(?:animad[oa]|empolgad[oa]|incr[ií]vel|maravilhos[oa])\b', re.I),
    'indignação': re.compile(r'\b(?:absurdo|revoltad[oa]|indignad[oa])\b', re.I),
}


def affective_cues(asset: MediaAsset, transcript: list[Evidence]):
    provenance = Provenance(run_id='affective_language_pt_v1', source_uri=asset.source_uri,
                            artifact_hash=asset.content_hash, original_offset_s=0,
                            settings={'method': 'literal Portuguese language cues',
                                      'inference': 'no speaker emotion inferred'})
    events = []
    for item in transcript:
        labels = [label for label, pattern in PATTERNS.items() if pattern.search(item.observation)]
        if not labels:
            continue
        events.append(Evidence(evidence_id='affect_' + item.evidence_id,
            asset_id=asset.asset_id, start_s=item.start_s, end_s=item.end_s,
            observation='Expressões transcritas associadas a: ' + ', '.join(labels) + '.',
            interpretation='Indício linguístico de expressão afetiva; pode ser citação, ironia ou erro de transcrição.',
            hypothesis='A expressão pode chamar atenção; exige revisão humana.',
            provenance=provenance))
    return events, provenance
