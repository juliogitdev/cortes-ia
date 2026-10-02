"""Opt-in real CUDA inference, local models only; never falls back to CPU."""
import argparse
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import threading
import time
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--speech-model', type=Path)
    parser.add_argument('--audio', type=Path)
    parser.add_argument('--vision-model', type=Path)
    parser.add_argument('--image', type=Path)
    parser.add_argument('--output', type=Path, default=Path('runtime/diagnostics/gpu-smoke.json'))
    args = parser.parse_args()
    report = {'observed_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'pending', 'python': platform.python_version(), 'runs': [],
              'versions': {}, 'note': 'No model download and no CPU fallback.'}
    for package in ('torch', 'transformers', 'faster-whisper', 'ctranslate2', 'Pillow'):
        try:
            report['versions'][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report['versions'][package] = None
    exit_code = 2
    stop = threading.Event()
    samples = []
    inference_started = False
    def identity(path):
        files = sorted(path.rglob('*')) if path.is_dir() else [path]
        digest = hashlib.sha256()
        for file in files:
            if file.is_file():
                digest.update(str(file.relative_to(path) if path.is_dir() else file.name).encode())
                with file.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
        return {'path': str(path.resolve()), 'sha256_manifest_and_contents': digest.hexdigest()}
    def memory_summary(values):
        return {'baseline_device_mib': values[0] if values else None,
                'peak_sampled_device_mib': max((max(v) for v in values), default=None)}
    def sample_memory():
        while not stop.is_set():
            try:
                result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                                        capture_output=True, text=True, timeout=3, check=True)
                samples.append([int(v.strip()) for v in result.stdout.splitlines()])
            except (OSError, subprocess.SubprocessError, ValueError):
                pass
            stop.wait(.1)
    try:
        import torch
        report['torch_cuda_build'] = torch.version.cuda
        report['cuda_available'] = torch.cuda.is_available()
        if not torch.cuda.is_available():
            raise RuntimeError('No CUDA device accessible; real GPU inference pending.')
        report['gpu'] = {'name': torch.cuda.get_device_name(0),
                         'capability': torch.cuda.get_device_capability(0),
                         'total_vram_bytes': torch.cuda.get_device_properties(0).total_memory}
        for name in ('speech_model', 'audio', 'vision_model', 'image'):
            path = getattr(args, name)
            if path is None or not path.exists():
                raise RuntimeError(f'Local input required: --{name.replace("_", "-")}')
            report[name] = identity(path)
        driver = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'],
                                capture_output=True, text=True, check=True, timeout=5)
        report['nvidia_driver'] = driver.stdout.strip()
        # Exclusive reservation spans both backends. No overlapping models.
        lock = Path(__file__).resolve().parents[1] / 'runtime' / 'gpu-reservation.lock'
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open('x', encoding='utf-8') as reservation:
            reservation.write('gpu_smoke: exclusive GPU reservation\n')
        try:
            thread = threading.Thread(target=sample_memory, daemon=True)
            thread.start()
            from faster_whisper import WhisperModel
            inference_started = True
            start = time.perf_counter()
            model = WhisperModel(str(args.speech_model.resolve()), device='cuda', compute_type='float16', local_files_only=True)
            segments, info = model.transcribe(str(args.audio.resolve()), language='pt', beam_size=1)
            segments = list(segments)  # Lazy generator must be consumed to execute inference.
            report['runs'].append({'kind': 'speech', 'model': str(args.speech_model.resolve()),
                                   'backend': 'CTranslate2 CUDA float16', 'load_and_inference_s': time.perf_counter()-start,
                                   'segment_count': len(segments), 'detected_language': info.language,
                                   'device_memory_samples_mib': samples.copy()})
            report['runs'][-1].update(memory_summary(samples.copy()))
            del model, segments
            gc.collect()
            torch.cuda.empty_cache()
            samples.clear()
            from transformers import AutoProcessor, AutoModelForImageTextToText
            from PIL import Image
            start = time.perf_counter()
            torch.cuda.reset_peak_memory_stats()
            processor = AutoProcessor.from_pretrained(str(args.vision_model.resolve()), local_files_only=True)
            model = AutoModelForImageTextToText.from_pretrained(str(args.vision_model.resolve()),
                        local_files_only=True, torch_dtype=torch.float16).to('cuda').eval()
            with Image.open(args.image) as image:
                image.thumbnail((512, 512))
                messages = [{'role': 'user', 'content': [{'type': 'image', 'image': image.convert('RGB')},
                            {'type': 'text', 'text': 'Descreva somente o que é visível nesta imagem.'}]}]
                inputs = processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                        return_dict=True, return_tensors='pt').to('cuda')
                with torch.inference_mode():
                    output = model.generate(**inputs, max_new_tokens=32, do_sample=False)
                torch.cuda.synchronize()
                generated_tokens = output.shape[-1]-inputs['input_ids'].shape[-1]
            report['runs'].append({'kind': 'vision', 'model': str(args.vision_model.resolve()),
                                   'backend': 'PyTorch CUDA float16', 'load_and_inference_s': time.perf_counter()-start,
                                   'generated_tokens': generated_tokens,
                                   'peak_torch_allocated_bytes': torch.cuda.max_memory_allocated(),
                                   'peak_torch_reserved_bytes': torch.cuda.max_memory_reserved(),
                                   'device_memory_samples_mib': samples.copy()})
            report['runs'][-1].update(memory_summary(samples.copy()))
            memory_complete = all(run['peak_sampled_device_mib'] is not None for run in report['runs'])
            report['status'] = 'passed' if memory_complete else 'incomplete_measurement'
            exit_code = 0 if memory_complete else 2
        finally:
            stop.set()
            if 'thread' in locals():
                thread.join(timeout=4)
            lock.unlink(missing_ok=True)
    except Exception as exc:
        report['reason'] = f'{type(exc).__name__}: {exc}'
        report['status'] = 'failed' if inference_started else 'pending'
    finally:
        report['memory_note'] = 'nvidia-smi samples are total device VRAM, include other processes, may miss brief peaks; torch peaks exclude CTranslate2.'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"{report['status']}: {args.output}")
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
