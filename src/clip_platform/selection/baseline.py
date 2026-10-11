"""Deterministic transcript window baseline, independent from media and UI."""
import hashlib
import re
from collections import Counter

from clip_platform.shared.contracts import (
    AnalysisRequest, AnalysisResult, ClipCandidate, EvidenceBundle, MediaAsset, ModelRun,
)
from clip_platform.speech.transcribe import _repetition_loop


_PROMOTION_CUES = (
    re.compile(r'\b(?:qr\s*code|cupom|link na descri[cç][aã]o)\b', re.I),
    re.compile(r'\b(?:aprender ingl[eê]s|escola online|inscreva.se|desconto)\b', re.I),
    re.compile(r'\b(?:patrocinad[oa]|parceria comercial|pr[eê]mios?)\b', re.I),
)

_STREAM_ADMIN_CUES = (
    re.compile(r'\b(?:bora bater|meta de)\s+\d+\s*(?:mil\s+)?likes\b', re.I),
    re.compile(r'\b(?:manda(?:r)?|divulga(?:r)?)\s+(?:o|esse|a)?\s*link\b', re.I),
    re.compile(r'\b(?:página de inscrição|senha do banco|site (?:deslogando|fora do ar))\b', re.I),
    re.compile(r'\b(?:fecha (?:essa|a) (?:bosta|votação)|entra aí,? geral e vota|termina a votação)\b', re.I),
    re.compile(r'\bsite\b.{0,45}\bdeslogando\b|\b(?:vendendo|divulgando)\s+(?:no|o)\s+link\b', re.I),
    re.compile(r'\b(?:manda|mandem)\s+(?:um|o)?\s*vídeo(?:s)?\s+(?:no|pro)\s+discord\b', re.I),
    re.compile(r'\b(?:todos os dias|sempre que)\b.{0,45}\b(?:abrir|abri)\s+live\b', re.I),
    re.compile(r'\b(?:vota[cç][aã]o|bota[cç][aã]o)\s+aberta\b', re.I),
    re.compile(r'\b(?:vamos|bora)\s+ver\s+(?:os|mais)\s+v[ií]deos\b', re.I),
)


def _stream_admin_window(items) -> bool:
    text = ' '.join(item.observation for item in items)
    return any(pattern.search(text) for pattern in _STREAM_ADMIN_CUES)


def _promotional_window(items) -> bool:
    text = ' '.join(item.observation for item in items)
    return sum(bool(pattern.search(text)) for pattern in _PROMOTION_CUES) >= 2


def _speech_density_score(words: int, duration_s: float) -> float:
    """Stop rewarding arbitrarily dense, possibly overlapping speech."""
    rate = words / duration_s
    return min(rate, 4.4) - min(.8, max(0., rate - 5.2) * .35)


def _opening_question(items, start_s: float) -> bool:
    opening = ' '.join(item.observation for item in items
                       if item.start_s >= start_s and item.start_s < start_s + 4)
    return '?' in opening and len(re.findall(r'\w+', opening)) >= 5


_OPENING_HOUSEKEEPING = (
    re.compile(r'\b(?:vou|vamos)\s+ver\s+mais\s+(?:\d+|um|dois|tr[eê]s)\s+v[ií]deos\b', re.I),
    re.compile(r'\bvou\s+botar\s+aqui\s+um\s+minuto\b', re.I),
    re.compile(r'\bantes\s+de\s+mais\s+nada\b.{0,80}\bvamos\s+come[cç]ar\b', re.I),
    re.compile(r'\b(?:vamos|vamo|bora)\s+come[cç]ar\s+essa\b', re.I),
)


def _opening_housekeeping(items, start_s: float) -> bool:
    opening = ' '.join(item.observation for item in items
                       if item.start_s >= start_s and item.start_s < start_s + 6)
    return any(pattern.search(opening) for pattern in _OPENING_HOUSEKEEPING)


def _editorial_reject(items, start_s: float) -> bool:
    """Reject identifiable live operations rather than filling top_k with them."""
    if _opening_housekeeping(items, start_s):
        return True
    return _stream_admin_window(items)


