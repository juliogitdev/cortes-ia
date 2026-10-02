"""Worker separado, um job com lease por vez, backend explicitamente escolhido."""
import argparse
from contextlib import contextmanager
import multiprocessing
import os
import signal
import subprocess
from pathlib import Path
import time
import uuid

from clip_platform.shared.contracts import AnalysisRequest
from clip_platform.services.store import Store
from clip_platform.media.audio import extract_audio
from clip_platform.media.export import export_clip
from clip_platform.speech.transcribe import transcribe
from clip_platform.selection.baseline import select


@contextmanager
def resource_lock(root):
    """Reserva de processo: inclusive um filho órfão mantém exclusão física."""
    path = root / 'processing.lock'
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(.1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def execute_job(root, job_id, owner, model_path, device, transcriber, pipe):
    if os.name != 'nt':
        os.setsid()
    store = Store(Path(root))
    try:
        with resource_lock(store.root):
            job = store.get_job(job_id)
            result = process_job(store, job, owner, model_path, device, transcriber)
        pipe.send((True, result))
    except Exception as exc:
        pipe.send((False, str(exc)))
    finally:
        pipe.close()


def process_job(store, job, owner, model_path, device, transcriber):
    directory = store.root / 'projects' / job.project_id / 'jobs' / job.job_id
    directory.mkdir(parents=True, exist_ok=True)
    if job.kind == 'analysis':
        request = AnalysisRequest.model_validate(job.payload)
        asset = store.get_asset(request.asset_id)
        store.set_stage(job.job_id, owner, 'preparando')
        audio = extract_audio(asset, directory / 'audio.wav')
        store.set_stage(job.job_id, owner, 'transcrevendo')
        evidence = (transcriber or transcribe)(asset, audio, str(model_path), device=device)
        store.set_stage(job.job_id, owner, 'selecionando')
        return select(asset, evidence, request).model_dump(mode='json')
    revision = store.get_revision(job.payload['revision_id'])
    asset = store.get_asset(revision.asset_id)
    store.set_stage(job.job_id, owner, 'exportando')
    return export_clip(asset, revision, store.root / 'projects' / job.project_id / 'exports').model_dump(mode='json')


def run_once(store, model_path, device='cpu', transcriber=None, lease_s=60):
    owner = uuid.uuid4().hex
    job = store.claim(owner, lease_s=lease_s)
    if job is None:
        return None
    context = multiprocessing.get_context('spawn')
    receiving, sending = context.Pipe(duplex=False)
    process = context.Process(target=execute_job, args=(str(store.root), job.job_id, owner,
                              str(model_path), device, transcriber, sending))
    message = None
    next_heartbeat = time.monotonic()
    try:
        process.start()
        sending.close()
        while True:
            if store.get_job(job.job_id).status != 'running':
                raise ValueError('Tarefa cancelada ou retomada por outro executor.')
            if time.monotonic() >= next_heartbeat:
                store.heartbeat(job.job_id, owner, lease_s=lease_s)
                next_heartbeat = time.monotonic() + max(.1, lease_s / 3)
            if receiving.poll(.1):
                message = receiving.recv()
                break
            if not process.is_alive():
                raise RuntimeError('Processo de execução encerrou sem entregar resultado.')
        process.join(timeout=5)
        if not message[0]:
            raise RuntimeError(message[1])
        store.finish(job.job_id, owner, message[1])
    except Exception as exc:
        try:
            store.fail(job.job_id, owner, str(exc))
        except (ValueError, KeyError):
            pass  # Cancelamento ou novo owner venceu; preservar esse estado.
    finally:
        if process.pid is not None:
            if process.is_alive():
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                else:
                    os.killpg(process.pid, signal.SIGTERM)
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
        receiving.close()
        sending.close()
        try:
            store.release(job.job_id, owner)
        except (ValueError, KeyError):
            pass
    return store.get_job(job.job_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage', default=os.environ.get('CLIP_STORAGE', 'storage'))
    parser.add_argument('--model', default=os.environ.get('CLIP_SPEECH_MODEL', 'models/whisper-tiny'))
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    store = Store(Path(args.storage))
    print(f'Worker local: device={args.device}, modelo={args.model}', flush=True)
    try:
        while True:
            job = run_once(store, args.model, args.device)
            if job:
                print(f'{job.job_id}: {job.status}', flush=True)
            if args.once:
                break
            if job is None:
                time.sleep(1)
    except KeyboardInterrupt:
        print('Worker interrompido; tarefas serão recuperadas após expiração do lease.', flush=True)


if __name__ == '__main__':
    main()
