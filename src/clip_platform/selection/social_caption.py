"""Editable post copy grounded in the clip transcript and known source context."""
import re

from clip_platform.shared.contracts import AnalysisResult, ClipCandidate
from clip_platform.speech.transcribe import _repetition_loop


def _speech(analysis: AnalysisResult, candidate: ClipCandidate) -> str:
    return ' '.join(item.observation for item in analysis.evidence.transcript
                    if item.evidence_id in candidate.evidence_ids
                    and item.start_s < candidate.end_s and item.end_s > candidate.start_s
                    and not _repetition_loop(item.observation))


def _creator(project_name: str, source_uri: str) -> tuple[str, str]:
    # This source's public uploader/title was checked on 2026-10-03.
    if 'XBKuTcBuFKg' in source_uri:
        return 'Yuri22', '#Yuri22'
    match = re.search(r'\blive\s+(?:do|da|de)\s+([\wÀ-ÿ]+)', project_name, re.I)
    if match and len(match[1]) >= 3:
        name = match[1].capitalize()
        return name, '#' + re.sub(r'\W+', '', name)
    return '', ''


_TOPICS = (
    (r'\b(?:lula|pol[ií]tica|presidente)\b', 'A conversa entrou em política durante a live.', '#Politica'),
    (r'\b(?:roubou|roubar)\b.{0,45}\b(?:milh[aã]o|milh[oõ]es)\b', 'Uma acusação de dinheiro virou assunto na live.', '#Treta'),
    (r'\b(?:crian[cç]a|inf[aâ]ncia|era loiro|foto antiga)\b', 'Uma lembrança da infância apareceu na conversa.', '#Infancia'),
    (r'\b(?:edita(?:r|do)|montagem|barriga)\b', 'Uma edição de vídeo virou assunto na live.', '#Reacao'),
    (r'\b(?:m[uú]sica|cantor|artista)\b', 'A música virou assunto na conversa.', '#Musica'),
    (r'\b(?:avi[aã]o|voar|voo)\b', 'Uma conversa sobre voar apareceu na live.', '#Viagem'),
    (r'\b(?:voltar comigo|namorad[ao]|relacionamento)\b', 'Um relacionamento entrou na conversa.', '#Relacionamento'),
    (r'\b(?:abra[cç]o|amizade|amigo)\b', 'Uma conversa sobre amizade na live.', '#Amizade'),
    (r'\b(?:pizza|pizzas|receita|cozinha|recheio|frango)\b', 'A conversa sobre comida rendeu esse trecho.', '#Comida'),
    (r'\b(?:futebol|gols?|partida de futebol)\b', 'O futebol entrou no papo da live.', '#Futebol'),
    (r'\b(?:gameplay|jogando|videogame|game)\b', 'Gameplay e conversa ao vivo.', '#Gameplay'),
)


def _topics(speech: str) -> list[tuple[str, str]]:
    return [(copy, tag) for pattern, copy, tag in _TOPICS if re.search(pattern, speech, re.I)]


def suggest_headline(analysis: AnalysisResult, candidate: ClipCandidate) -> str:
    """Use observed words, never invent a claim from an unreliable ASR segment."""
    parts = [item.observation.strip() for item in analysis.evidence.transcript
             if item.evidence_id in candidate.evidence_ids
             and item.start_s >= candidate.start_s and item.start_s < candidate.start_s + 8
             and not _repetition_loop(item.observation)]
    for part in parts:
        clause = re.split(r'[.!?…]', part, maxsplit=1)[0].strip(' ,:;–-')
        words = clause.split()
        if 5 <= len(words) <= 17 and 20 <= len(clause) <= 90:
            return clause.upper()
    words = re.findall(r'\S+', ' '.join(parts))
    if len(words) >= 5:
        return ' '.join(words[:12]).strip(' ,:;–-').upper()[:90]
    return 'MOMENTO DA LIVE'


def suggest_caption(analysis: AnalysisResult, candidate: ClipCandidate,
                    project_name: str = '', source_uri: str = '') -> str:
    speech = _speech(analysis, candidate)
    creator, _ = _creator(project_name, source_uri)
    if re.search(r'\bpizza(?:s)?\b', speech, re.I):
        if re.search(r'\bfrango\b', speech, re.I):
            return 'Frango no recheio da pizza entrou na conversa.'
        if re.search(r'\bqueij[oa]s?\b', speech, re.I):
            return 'O queijo da pizza virou assunto nesse trecho.'
        return 'Pizza no meio da live: o preparo rendeu conversa.'
    if re.search(r'master\s*chef', project_name, re.I) and re.search(r'\b(?:sal|queijo|comer|cozinha|recheio)\b', speech, re.I):
        return 'Um detalhe do preparo na live de culinária.'
    topics = _topics(speech)
    if topics:
        copy = topics[0][0]
        return f'{creator}: {copy[0].lower() + copy[1:]}' if creator else copy
    # A fluent looking ASR sentence can still be wrong. Avoid posting it as a quote.
    return f'Trecho da live de {creator}.' if creator else 'Trecho da live.'


def suggest_hashtags(analysis: AnalysisResult, candidate: ClipCandidate,
                     project_name: str = '', source_uri: str = '') -> str:
    speech = _speech(analysis, candidate)
    _name, creator_tag = _creator(project_name, source_uri)
    tags = ['#Cortes']
    if creator_tag:
        tags.append(creator_tag)
    tags.extend(tag for _copy, tag in _topics(speech))
    if re.search(r'master\s*chef', project_name, re.I) and re.search(r'\b(?:sal|queijo|comer|cozinha|recheio)\b', speech, re.I):
        tags.append('#Culinaria')
    extras = ((r'\b(?:podcast|flow)\b', '#Podcast'),
              (r'\bpizza(?:s)?\b', '#Pizza'),
              (r'\b(?:cozinha|receita|culin[aá]ria)\b', '#Culinaria'),
              (r'\blula\b', '#Lula'))
    tags.extend(tag for pattern, tag in extras if re.search(pattern, speech, re.I))
    return ' '.join(list(dict.fromkeys(tags))[:5])