def select(asset: MediaAsset, evidence: EvidenceBundle, request: AnalysisRequest) -> AnalysisResult:
    # Cross-asset and out-of-bounds checks also apply when no candidate is produced.
    limitations = ['Ranking heurístico de fala, mudanças de quadro, energia e expressões afetivas transcritas; score não prevê viralização.',
                   'Qualidade editorial e limites precisam de revisão humana.']
    AnalysisResult(asset=asset, request=request, evidence=evidence, candidates=[], limitations=limitations)
    minimum = request.target_s if request.duration_mode == 'exact' else request.min_s
    maximum = request.target_s if request.duration_mode == 'exact' else request.max_s
    if minimum > asset.duration_s:
        return AnalysisResult(asset=asset, request=request, evidence=evidence, candidates=[],
                              limitations=limitations + ['Duração pedida excede a mídia; nenhum ajuste silencioso.'])
    transcript = sorted((item for item in evidence.transcript if not _repetitive(item.observation)),
                        key=lambda x: (x.start_s, x.end_s, x.evidence_id))
    windows = {}
    for index, anchor in enumerate(transcript):
        if request.duration_mode == 'exact':
            duration = minimum
            start = min(anchor.start_s, asset.duration_s-duration)
            end = start + duration
            refs = [item for item in transcript if item.start_s < end and item.end_s > start]
            complete = [item for item in refs if item.start_s >= start and item.end_s <= end]
            if complete and not _promotional_window(complete):
                count = sum(len(item.observation.split()) for item in complete)
                windows[(start, end)] = (_speech_density_score(count, duration), count, refs, 0, False)
            continue

        # In range mode, close only after a complete transcript segment. Prefer a
        # sentence ending or a pause; if none exists, state that the ending is uncertain.
        start = anchor.start_s
        endings = []
        for end_index in range(index, len(transcript)):
            last = transcript[end_index]
            if last.end_s - start > maximum:
                break
            next_start = transcript[end_index + 1].start_s if end_index + 1 < len(transcript) else asset.duration_s
            if last.end_s - start < minimum and next_start < start + minimum:
                continue
            pause = next_start - last.end_s >= .7
            punctuation = bool(re.search(r'[.!?…]["”\']?\s*$', last.observation.strip()))
            boundary = int(pause) + int(punctuation)
            end = min(asset.duration_s, last.end_s + min(.25, max(0, next_start - last.end_s) / 2))
            if end - start < minimum and next_start >= start + minimum:
                end = start + minimum
            if end - start > maximum:
                end = last.end_s
            complete = [item for item in transcript[index:end_index+1]
                        if item.start_s >= start and item.end_s <= end]
            if not complete or _promotional_window(complete):
                continue
            count = sum(len(item.observation.split()) for item in complete)
            duration = end - start
            score = _speech_density_score(count, duration) + .15 * boundary
            endings.append((boundary, score, duration, end, count, complete, pause, punctuation))
        if endings:
            boundary, score, duration, end, count, complete, pause, punctuation = max(
                endings, key=lambda item: (item[0], item[1], item[2]))
            windows[(start, end)] = (score, count, complete, boundary, pause or punctuation)
    for event in evidence.visual_events:
        if any(start <= event.start_s < end for start, end in windows):
            continue
        duration = minimum
        start = max(0, min(event.start_s - duration / 2, asset.duration_s - duration))
        end = start + duration
        windows[(start, end)] = (0., 0, [], 0, False)
    enriched = {}
    for (start, end), (score, count, refs, boundary, natural_end) in windows.items():
        visual = [item for item in evidence.visual_events if item.start_s < end and item.end_s > start]
        audio = [item for item in evidence.audio_events if item.start_s < end and item.end_s > start]
        affect = [item for item in audio if item.provenance.run_id == 'affective_language_pt_v1']
        energy = [item for item in audio if item.provenance.run_id != 'affective_language_pt_v1']
        prior = next((item for item in reversed(transcript) if item.end_s <= start), None)
        opening = int(prior is None or start - prior.end_s >= .7 or
                      bool(re.search(r'[.!?…]["”\']?\s*$', prior.observation.strip())))
        following = next((item for item in transcript if item.start_s >= end), None)
        continuation = int(following is not None and following.start_s - end < 1.5 and not natural_end)
        admin_penalty = 1.25 if _stream_admin_window(refs) else 0.
        hook_question = int(_opening_question(refs, start))
        opening_housekeeping = int(_opening_housekeeping(refs, start))
        enriched[(start, end)] = (score + .25 * min(len(visual), 3) + .1 * min(len(energy), 3)
                                  + .15 * min(len(affect), 2)
                                  + .2 * opening + .2 * hook_question - .25 * continuation
                                  - admin_penalty - .75 * opening_housekeeping,
                                  count, refs, boundary, natural_end, visual, audio, energy, affect, opening,
                                  continuation, hook_question, opening_housekeeping)
    candidates = []
    signature = request.model_dump_json() + asset.content_hash + repr([
        (item.evidence_id, item.start_s, item.end_s, item.observation) for item in evidence.all_evidence()])
    for (start, end), (score, count, refs, boundary, natural_end, visual, audio, energy, affect, opening, continuation, hook_question, opening_housekeeping) in sorted(
            enriched.items(), key=lambda pair: (-pair[1][0], pair[0])):
        if refs and _editorial_reject(refs, start):
            continue
        # One suggested window per overlapping region, to avoid repeating speech.
        if any(start < candidate.end_s and end > candidate.start_s for candidate in candidates):
            continue
        identifier = hashlib.sha256(f'{signature}:{start}:{end}'.encode()).hexdigest()[:20]
        versions = ModelRun(run_id='baseline_' + identifier, model_version='observable-signals-baseline-2',
                            rules_version='windows-5-editorial-review', feature_schema='observable-signals-3',
                            dataset_version='not-trained', settings={'duration_mode': request.duration_mode,
                            'ranking': 'capped speech density, observed opening question, transcript ending, frame changes, audio energy and literal affective language cues',
                            'instructions_applied': False})
        reason = ('Fim alinhado a pausa ou pontuação observada na transcrição.' if natural_end
                  else 'Fim no limite de um segmento transcrito; continuidade pode exigir revisão.')
        candidate_limitations = ['Mudança de quadro, energia sonora e palavras afetivas não identificam emoção real.',
                                 'Expressões podem ser ironia ou erro de transcrição; tendências e contexto exigem revisão humana.']
        if refs and not natural_end:
            candidate_limitations.append('Não foi detectado um encerramento claro dentro da faixa solicitada.')
        if not refs:
            candidate_limitations.append('Sugestão visual sem fala transcrita; início e fim são aproximados.')
        elif not opening:
            candidate_limitations.append('Início sem pausa ou fim de frase anterior; o assunto pode começar antes.')
        if continuation:
            candidate_limitations.append('A fala continua logo após o corte; considere uma continuação ou revisão manual.')
        if count / (end - start) > 5.2:
            candidate_limitations.append('Fala transcrita muito densa; confira sobreposição de vozes e entendimento do trecho.')
        if opening_housekeeping:
            candidate_limitations.append('A abertura contém um recado de operação da live; considere iniciar mais adiante.')
        reasons = ([f'Contém {len(refs)} segmento(s) completo(s) de fala e {count} palavras transcritas.',
                    reason, 'Trecho de fala: ' + refs[0].observation[:200]] if refs else
                   ['Mudança visual detectada em amostragem; conteúdo não identificado.'])
        if visual:
            reasons.append(f'{len(visual)} mudança(s) de quadro observada(s) no intervalo.')
        if energy:
            reasons.append(f'{len(energy)} janela(s) com energia sonora elevada.')
        if affect:
            reasons.append(f'{len(affect)} expressão(ões) afetiva(s) na transcrição; emoção real não inferida.')
        if hook_question:
            reasons.append('Pergunta com pelo menos cinco palavras observada nos quatro segundos iniciais.')
        candidates.append(ClipCandidate(candidate_id='candidate_' + identifier, asset_id=asset.asset_id,
                          start_s=start, end_s=end, features={'word_count': float(count), 'words_per_s': count / (end-start),
                          'boundary_signals': float(boundary), 'visual_changes': float(len(visual)),
                          'audio_energy_events': float(len(energy)), 'affective_cues': float(len(affect)),
                          'opening_signal': float(opening),
                          'hook_question_observed': float(hook_question),
                          'opening_housekeeping_observed': float(opening_housekeeping),
                          'speech_density_capped': float(count / (end - start) > 4.4),
                          'continuation_suggested': float(continuation)},
                          evidence_ids=[item.evidence_id for item in refs + visual + audio],
                          reasons=reasons,
                          limitations=candidate_limitations,
                          rank_score=score, versions=versions))
        if len(candidates) == request.top_k:
            break
    if request.instructions:
        limitations.append('Orientação livre registrada no pedido; baseline não interpreta essa orientação.')
    if request.duration_mode == 'exact':
        limitations.append('Duração exata pode cortar uma fala em andamento; modo faixa permite buscar pausa ou fim de frase.')
    if not candidates:
        limitations.append('Sem fala completa compatível com a duração solicitada.')
    elif len(candidates) < request.top_k:
        limitations.append('Há menos regiões elegíveis do que o número solicitado; momentos operacionais da live são omitidos.')
    return AnalysisResult(asset=asset, request=request, evidence=evidence,
                          candidates=candidates, limitations=limitations)


def _repetitive(observation: str) -> bool:
    if _repetition_loop(observation):
        return True
    words = re.findall(r'\w+', observation.lower())
    return len(words) >= 8 and Counter(words).most_common(1)[0][1] / len(words) > .55
