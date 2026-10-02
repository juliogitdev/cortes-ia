import sys
from types import SimpleNamespace

import pytest

from clip_platform.selection.baseline import select
from clip_platform.shared.contracts import AnalysisRequest, Evidence, EvidenceBundle, MediaAsset, Provenance
from clip_platform.speech.transcribe import transcribe


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
