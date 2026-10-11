"""Local-only speech adapter. Receives full audio, hence original offset is zero."""
import hashlib
import json
import math
import re
import sys
import tempfile
import wave
import zlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from clip_platform.shared.contracts import Evidence, EvidenceBundle, MediaAsset, Provenance


def _version(package):
    try:
        return version(package)
    except PackageNotFoundError:
        return "not-installed"


def _sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return 'sha256:' + digest.hexdigest()


def _process_peak_memory():
    """Lifetime process RAM high-water mark; never a stage delta or VRAM."""
    try:
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                    (name, ctypes.c_size_t) for name in (
                        'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                        'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                        'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]

            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            psapi = ctypes.WinDLL('psapi', use_last_error=True)
            kernel.GetCurrentProcess.argtypes = []
            kernel.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
                return None
            return {'method': 'Windows GetProcessMemoryInfo.PeakWorkingSetSize',
                    'peak_working_set_bytes': counters.PeakWorkingSetSize,
                    'scope': 'entire process lifetime RAM including libraries; not VRAM'}
        if sys.platform.startswith('linux'):
            import resource
            return {'method': 'Linux resource.getrusage(RUSAGE_SELF).ru_maxrss * 1024',
                    'peak_working_set_bytes': int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024),
                    'scope': 'entire process lifetime RAM including libraries; not VRAM'}
    except (ImportError, AttributeError, OSError, ValueError):
        pass
    return None


