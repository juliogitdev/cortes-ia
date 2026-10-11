import sys
from types import SimpleNamespace

import pytest

from clip_platform.selection.baseline import select, _speech_density_score, _opening_housekeeping
from clip_platform.shared.contracts import AnalysisRequest, Evidence, EvidenceBundle, MediaAsset, Provenance
from clip_platform.speech.transcribe import transcribe, _repetition_loop


@pytest.fixture
def asset():
    return MediaAsset(asset_id='a', source_uri='local:test', content_hash='sha256:'+'0'*64,
                      duration_s=60, tracks=['audio','video'], local_path='test.mp4')


def bundle(asset, spans=((2, 5), (25, 28), (50, 53))):
    provenance = Provenance(run_id='fixture', source_uri='synthetic', artifact_hash=asset.content_hash,
                            original_offset_s=0, settings={})
    return EvidenceBundle(asset_id=asset.asset_id, transcript=[Evidence(evidence_id=f'e{i}',
            asset_id=asset.asset_id, start_s=start, end_s=end, observation='Fala sintética verificável aqui.',
            provenance=provenance) for i,(start,end) in enumerate(spans)],
            visual_events=[], audio_events=[], quality=[], provenance=[provenance])


def request(asset, **overrides):
    data = dict(asset_id=asset.asset_id, duration_mode='exact', target_s=10, top_k=5, niche='conversa')
    data.update(overrides)
    return AnalysisRequest(**data)


def test_exact_deterministic_references_and_no_overlap(asset):
    evidence = bundle(asset)
    output = select(asset,evidence,request(asset))
    assert output == select(asset,evidence,request(asset))
    assert len(output.candidates) == 3
    for candidate in output.candidates:
        assert candidate.end_s-candidate.start_s == 10
        assert candidate.evidence_ids
        assert candidate.end_s <= asset.duration_s
    assert all(left.end_s <= right.start_s for left,right in zip(output.candidates,output.candidates[1:]))


def test_range_top_k(asset):
    output = select(asset,bundle(asset),request(asset,duration_mode='range',target_s=None,min_s=5,max_s=12,top_k=1))
    assert len(output.candidates) == 1
    assert 5 <= output.candidates[0].end_s-output.candidates[0].start_s <= 12


def test_dense_transcript_no_longer_wins_by_word_count_alone():
    assert _speech_density_score(45, 10) < _speech_density_score(40, 10) + .5
    assert _speech_density_score(60, 10) < _speech_density_score(45, 10)


def test_opening_question_is_observed_and_explained(asset):
    evidence = bundle(asset, ((0, 5), (5.5, 10)))
    evidence.transcript[0].observation = 'Por que essa decisão mudou a conversa inteira?'
    evidence.transcript[1].observation = 'Aqui está a explicação completa.'
    output = select(asset, evidence, request(asset, target_s=11, top_k=1))
    assert output.candidates[0].features['hook_question_observed'] == 1
    assert any('Pergunta com pelo menos cinco palavras' in reason for reason in output.candidates[0].reasons)


def test_housekeeping_only_counts_at_opening(asset):
    evidence = bundle(asset, ((0, 4), (10, 14)))
    evidence.transcript[0].observation = 'Vou ver mais dois vídeos aqui, tropa.'
    evidence.transcript[1].observation = 'A conversa começa com a acusação.'
    assert _opening_housekeeping(evidence.transcript, 0)
    assert not _opening_housekeeping(evidence.transcript, 10)


def test_live_operations_do_not_fill_requested_clip_count(asset):
    evidence = bundle(asset, ((0, 5), (20, 25), (40, 45)))
    evidence.transcript[0].observation = 'Vou ver mais dois vídeos aqui, tropa.'
    evidence.transcript[1].observation = 'Entra aí geral e vota, a votação está aberta.'
    evidence.transcript[2].observation = 'Por que essa decisão mudou toda a conversa?'
    output = select(asset, evidence, request(asset, target_s=10, top_k=3))
    assert len(output.candidates) == 1
    assert output.candidates[0].start_s == 40
    assert any('menos regiões elegíveis' in item for item in output.limitations)


