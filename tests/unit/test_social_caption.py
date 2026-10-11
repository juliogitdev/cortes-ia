from types import SimpleNamespace

from clip_platform.selection.social_caption import suggest_caption, suggest_hashtags, suggest_headline
from clip_platform.selection.baseline import _stream_admin_window


def _clip(lines):
    transcript = [SimpleNamespace(evidence_id=str(i), start_s=i, end_s=i + 1,
                                  observation=line) for i, line in enumerate(lines)]
    analysis = SimpleNamespace(evidence=SimpleNamespace(transcript=transcript))
    candidate = SimpleNamespace(evidence_ids=[str(i) for i in range(len(lines))],
                                start_s=0, end_s=len(lines))
    return analysis, candidate


def test_caption_uses_observed_speech_and_avoids_repetition_loop():
    analysis, candidate = _clip([
        'pão de queijo pão de queijo pão de queijo pão de queijo pão de queijo',
        'Hoje mostramos uma receita de frango para comer em casa.',
    ])
    caption = suggest_caption(analysis, candidate)
    assert 'pão de queijo' not in caption
    assert 'O que você achou' not in caption
    assert 'comida' in caption


def test_hashtags_follow_observed_topics_only():
    analysis, candidate = _clip(['Hoje vamos fazer uma receita de pizza na cozinha.'])
    assert suggest_hashtags(analysis, candidate) == '#Cortes #Comida #Pizza #Culinaria'


def test_creator_and_specific_topic_are_grounded_in_context():
    analysis, candidate = _clip(['Eu não gosto do Lula, mas essa é só minha opinião.'])
    assert suggest_hashtags(analysis, candidate, 'live do yuri 02/10',
                            'https://www.youtube.com/watch?v=XBKuTcBuFKg') == '#Cortes #Yuri22 #Politica #Lula'
    assert suggest_caption(analysis, candidate, 'live do yuri 02/10',
                           'https://www.youtube.com/watch?v=XBKuTcBuFKg').startswith('Yuri22:')


def test_feedback_pattern_deprioritizes_like_requests():
    assert _stream_admin_window([SimpleNamespace(observation='Bora bater 30 mil likes, tropa!')])
    assert not _stream_admin_window([SimpleNamespace(observation='Uma conversa sobre a infância dele.')])


def test_music_remains_main_topic_when_airplane_is_mentioned():
    analysis, candidate = _clip(['Ele pagou os artistas para fazer a música, mas depois mencionou o avião.'])
    assert 'música' in suggest_caption(analysis, candidate)
    assert '#Musica' in suggest_hashtags(analysis, candidate)


def test_video_headline_uses_observed_opening_and_stays_short():
    analysis, candidate = _clip(['Por que você mudou de ideia depois da conversa?',
                                 'A explicação apareceu logo em seguida.'])
    headline = suggest_headline(analysis, candidate)
    assert headline == 'POR QUE VOCÊ MUDOU DE IDEIA DEPOIS DA CONVERSA'
    assert len(headline) <= 120
