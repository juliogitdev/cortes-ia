"""Deterministic transcript window baseline, independent from media and UI."""
import hashlib

from clip_platform.shared.contracts import (
    AnalysisRequest, AnalysisResult, ClipCandidate, EvidenceBundle, MediaAsset, ModelRun,
)


def select(asset: MediaAsset, evidence: EvidenceBundle, request: AnalysisRequest) -> AnalysisResult:
    # Cross-asset and out-of-bounds checks also apply when no candidate is produced.
    limitations = ['Baseline somente de fala; score ordena densidade textual, não prevê viralização.',
                   'Qualidade editorial e limites precisam de revisão humana.']
    AnalysisResult(asset=asset, request=request, evidence=evidence, candidates=[], limitations=limitations)
    minimum = request.target_s if request.duration_mode == 'exact' else request.min_s
    maximum = request.target_s if request.duration_mode == 'exact' else request.max_s
    if minimum > asset.duration_s:
        return AnalysisResult(asset=asset, request=request, evidence=evidence, candidates=[],
                              limitations=limitations + ['Duração pedida excede a mídia; nenhum ajuste silencioso.'])
    transcript = sorted(evidence.transcript, key=lambda x: (x.start_s, x.end_s, x.evidence_id))
    windows = {}
    for anchor in transcript:
        duration = minimum if request.duration_mode == 'exact' else min(maximum, max(minimum, anchor.end_s-anchor.start_s))
        start = min(anchor.start_s, asset.duration_s-duration)
        end = start + duration
        refs = [item for item in transcript if item.start_s < end and item.end_s > start]
        # Full segments only: don't justify a quote that is cut by the boundary.
        complete = [item for item in refs if item.start_s >= start and item.end_s <= end]
        if not complete:
            continue
        count = sum(len(item.observation.split()) for item in complete)
        score = count / duration
        windows[(start, end)] = (score, count, complete)
    candidates = []
    signature = request.model_dump_json() + asset.content_hash + repr([
        (item.evidence_id, item.start_s, item.end_s, item.observation) for item in transcript])
    for (start, end), (score, count, refs) in sorted(windows.items(), key=lambda pair: (-pair[1][0], pair[0])):
        # One suggested window per overlapping region, to avoid repeating speech.
        if any(start < candidate.end_s and end > candidate.start_s for candidate in candidates):
            continue
        identifier = hashlib.sha256(f'{signature}:{start}:{end}'.encode()).hexdigest()[:20]
        versions = ModelRun(run_id='baseline_' + identifier, model_version='speech-density-baseline-1',
                            rules_version='windows-1', feature_schema='speech-density-1',
                            dataset_version='not-trained', settings={'duration_mode': request.duration_mode,
                            'ranking': 'complete transcript words per requested second',
                            'instructions_applied': False})
        candidates.append(ClipCandidate(candidate_id='candidate_' + identifier, asset_id=asset.asset_id,
                          start_s=start, end_s=end, features={'word_count': float(count), 'words_per_s': score},
                          evidence_ids=[item.evidence_id for item in refs],
                          reasons=[f'Contém {len(refs)} segmento(s) completo(s) de fala e {count} palavras transcritas.',
                                   'Trecho de fala: ' + refs[0].observation[:200]],
                          limitations=['Não considera imagem, emoção, tendências ou independência de contexto.'],
                          rank_score=score, versions=versions))
        if len(candidates) == request.top_k:
            break
    if request.instructions:
        limitations.append('Orientação livre registrada no pedido; baseline não interpreta essa orientação.')
    if not candidates:
        limitations.append('Sem fala completa compatível com a duração solicitada.')
    elif len(candidates) < request.top_k:
        limitations.append('Há menos regiões de fala sem sobreposição do que o número solicitado.')
    return AnalysisResult(asset=asset, request=request, evidence=evidence,
                          candidates=candidates, limitations=limitations)