def test_range_ends_after_observed_sentence_and_keeps_exact_mode(asset):
    evidence = bundle(asset, ((0, 12), (12.1, 24), (24.1, 36)))
    evidence.transcript[0].observation = 'Começo do assunto sem final'
    evidence.transcript[1].observation = 'Agora a frase termina.'
    evidence.transcript[2].observation = 'Novo assunto ainda em andamento'
    ranged = select(asset, evidence, request(asset, duration_mode='range', target_s=None,
                                          min_s=20, max_s=30, top_k=1))
    assert len(ranged.candidates) == 1
    assert ranged.candidates[0].end_s == pytest.approx(24.05)
    assert ranged.candidates[0].features['boundary_signals'] >= 1
    assert not any('encerramento claro' in item for item in ranged.candidates[0].limitations)
    exact = select(asset, evidence, request(asset, target_s=30, top_k=1))
    assert exact.candidates[0].end_s - exact.candidates[0].start_s == 30
    assert any('Duração exata pode cortar' in item for item in exact.limitations)


def test_range_marks_uncertain_ending_when_no_pause_or_punctuation(asset):
    evidence = bundle(asset, ((0, 12), (12.1, 25), (25.1, 38), (38.1, 50)))
    for item in evidence.transcript:
        item.observation = 'Fala continua sem pontuação'
    ranged = select(asset, evidence, request(asset, duration_mode='range', target_s=None,
                                          min_s=20, max_s=30, top_k=5))
    assert ranged.candidates
    assert all(c.end_s - c.start_s <= 30 for c in ranged.candidates)
    assert any(any('encerramento claro' in item for item in c.limitations) for c in ranged.candidates)


def test_repetitive_transcript_does_not_dominate_and_visual_event_can_seed_candidate(asset):
    evidence = bundle(asset, ((1, 20),))
    evidence.transcript[0].observation = 't ' * 30
    signal = evidence.transcript[0].model_copy(deep=True)
    signal.evidence_id = 'visual_1'
    signal.start_s = 30
    signal.end_s = 31
    signal.observation = 'Mudança visual entre quadros amostrados.'
    evidence.visual_events = [signal]
    output = select(asset, evidence, request(asset, duration_mode='range', target_s=None,
                                             min_s=10, max_s=20, top_k=1))
    assert len(output.candidates) == 1
    assert output.candidates[0].features['visual_changes'] == 1
    assert output.candidates[0].features['word_count'] == 0
    assert any('sem fala transcrita' in item for item in output.candidates[0].limitations)


def test_repeated_phrase_inside_segment_is_excluded_from_ranking(asset):
    evidence = bundle(asset, ((1, 20),))
    evidence.transcript[0].observation = 'Pão de queijo? ' * 12
    output = select(asset, evidence, request(asset, target_s=10))
    assert not output.candidates


def test_promotional_call_to_action_is_not_ranked_as_editorial_clip(asset):
    evidence = bundle(asset, ((0, 20), (30, 50)))
    evidence.transcript[0].observation = 'Vamos conversar sobre as decisões que mudaram o país.'
    evidence.transcript[1].observation = ('Acesse o QR Code e o link na descrição para aprender inglês '
                                          'na escola online com desconto e prêmios.')
    output = select(asset, evidence, request(asset, target_s=20, top_k=2))
    assert len(output.candidates) == 1
    assert output.candidates[0].start_s == 0


def test_impossible_and_silent_are_explicit(asset):
    assert not select(asset,bundle(asset),request(asset,target_s=61)).candidates
    output = select(asset,bundle(asset,()),request(asset))
    assert not output.candidates and output.limitations


def test_cross_asset_and_bad_time_rejected(asset):
    with pytest.raises(ValueError):
        select(asset,bundle(asset),request(asset,asset_id='other'))
    with pytest.raises(ValueError):
        select(asset,bundle(asset,((59,61),)),request(asset))