def _repetition_loop(text: str) -> bool:
    """Reject decoder loops inside one segment without guessing replacement speech."""
    encoded = text.encode('utf-8')
    if len(encoded) >= 120 and len(encoded) / max(1, len(zlib.compress(encoded))) > 2.8:
        return True
    tokens = re.findall(r'\w+', text.casefold())
    if len(tokens) < 4:
        return False
    if len(tokens) >= 4 and len(set(tokens)) == 1 and tokens[0] in {'ai', 'aí', 'ah', 'hã', 'hum'}:
        return True
    if len(tokens) < 12:
        return False
    for width in range(1, min(8, len(tokens) // 4) + 1):
        for start in range(len(tokens) - width * 4 + 1):
            phrase = tokens[start:start + width]
            repetitions = 1
            while tokens[start + repetitions * width:start + (repetitions + 1) * width] == phrase:
                repetitions += 1
            if repetitions >= 4 and repetitions * width >= len(tokens) * .6:
                return True
    return False


def _normalized_text(text: str) -> str:
    return ' '.join(re.findall(r'\w+', text.casefold()))


def _remove_repeated_runs(records, suppressed):
    """Remove local runs of identical short ASR segments, preserving other speech."""
    kept = []
    index = 0
    while index < len(records):
        phrase = _normalized_text(records[index][2])
        end = index + 1
        while end < len(records) and _normalized_text(records[end][2]) == phrase:
            end += 1
        threshold = 6 if len(phrase.split()) <= 4 else 4
        if phrase and end - index >= threshold:
            suppressed.extend({'start_s': record[0], 'end_s': record[1],
                               'reason': 'repeated_segment_run'} for record in records[index:end])
        else:
            kept.extend(records[index:end])
        index = end
    return kept


def transcribe(asset: MediaAsset, audio_path: Path, model_path: str, device='cpu', progress_callback=None) -> EvidenceBundle:
    if device not in {'cpu', 'cuda'}:
        raise ValueError('device deve ser cpu ou cuda; não há fallback automático')
    audio_path = Path(audio_path).resolve(strict=True)
    model_dir = Path(model_path).resolve(strict=True)
    if not audio_path.is_file() or not model_dir.is_dir() or not (model_dir / 'model.bin').is_file():
        raise ValueError('Áudio deve ser arquivo e modelo deve ser diretório CTranslate2 local com model.bin')
    # Content identity work is explicitly outside the model-load/inference timer.
    model_identity = {'model_bin_sha256': _sha256(model_dir / 'model.bin')}
    manifest_path = model_dir / 'download-manifest.json'
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        if not isinstance(manifest, dict):
            raise ValueError('download-manifest.json deve ser objeto JSON')
        # Manifest is untrusted metadata; do not execute or fetch its contents.
        model_identity.update({key: manifest[key] for key in ('repo', 'revision')
                               if isinstance(manifest.get(key), str)})
    # Import delayed: panel and deterministic engine never load inference backends.
    if device == 'cuda':
        from clip_platform.speech.cuda import configure_cuda_libraries
        configure_cuda_libraries()
    from faster_whisper import WhisperModel

    started = perf_counter()
    compute_type = 'int8' if device == 'cpu' else 'float16'
    model = WhisperModel(str(model_dir), device=device, compute_type=compute_type,
                         local_files_only=True)
    def transcribed_segments():
        options = dict(language='pt', word_timestamps=True, beam_size=5,
                       temperature=0.0, vad_filter=False,
                       condition_on_previous_text=False)
        if asset.duration_s <= 600:
            segments, info = model.transcribe(str(audio_path), **options)
            for segment in segments:
                yield segment, 0.0, info.language
            return
        # Whisper can loop on a phrase when given a multi-hour recording. Feed
        # bounded PCM chunks and restore every timestamp to the original audio.
        with tempfile.TemporaryDirectory(prefix='speech-chunks-', dir=audio_path.parent) as temporary:
            with wave.open(str(audio_path), 'rb') as source:
                if source.getnchannels() != 1 or source.getframerate() != 16000 or source.getsampwidth() != 2:
                    raise ValueError('Áudio de transcrição deve ser PCM mono 16 kHz')
                rate = source.getframerate()
                step = 300 * rate
                start_frame = 0
                while start_frame < source.getnframes():
                    chunk = Path(temporary) / f'{start_frame}.wav'
                    with wave.open(str(chunk), 'wb') as output:
                        output.setparams(source.getparams())
                        output.writeframes(source.readframes(step))
                    segments, info = model.transcribe(str(chunk), **options)
                    for segment in segments:
                        yield segment, start_frame / rate, info.language
                    chunk.unlink(missing_ok=True)
                    start_frame += step
    records = []
    previous_start = 0.0
    recognized_language = 'pt'
    invalid_words = 0
    suppressed = []
    quality = ['Transcrição automática não revisada; horários e palavras podem conter erros.']
    for segment, offset, recognized_language in transcribed_segments():
        text = segment.text.strip()
        if not text:
            continue
        start, end = offset + float(segment.start), offset + float(segment.end)
        if not (math.isfinite(start) and math.isfinite(end) and previous_start <= start < end <= asset.duration_s):
            raise ValueError('Timestamp de transcrição fora da mídia original')
        if progress_callback:
            progress_callback(min(1., end / asset.duration_s))
        previous_start = start
        if _repetition_loop(text):
            suppressed.append({'start_s': start, 'end_s': end, 'reason': 'repetitive_decoder_loop'})
            continue
        words = []
        previous_word_start = start
        for word in segment.words or []:
            ws, we = offset + float(word.start), offset + float(word.end)
            if not (math.isfinite(ws) and math.isfinite(we) and previous_word_start <= ws <= we <= end):
                invalid_words += 1
                continue
            previous_word_start = ws
            words.append({'start_s': ws, 'end_s': we, 'text': word.word})
        metrics = {key: float(value) for key in ('avg_logprob', 'compression_ratio', 'no_speech_prob')
                   if (value := getattr(segment, key, None)) is not None and math.isfinite(float(value))}
        records.append((start, end, text, words, metrics))
    elapsed = perf_counter() - started
    if len(records) >= 100:
        from collections import Counter
        normalized = [_normalized_text(text) for _, _, text, _, _ in records]
        repeated, count = Counter(normalized).most_common(1)[0]
        if repeated and count / len(records) >= .9:
            raise ValueError('Transcrição inválida: a mesma frase foi repetida em quase toda a gravação. Reprocessar a fala antes de gerar cortes.')
    records = _remove_repeated_runs(records, suppressed)
    if progress_callback:
        progress_callback(1.)
    if invalid_words:
        quality.append(f'{invalid_words} palavra(s) com horário inconsistente foram omitidas; segmentos preservados.')
    if suppressed:
        quality.append(f'{len(suppressed)} segmento(s) repetitivos foram omitidos da análise e das legendas; revisar os intervalos registrados na proveniência.')
    memory = _process_peak_memory()
    audio_hash = _sha256(audio_path)
    settings = {'device': device, 'compute_type': compute_type, 'model_path': str(model_dir),
                'language': recognized_language, 'word_timestamps': True, 'beam_size': 5,
                'temperature': 0.0, 'vad_filter': False, 'condition_on_previous_text': False,
                'chunk_s': 300 if asset.duration_s > 600 else None,
                'suppressed_segments': suppressed,
                'local_files_only': True,
                'faster_whisper_version': _version('faster-whisper'),
                'ctranslate2_version': _version('ctranslate2'), 'elapsed_s': elapsed,
                'offset_policy': 'full original audio; offset zero',
                'model_identity': model_identity, 'model_hash_timing': 'excluded from elapsed_s',
                'memory_measurement': memory}
    provenance = Provenance(run_id='speech_' + uuid4().hex,
                            source_uri=str(audio_path), artifact_hash=audio_hash,
                            original_offset_s=0, settings=settings)
    transcript = []
    for index, (start, end, text, words, metrics) in enumerate(records):
        item_provenance = provenance.model_copy(deep=True)
        item_provenance.settings['words'] = words
        item_provenance.settings['confidence_signals'] = metrics
        transcript.append(Evidence(evidence_id=f'speech_{index:06d}', asset_id=asset.asset_id,
                                   start_s=start, end_s=end, observation=text,
                                   provenance=item_provenance))
    if not transcript:
        quality.append('Nenhuma fala reconhecida; isso não prova ausência de acontecimentos visuais.')
    return EvidenceBundle(asset_id=asset.asset_id, transcript=transcript, visual_events=[],
                          audio_events=[], quality=quality, provenance=[provenance])
