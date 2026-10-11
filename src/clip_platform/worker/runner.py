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

from clip_platform.shared.contracts import AnalysisRequest, SubtitleSettings
from clip_platform.services.store import Store
from clip_platform.media.audio import extract_audio
from clip_platform.media.export import export_clip
from clip_platform.media.presentation import compose_clip
from clip_platform.media.signals import audio_events, visual_events
from clip_platform.media.affect import affective_cues
from clip_platform.speech.transcribe import transcribe
from clip_platform.subtitles.render import render_subtitled_clip
from clip_platform.selection.baseline import select
from clip_platform.ingestion.download import DownloadRequest, download_video
from clip_platform.worker.progress import ProgressReporter


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
    reporter = ProgressReporter(store, job.job_id, owner)
    if job.kind == 'download':
        reporter.update('consultando plataforma', 0., force=True)
        def download_progress(fraction, stage):
            stage_fraction = (min(1., fraction / .9) if stage == 'baixando' else
                min(1., max(0., (fraction - .9) / .09)) if stage == 'registrando gravação' else None)
            reporter.update(stage, fraction, stage_fraction)
        asset, _ = download_video(DownloadRequest.model_validate(job.payload), directory / 'download',
            download_progress)
        asset = asset.model_copy(update={'asset_id': 'asset-' + job.project_id + '-' + asset.content_hash.split(':')[1]})
        reporter.update('finalizando importação', .99, force=True)
        return asset.model_dump(mode='json')
    if job.kind == 'analysis':
        request = AnalysisRequest.model_validate(job.payload)
        asset = store.get_asset(request.asset_id)
        reporter.update('preparando áudio', 0., force=True)
        audio = extract_audio(asset, directory / 'audio.wav',
            lambda fraction: reporter.update('preparando áudio', .10 * fraction, fraction))
        reporter.update('carregando modelo de fala', .10, force=True)
        if transcriber:
            reporter.update('transcrevendo', .10, 0., force=True)
            evidence = transcriber(asset, audio, str(model_path), device=device)
        else:
            evidence = transcribe(asset, audio, str(model_path), device=device,
                progress_callback=lambda fraction: reporter.update('transcrevendo',
                    .10 + .72 * fraction, fraction))
        reporter.update('observando áudio', .82, 0., force=True)
        for detector, arguments, field in ((audio_events, (asset, audio), 'audio_events'),
                                           (visual_events, (asset,), 'visual_events')):
            reporter.update('observando áudio' if field == 'audio_events' else 'observando imagem',
                .82 if field == 'audio_events' else .88, force=True)
            try:
                events, provenance = detector(*arguments, **({'device': device} if field == 'visual_events' else {}))
                setattr(evidence, field, events)
                if provenance is not None:
                    evidence.provenance.append(provenance)
            except Exception as exc:
                evidence.quality.append(f'{field}: observação indisponível ({type(exc).__name__}).')
            reporter.update('observando áudio' if field == 'audio_events' else 'observando imagem',
                .88 if field == 'audio_events' else .94, 1., force=True)
        reporter.update('avaliando sinais', .94, force=True)
        cues, cue_provenance = affective_cues(asset, evidence.transcript)
        evidence.audio_events.extend(cues)
        evidence.provenance.append(cue_provenance)
        reporter.update('selecionando cortes', .97, force=True)
        result = select(asset, evidence, request).model_dump(mode='json')
        reporter.update('finalizando análise', .99, force=True)
        return result
    revision = store.get_revision(job.payload['revision_id'])
    asset = store.get_asset(revision.asset_id)
    reporter.update('verificando gravação', 0., force=True)
    analysis_id = revision.analysis_id or job.payload.get('analysis_id')
    subtitle_analysis = store.get_analysis(analysis_id) if analysis_id else None
    subtitle_settings = (SubtitleSettings.model_validate(job.payload['subtitle_settings'])
                         if job.payload.get('subtitle_settings') else
                         subtitle_analysis.request.subtitle_settings if subtitle_analysis else None)
    captions_enabled = bool(subtitle_settings and subtitle_settings.enabled)
    def export_progress(fraction, stage):
        bounds = {'verificando gravação': (0., .10), 'codificando corte': (.10, .85),
            'codificando corte na GPU': (.10, .85),
            'validando corte': (.85, .98), 'validando corte existente': (.10, .98)}
        start, end = bounds.get(stage, (.98, 1.))
        overall = fraction * (.70 if captions_enabled else 1.)
        reporter.update(stage, overall, min(1., max(0., (fraction - start) / (end - start))))
    result = export_clip(asset, revision, store.root / 'projects' / job.project_id / 'exports',
        export_progress, device=device)
    store.put_export(result)
    time_map = None
    if subtitle_analysis:
        settings = subtitle_analysis.request.video_settings
        if settings.aspect != 'source' or settings.remove_silence or settings.watermark_text.strip() or settings.header_enabled:
            reporter.update('enquadrando e finalizando vídeo', .68 if captions_enabled else .86, force=True)
            profile = None
            project = store.get_project(job.project_id)
            if project.profile_id:
                try:
                    profile = store.get_profile(project.profile_id)
                except KeyError:
                    pass
            avatar = (store.root / 'profiles' / profile.profile_id / 'avatar.png') if profile else None
            editorial = store.get_clip_editorial(analysis_id, revision.candidate_id) if analysis_id else None
            result, time_map = compose_clip(result, settings,
                store.root / 'projects' / job.project_id / 'exports', device=device,
                header_name=settings.header_name or (profile.brand_name or profile.name if profile else ''),
                header_title=editorial.headline if editorial else '', header_avatar=avatar)
            store.put_export(result)
    if captions_enabled:
        reporter.update('preparando legendas', .70, 0., force=True)
        rendered = render_subtitled_clip(result, subtitle_analysis.evidence,
            revision.boundaries.start_s, revision.boundaries.end_s, subtitle_settings,
            store.root / 'projects' / job.project_id / 'exports',
            progress_callback=lambda fraction: reporter.update(
                'gravando legendas com NVENC' if device == 'cuda' else 'gravando legendas',
                .70 + .28 * fraction, fraction),
            word_overrides=job.payload.get('subtitle_words'), device=device, time_map=time_map)
        result = rendered.export
    reporter.update('finalizando corte', .99, force=True)
    return result.model_dump(mode='json')


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