def test_no_complete_quote_not_presented_as_evidence(asset):
    output = select(asset,bundle(asset,((0,20),)),request(asset,target_s=5))
    assert not output.candidates


def mock_backend(monkeypatch, segments, fail=False):
    calls = []
    monkeypatch.setattr('clip_platform.speech.cuda.configure_cuda_libraries', lambda: None)
    class Model:
        def __init__(self, path, **kwargs):
            calls.append((path,kwargs))
            if fail:
                raise RuntimeError('backend unavailable')
        def transcribe(self, path, **kwargs):
            calls.append((path,kwargs))
            return iter(segments), SimpleNamespace(language='pt')
    monkeypatch.setitem(sys.modules,'faster_whisper',SimpleNamespace(WhisperModel=Model))
    return calls


@pytest.fixture
def local_files(tmp_path):
    audio = tmp_path/'audio.wav'
    audio.write_bytes(b'synthetic mock audio')
    model = tmp_path/'model'
    model.mkdir()
    (model/'model.bin').write_bytes(b'synthetic mock weights')
    return audio,model


@pytest.mark.parametrize('device,compute',[('cpu','int8'),('cuda','float16')])
def test_adapter_explicit_backend_words_provenance(asset,local_files,monkeypatch,device,compute):
    segment = SimpleNamespace(start=2,end=4,text=' Olá mundo ',words=[
        SimpleNamespace(start=2,end=3,word='Olá'),SimpleNamespace(start=3,end=4,word='mundo')])
    calls = mock_backend(monkeypatch,[segment])
    output = transcribe(asset,*local_files,device=device)
    assert calls[0][1] == dict(device=device,compute_type=compute,local_files_only=True)
    assert calls[1][1]['word_timestamps'] is True
    assert calls[1][1]['vad_filter'] is False
    assert calls[1][1]['condition_on_previous_text'] is False
    assert output.transcript[0].start_s == 2
    assert output.transcript[0].provenance.settings['words'][1]['end_s'] == 4
    assert output.provenance[0].settings['elapsed_s'] >= 0
    assert output.provenance[0].original_offset_s == 0


def test_adapter_backend_failure_no_cpu_fallback(asset,local_files,monkeypatch):
    calls = mock_backend(monkeypatch,[],fail=True)
    with pytest.raises(RuntimeError,match='backend unavailable'):
        transcribe(asset,*local_files,device='cuda')
    assert len(calls) == 1


def test_adapter_bad_timestamp_and_missing_model(asset,local_files,monkeypatch):
    mock_backend(monkeypatch,[SimpleNamespace(start=59,end=62,text='fora',words=[])])
    with pytest.raises(ValueError,match='Timestamp'):
        transcribe(asset,*local_files)
    with pytest.raises(FileNotFoundError):
        transcribe(asset,local_files[0],'not-a-local-model')


def test_adapter_omits_invalid_word_timestamp_and_preserves_segment(asset,local_files,monkeypatch):
    mock_backend(monkeypatch,[SimpleNamespace(start=2,end=4,text='fala válida',words=[
        SimpleNamespace(start=2,end=3,word='fala'),
        SimpleNamespace(start=3.9,end=4.2,word='válida')])])
    output = transcribe(asset,*local_files)
    assert len(output.transcript) == 1
    assert len(output.transcript[0].provenance.settings['words']) == 1
    assert any('horário inconsistente' in message for message in output.quality)


def test_adapter_silence(asset,local_files,monkeypatch):
    mock_backend(monkeypatch,[])
    output = transcribe(asset,*local_files)
    assert not output.transcript
    assert any('Nenhuma fala' in message for message in output.quality)


def test_adapter_out_of_order_segments_rejected(asset,local_files,monkeypatch):
    mock_backend(monkeypatch,[SimpleNamespace(start=10,end=12,text='primeiro',words=[]),
                              SimpleNamespace(start=5,end=7,text='depois',words=[])])
    with pytest.raises(ValueError,match='Timestamp'):
        transcribe(asset,*local_files)


