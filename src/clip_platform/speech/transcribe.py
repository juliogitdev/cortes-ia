"""Local-only speech adapter. Receives full audio, hence original offset is zero."""
import hashlib
import json
import math
import sys
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


def transcribe(asset: MediaAsset, audio_path: Path, model_path: str, device='cpu') -> EvidenceBundle:
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
    from faster_whisper import WhisperModel

    started = perf_counter()
    compute_type = 'int8' if device == 'cpu' else 'float16'
    model = WhisperModel(str(model_dir), device=device, compute_type=compute_type,
                         local_files_only=True)
    segments, info = model.transcribe(str(audio_path), language='pt', word_timestamps=True,
                                     beam_size=5, temperature=0.0, vad_filter=False)
    records = []
    previous_start = 0.0
    quality = ['Transcrição automática não revisada; baseline de fala.']
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        start, end = float(segment.start), float(segment.end)
        if not (math.isfinite(start) and math.isfinite(end) and previous_start <= start < end <= asset.duration_s):
            raise ValueError('Timestamp de transcrição fora da mídia original')
        previous_start = start
        words = []
        previous_word_start = start
        for word in segment.words or []:
            ws, we = float(word.start), float(word.end)
            if not (math.isfinite(ws) and math.isfinite(we) and previous_word_start <= ws <= we <= end):
                raise ValueError('Timestamp de palavra fora do segmento')
            previous_word_start = ws
            words.append({'start_s': ws, 'end_s': we, 'text': word.word})
        records.append((start, end, text, words))
    elapsed = perf_counter() - started
    memory = _process_peak_memory()
    audio_hash = _sha256(audio_path)
    settings = {'device': device, 'compute_type': compute_type, 'model_path': str(model_dir),
                'language': info.language, 'word_timestamps': True, 'beam_size': 5,
                'temperature': 0.0, 'vad_filter': False, 'local_files_only': True,
                'faster_whisper_version': _version('faster-whisper'),
                'ctranslate2_version': _version('ctranslate2'), 'elapsed_s': elapsed,
                'offset_policy': 'full original audio; offset zero',
                'model_identity': model_identity, 'model_hash_timing': 'excluded from elapsed_s',
                'memory_measurement': memory}
    provenance = Provenance(run_id='speech_' + uuid4().hex,
                            source_uri=str(audio_path), artifact_hash=audio_hash,
                            original_offset_s=0, settings=settings)
    transcript = []
    for index, (start, end, text, words) in enumerate(records):
        item_provenance = provenance.model_copy(deep=True)
        item_provenance.settings['words'] = words
        transcript.append(Evidence(evidence_id=f'speech_{index:06d}', asset_id=asset.asset_id,
                                   start_s=start, end_s=end, observation=text,
                                   provenance=item_provenance))
    if not transcript:
        quality.append('Nenhuma fala reconhecida; isso não prova ausência de acontecimentos visuais.')
    return EvidenceBundle(asset_id=asset.asset_id, transcript=transcript, visual_events=[],
                          audio_events=[], quality=quality, provenance=[provenance])