def test_adapter_rejects_repeated_whisper_hallucination(asset,local_files,monkeypatch):
    repeated = [SimpleNamespace(start=index * .5, end=index * .5 + .4,
                text='E aí', words=[]) for index in range(100)]
    mock_backend(monkeypatch,repeated)
    with pytest.raises(ValueError, match='mesma frase foi repetida'):
        transcribe(asset,*local_files)


def test_adapter_omits_internal_repetition_and_uncertain_interjection(asset,local_files,monkeypatch):
    assert _repetition_loop('Pão de queijo? ' * 12)
    assert _repetition_loop('Você vai ter acesso a outros sete idiomas. ' * 4 +
                            'Você vai ter acesso ao outro sete idiomas. ' * 3)
    assert _repetition_loop('Ai ai ai ai ai')
    assert not _repetition_loop('Pão de queijo? Só uma vez, por favor.')
    segments = [
        SimpleNamespace(start=1, end=2, text='Pão de queijo? Só uma vez.', words=[],
                        avg_logprob=-.2, compression_ratio=1.2, no_speech_prob=.1),
        SimpleNamespace(start=3, end=8, text='Pão de queijo? ' * 12, words=[]),
        SimpleNamespace(start=9, end=10, text='Ai ai ai ai ai', words=[]),
        SimpleNamespace(start=11, end=13, text='Vamos conversar sobre o debate.', words=[]),
        SimpleNamespace(start=14, end=18,
                        text='Você vai ter acesso a outros sete idiomas. ' * 4 +
                             'Você vai ter acesso ao outro sete idiomas. ' * 3,
                        words=[]),
    ]
    mock_backend(monkeypatch,segments)
    output = transcribe(asset,*local_files)
    assert [item.observation for item in output.transcript] == [
        'Pão de queijo? Só uma vez.', 'Vamos conversar sobre o debate.']
    assert output.transcript[0].provenance.settings['confidence_signals']['compression_ratio'] == 1.2
    assert output.provenance[0].settings['suppressed_segments'] == [
        {'start_s': 3., 'end_s': 8., 'reason': 'repetitive_decoder_loop'},
        {'start_s': 9., 'end_s': 10., 'reason': 'repetitive_decoder_loop'},
        {'start_s': 14., 'end_s': 18., 'reason': 'repetitive_decoder_loop'}]


def test_adapter_omits_local_run_of_repeated_short_segments(asset,local_files,monkeypatch):
    segments = [SimpleNamespace(start=index, end=index + .8,
                text='E aí?' if index % 2 else 'E aí.', words=[])
                for index in range(6)]
    segments.append(SimpleNamespace(start=7, end=9, text='Agora vamos ao assunto.', words=[]))
    mock_backend(monkeypatch,segments)
    output = transcribe(asset,*local_files)
    assert [item.observation for item in output.transcript] == ['Agora vamos ao assunto.']
    assert len(output.provenance[0].settings['suppressed_segments']) == 6
    assert all(item['reason'] == 'repeated_segment_run'
               for item in output.provenance[0].settings['suppressed_segments'])


def test_adapter_long_audio_restores_chunk_offsets(asset,local_files,monkeypatch):
    import wave
    audio, model = local_files
    with wave.open(str(audio), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b'\0\0' * 16000 * 610)
    segment = SimpleNamespace(start=1., end=2., text='Fala diferente', words=[
        SimpleNamespace(start=1., end=2., word='Fala')])
    calls = mock_backend(monkeypatch,[segment])
    long_asset = asset.model_copy(update={'duration_s': 610})
    output = transcribe(long_asset,audio,model)
    assert len(output.transcript) == 3
    assert [item.start_s for item in output.transcript] == [1., 301., 601.]
    assert output.transcript[1].provenance.settings['words'][0]['start_s'] == 301.
    assert output.provenance[0].settings['chunk_s'] == 300
    assert len([item for item in calls if item[0].endswith('.wav')]) == 3
