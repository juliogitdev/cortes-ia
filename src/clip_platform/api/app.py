"""API local: mídia autorizada, fila persistida e resultados validados."""
import os
from pathlib import Path
import shutil
import uuid
import time
import secrets
import hmac
import io
import re
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import FastAPI, Header, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal

from clip_platform.shared.contracts import (AnalysisRequest, AnalysisResult, ClipRevision, Interval, SubtitleWord,
    SubtitleSettings,
    MediaAsset, Publication, PublicationRecord, PublicationCollectionRun, MetricSnapshot,
    TikTokPublishAttempt)
from clip_platform.shared.jobs import (CandidateFeedback, ClipEditorial, EditorialProfile,
    Project, Job, Export, ClipMediaVariants)
from clip_platform.services.store import Store
from clip_platform.ingestion.local import ingest_file
from clip_platform.ingestion.download import DownloadRequest, identify_provider
from clip_platform.media.tools import AV_DEMUXERS, run_tool
from clip_platform.speech.transcribe import _repetition_loop
from clip_platform.learning.tiktok import connection_status, query_metrics, query_video_details, TikTokCollectionError, VIDEO_URL
from clip_platform.learning.tiktok_oauth import (app_status, save_app, accounts, account,
    authorization_url, exchange_code, disconnect, TikTokOAuthError)
from clip_platform.learning.tiktok_posting import (list_videos, creator_info, direct_post,
    fetch_post_status, TikTokPostingError)


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=200)
    profile_id: str | None = None

class ProfileInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=200)
    platforms: list[Literal['tiktok', 'instagram']] = Field(min_length=1, max_length=2)
    account_open_id: str | None = None


class ProfileBrandingInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tiktok_url: str = Field(default='', max_length=250)
    brand_name: str = Field(default='', max_length=60)

class ProjectProfileInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    profile_id: str | None = None


class RevisionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    analysis_id: str
    start_s: float = Field(ge=0, allow_inf_nan=False)
    end_s: float = Field(gt=0, allow_inf_nan=False)
    editor_changes: list[str] = Field(default_factory=list)
    parent_revision_id: str | None = None


class SubtitleCorrectionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    words: list[SubtitleWord] = Field(min_length=1, max_length=500)
    settings: SubtitleSettings | None = None


class MediaSelectionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    export_id: str = Field(min_length=1)


class CandidateFeedbackInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rating: Literal['useful', 'not_useful']
    note: str = Field(default='', max_length=1000)


class PublicationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision_id: str
    platform: str = Field(min_length=1, max_length=80)
    account: str = Field(min_length=1, max_length=100)
    account_open_id: str | None = None
    posted_at: datetime | None = None
    publication_url: str
    external_video_id: str | None = Field(default=None, pattern=r'^\d{10,25}$')


class ManualMetricInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    metric_name: Literal['views', 'likes', 'comments', 'shares']
    value: int = Field(ge=0)
    reviewer: str = Field(min_length=1, max_length=100)


class CollectionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(min_length=1, max_length=120)
    trigger: Literal['explicit_user_action', 'authorized_session_start'] = 'authorized_session_start'
    profile_id: str | None = None


class TikTokAppInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    client_key: str = Field(min_length=3, max_length=150)
    client_secret: str = Field(default='', max_length=500)
    redirect_uri: str = Field(min_length=20, max_length=511)
    request_publish_scope: bool = False


class PublicationAccountInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    account_open_id: str = Field(min_length=1, max_length=200)


class ProjectAccountInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    account_open_id: str | None = Field(default=None, max_length=200)


class TikTokVideoListInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    cursor: int | None = Field(default=None, ge=0)


class TikTokPostInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(min_length=1, max_length=120)
    revision_id: str = Field(min_length=1)
    export_id: str = Field(min_length=1)
    account_open_id: str = Field(min_length=1, max_length=200)
    caption: str = Field(default='', max_length=2200)
    privacy_level: str = Field(min_length=1)
    disable_comment: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False
    consent: bool


class TikTokScheduleItem(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision_id: str = Field(min_length=1)
    export_id: str = Field(min_length=1)
    caption: str = Field(default='', max_length=2200)
    privacy_level: str = Field(min_length=1)
    scheduled_at: datetime | None = None
    disable_comment: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False


class TikTokScheduleInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    batch_id: str = Field(min_length=1, max_length=120)
    account_open_id: str = Field(min_length=1, max_length=200)
    mode: Literal['individual', 'interval']
    items: list[TikTokScheduleItem] = Field(min_length=1, max_length=100)
    start_at: datetime | None = None
    interval_hours: float | None = Field(default=None, gt=0, le=168)
    consent: bool


def create_app(storage_root=None):
    root = Path(storage_root or os.environ.get('CLIP_STORAGE', 'storage')).resolve()
    store = Store(root)
    app = FastAPI(title='Cortes IA — local', version='2.0.0')
    app.state.store = store

    @app.exception_handler(KeyError)
    async def missing(_, exc):
        return JSONResponse(status_code=404, content={'detail': 'Registro não encontrado.'})

    @app.exception_handler(ValueError)
    async def invalid(_, exc):
        return JSONResponse(status_code=422, content={'detail': str(exc)})

    @app.exception_handler(TikTokOAuthError)
    async def tiktok_invalid(_, exc):
        return JSONResponse(status_code=422, content={'detail': exc.code})

    @app.exception_handler(TikTokPostingError)
    async def tiktok_posting_invalid(_, exc):
        return JSONResponse(status_code=422, content={'detail': exc.code})

    def authorized_file(raw):
        path = Path(raw).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(404, 'Arquivo indisponível na área autorizada.')
        return path

    @app.get('/health')
    def health():
        return {'status': 'ok', 'mode': 'local', 'baseline': 'observable_signals_v1',
                'signals': ['speech', 'frame_change', 'audio_energy']}

    @app.post('/projects', response_model=Project, status_code=201)
    def create_project(data: ProjectInput):
        return store.create_project(data.name.strip() or 'Projeto', profile_id=data.profile_id)

    @app.get('/profiles', response_model=list[EditorialProfile])
    def profiles():
        return store.list_profiles()

    @app.post('/profiles', response_model=EditorialProfile, status_code=201)
    def create_profile(data: ProfileInput):
        if data.account_open_id and ('tiktok' not in data.platforms or not account(root, data.account_open_id)):
            raise HTTPException(422, 'Selecione uma conta TikTok vinculada.')
        return store.create_profile(data.name, data.platforms, data.account_open_id)

    @app.put('/profiles/{profile_id}', response_model=EditorialProfile)
    def update_profile(profile_id: str, data: ProfileInput):
        if data.account_open_id and ('tiktok' not in data.platforms or not account(root, data.account_open_id)):
            raise HTTPException(422, 'Selecione uma conta TikTok vinculada.')
        saved = store.update_profile(profile_id, data.name, data.platforms, data.account_open_id)
        return _sync_authorized_avatar(saved)

    def _sync_authorized_avatar(profile: EditorialProfile) -> EditorialProfile:
        if not profile.account_open_id or profile.avatar_version:
            return profile
        linked = account(root, profile.account_open_id)
        avatar_url = linked.get('avatar_url', '') if linked else ''
        parsed_avatar = urlparse(avatar_url)
        host = parsed_avatar.hostname or ''
        if parsed_avatar.scheme != 'https' or parsed_avatar.username or parsed_avatar.password or not any(
                host == domain or host.endswith('.' + domain)
                for domain in ('tiktokcdn.com', 'tiktokcdn-us.com')):
            return profile
        try:
            import httpx
            from PIL import Image
            response = httpx.get(avatar_url, timeout=8, follow_redirects=False)
            response.raise_for_status()
            if len(response.content) > 3_000_000:
                return profile
            image = Image.open(io.BytesIO(response.content))
            image.verify()
            image = Image.open(io.BytesIO(response.content)).convert('RGB')
            if image.width > 4096 or image.height > 4096:
                return profile
            image.thumbnail((512, 512))
            folder = root / 'profiles' / profile.profile_id
            folder.mkdir(parents=True, exist_ok=True)
            temporary = folder / 'avatar.tmp.png'
            image.save(temporary, format='PNG')
            temporary.replace(folder / 'avatar.png')
            return store.bump_profile_avatar(profile.profile_id)
        except (httpx.HTTPError, OSError, ValueError):
            return profile

    @app.put('/profiles/{profile_id}/branding', response_model=EditorialProfile)
    def save_profile_branding(profile_id: str, data: ProfileBrandingInput):
        raw_url = data.tiktok_url.strip()
        parsed = urlparse(raw_url) if raw_url else None
        match = re.fullmatch(r'/@([A-Za-z0-9._]{2,30})', parsed.path.rstrip('/')) if parsed else None
        if raw_url and (not parsed or parsed.scheme != 'https' or parsed.hostname not in
                        {'tiktok.com', 'www.tiktok.com'} or parsed.username or parsed.password or not match):
            raise HTTPException(422, 'Use um link de perfil no formato https://www.tiktok.com/@usuario.')
        url = 'https://www.tiktok.com/@' + match.group(1) if match else ''
        name = data.brand_name.strip()
        if not name and match:
            name = '@' + match.group(1)
            try:
                import httpx
                response = httpx.get('https://www.tiktok.com/oembed', params={'url': url}, timeout=5)
                response.raise_for_status()
                author = response.json().get('author_name', '').strip()
                if author and len(author) <= 60:
                    name = author
            except (httpx.HTTPError, ValueError, TypeError, AttributeError):
                pass
        return _sync_authorized_avatar(store.save_profile_branding(profile_id, url, name))

    @app.put('/profiles/{profile_id}/avatar', response_model=EditorialProfile)
    async def upload_profile_avatar(profile_id: str, request: Request):
        store.get_profile(profile_id)
        if int(request.headers.get('content-length', '0')) > 3_000_000:
            raise HTTPException(413, 'Imagem deve ter no máximo 3 MB.')
        raw = await request.body()
        if len(raw) > 3_000_000:
            raise HTTPException(413, 'Imagem deve ter no máximo 3 MB.')
        try:
            from PIL import Image
            image = Image.open(io.BytesIO(raw))
            image.verify()
            image = Image.open(io.BytesIO(raw)).convert('RGB')
            if image.width > 4096 or image.height > 4096:
                raise ValueError('Imagem grande demais.')
            image.thumbnail((512, 512))
        except (ValueError, OSError) as exc:
            raise HTTPException(422, 'Envie uma imagem JPG, PNG ou WebP válida.') from exc
        folder = root / 'profiles' / profile_id
        folder.mkdir(parents=True, exist_ok=True)
        temporary = folder / 'avatar.tmp.png'
        image.save(temporary, format='PNG')
        temporary.replace(folder / 'avatar.png')
        return store.bump_profile_avatar(profile_id)

    @app.get('/profiles/{profile_id}/avatar')
    def profile_avatar(profile_id: str):
        store.get_profile(profile_id)
        avatar = root / 'profiles' / profile_id / 'avatar.png'
        if not avatar.is_file():
            raise HTTPException(404, 'Foto não cadastrada.')
        return FileResponse(avatar, media_type='image/png')

    @app.delete('/profiles/{profile_id}')
    def delete_profile(profile_id: str):
        store.delete_profile(profile_id)
        return {'status': 'deleted', 'scope': 'editorial_profile_only',
                'lives_untouched': True, 'social_publications_untouched': True}

    @app.patch('/projects/{project_id}/profile', response_model=Project)
    def assign_project_profile(project_id: str, data: ProjectProfileInput):
        return store.assign_project_profile(project_id, data.profile_id)

    @app.get('/projects', response_model=list[Project])
    def projects():
        return store.list_projects()

    @app.patch('/projects/{project_id}', response_model=Project)
    def rename_project(project_id: str, data: ProjectInput):
        return store.rename_project(project_id, data.name)

    @app.patch('/projects/{project_id}/tiktok-account', response_model=Project)
    def assign_project_account(project_id: str, data: ProjectAccountInput):
        if data.account_open_id and not account(root, data.account_open_id):
            raise HTTPException(422, 'Conta TikTok não vinculada.')
        return store.assign_project_account(project_id, data.account_open_id)

    @app.delete('/projects/{project_id}')
    def delete_project(project_id: str):
        # Archived projects remain addressable here so failed local cleanup can be retried.
        project = store.project_for_cleanup(project_id)
        projects_root = (root / 'projects').resolve()
        directory = projects_root / project.project_id
        if (projects_root.parent != root or directory.is_symlink() or
                directory.resolve().parent != projects_root):
            raise HTTPException(422, 'Caminho da live inválido; arquivos preservados.')
        if directory.exists() and (not directory.is_dir() or
                any(path.is_symlink() for path in directory.rglob('*'))):
            raise HTTPException(422, 'A pasta contém links ou arquivos inesperados; exclusão local bloqueada.')
        store.archive_project(project_id)
        try:
            if directory.exists():
                shutil.rmtree(directory)
        except OSError as exc:
            raise HTTPException(500, 'Projeto ocultado, mas a limpeza local falhou; repita a exclusão.') from exc
        return {'status': 'deleted', 'project_id': project_id,
                'scope': 'local_only', 'tiktok_publications_untouched': True}

    @app.post('/projects/{project_id}/upload', response_model=MediaAsset, status_code=201)
    def upload(project_id: str, file: UploadFile = File(...)):
        project = store.get_project(project_id)
        incoming = root / 'incoming'
        incoming.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename or '').suffix.lower()
        if suffix not in {'.mp4', '.mkv', '.mov', '.webm', '.avi', '.m4v', '.ts', '.mpeg', '.mpg'}:
            raise HTTPException(422, 'Envie um contêiner de vídeo local suportado.')
        temporary = incoming / (uuid.uuid4().hex + suffix)
        limit = int(os.environ.get('CLIP_MAX_UPLOAD_BYTES', str(5 * 1024**3)))
        total = 0
        try:
            with temporary.open('xb') as output:
                while chunk := file.file.read(1024 * 1024):
                    total += len(chunk)
                    if total > limit:
                        raise HTTPException(413, 'Arquivo excede o limite local de upload.')
                    if shutil.disk_usage(root).free < len(chunk) + 128 * 1024**2:
                        raise HTTPException(507, 'Espaço livre insuficiente para continuar o upload.')
                    output.write(chunk)
            if not total:
                raise HTTPException(422, 'Arquivo vazio.')
            asset = ingest_file(temporary, root / 'projects' / project_id / 'assets')
            asset = asset.model_copy(update={'asset_id': 'asset-' + project_id + '-' + asset.content_hash.split(':')[1],
                                            'source_uri': 'upload://' + asset.content_hash.split(':')[1]})
            if project.asset_id and project.asset_id != asset.asset_id:
                raise HTTPException(409, 'Crie outro projeto para uma nova gravação; este já preserva uma mídia.')
            store.put_asset(project_id, asset)
            return asset
        except (RuntimeError, FileNotFoundError) as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            temporary.unlink(missing_ok=True)
            file.file.close()

    @app.get('/assets/{asset_id}/media')
    def media(asset_id: str):
        return FileResponse(authorized_file(store.get_asset(asset_id).local_path))

    @app.get('/assets/{asset_id}/thumbnail')
    def source_thumbnail(asset_id: str):
        asset = store.get_asset(asset_id)
        video = authorized_file(asset.local_path)
        thumbnail = video.with_name(video.stem + '.source-preview.jpg')
        if thumbnail.is_symlink() or not thumbnail.resolve().is_relative_to(root):
            raise HTTPException(422, 'Caminho da capa inválido.')
        if not thumbnail.is_file():
            temporary = video.with_name('.source-preview-' + uuid.uuid4().hex + '.jpg')
            try:
                run_tool('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                    '-ss', str(min(3., asset.duration_s / 3)), '-protocol_whitelist', 'file,pipe',
                    '-format_whitelist', AV_DEMUXERS, '-i', str(video), '-frames:v', '1',
                    '-vf', 'scale=640:-2', '-q:v', '4', str(temporary)], timeout=60)
                if not temporary.is_file() or temporary.stat().st_size == 0:
                    raise HTTPException(500, 'Não foi possível gerar a capa da live.')
                os.replace(temporary, thumbnail)
            finally:
                temporary.unlink(missing_ok=True)
        return FileResponse(thumbnail, media_type='image/jpeg')

    @app.get('/analyses/{analysis_id}/candidates/{candidate_id}/editorial', response_model=ClipEditorial)
    def clip_editorial(analysis_id: str, candidate_id: str):
        return store.get_clip_editorial(analysis_id, candidate_id)

    @app.put('/analyses/{analysis_id}/candidates/{candidate_id}/editorial', response_model=ClipEditorial)
    def save_clip_editorial(analysis_id: str, candidate_id: str, data: ClipEditorial):
        if data.analysis_id != analysis_id or data.candidate_id != candidate_id:
            raise HTTPException(422, 'Identificadores do corte divergentes.')
        return store.save_clip_editorial(data)

    @app.post('/projects/{project_id}/downloads', response_model=Job, status_code=202)
    def download_from_link(project_id: str, data: DownloadRequest, idempotency_key: str = Header(min_length=1)):
        project = store.get_project(project_id)
        if project.asset_id:
            raise HTTPException(409, 'Este projeto já contém uma gravação; crie outro projeto.')
        identify_provider(data.url)
        data.settings.format_selector()
        return store.enqueue(project_id, 'download', idempotency_key, data.model_dump(mode='json'))

    @app.post('/projects/{project_id}/analyses', response_model=Job, status_code=202)
    def analyze(project_id: str, data: AnalysisRequest, idempotency_key: str = Header(min_length=1)):
        project = store.get_project(project_id)
        if project.asset_id != data.asset_id:
            raise HTTPException(422, 'A gravação não pertence ao projeto atual.')
        return store.enqueue(project_id, 'analysis', idempotency_key, data.model_dump(mode='json'))

    @app.get('/jobs/{job_id}', response_model=Job)
    def job(job_id: str):
        return store.get_job(job_id)

    @app.get('/projects/{project_id}/jobs', response_model=list[Job])
    def project_jobs(project_id: str):
        return store.list_jobs(project_id)

    @app.post('/jobs/{job_id}/cancel', response_model=Job)
    def cancel(job_id: str):
        store.cancel(job_id)
        return store.get_job(job_id)

    @app.get('/analyses/{analysis_id}/candidates', response_model=AnalysisResult)
    def candidates(analysis_id: str):
        return store.get_analysis(analysis_id)

    def subtitle_context(analysis_id: str, candidate_id: str):
        analysis = store.get_analysis(analysis_id)
        candidate = next((item for item in analysis.candidates
                          if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise HTTPException(404, 'Corte não encontrado nesta análise.')
        if candidate_id in store.list_discarded(analysis_id):
            raise HTTPException(404, 'Corte excluído desta análise.')
        job = store.get_job(analysis_id)
        exports = [item for item in store.list_jobs(job.project_id)
                   if item.kind == 'export' and item.payload.get('analysis_id') == analysis_id
                   and item.payload.get('candidate_id') == candidate_id
                   and item.payload.get('auto') is True]
        if not exports:
            raise HTTPException(409, 'Exportação automática ainda não preparada.')
        return analysis, candidate, job, exports

    @app.get('/analyses/{analysis_id}/candidates/{candidate_id}/subtitles')
    def subtitle_review(analysis_id: str, candidate_id: str):
        analysis, candidate, _, exports = subtitle_context(analysis_id, candidate_id)
        edited = next((item for item in exports if item.payload.get('subtitle_words')), None)
        words = []
        suppressed_ranges = []
        for segment in analysis.evidence.transcript:
            if segment.end_s <= candidate.start_s or segment.start_s >= candidate.end_s:
                continue
            if _repetition_loop(segment.observation):
                suppressed_ranges.append({'start_s': max(segment.start_s, candidate.start_s),
                                          'end_s': min(segment.end_s, candidate.end_s)})
                continue
            for word in segment.provenance.settings.get('words', []):
                if not isinstance(word, dict):
                    continue
                try:
                    start, end = float(word['start_s']), float(word['end_s'])
                    label = str(word['text']).strip()
                except (KeyError, ValueError, TypeError):
                    continue
                start, end = max(start, candidate.start_s), min(end, candidate.end_s)
                if label and start < end:
                    words.append({'start_s': start, 'end_s': end, 'text': label})
        latest_settings = next((item.payload.get('subtitle_settings') for item in exports
                                if item.payload.get('subtitle_settings')), None)
        effective_settings = (SubtitleSettings.model_validate(latest_settings) if latest_settings
                              else analysis.request.subtitle_settings)
        return {'revision_id': exports[-1].payload['revision_id'],
                'enabled': effective_settings.enabled,
                'settings': effective_settings.model_dump(mode='json'),
                'words': edited.payload['subtitle_words'] if edited else words,
                'suppressed_ranges': suppressed_ranges,
                'version': edited.job_id if edited else None}

    @app.put('/analyses/{analysis_id}/candidates/{candidate_id}/subtitles',
             response_model=Job, status_code=202)
    def correct_subtitles(analysis_id: str, candidate_id: str, data: SubtitleCorrectionInput):
        analysis, candidate, job, exports = subtitle_context(analysis_id, candidate_id)
        prior_settings = next((item.payload.get('subtitle_settings') for item in exports
                               if item.payload.get('subtitle_settings')), None)
        if data.settings is not None:
            effective_settings = data.settings
        elif prior_settings:
            effective_settings = SubtitleSettings.model_validate(prior_settings)
        else:
            effective_settings = analysis.request.subtitle_settings
        if not effective_settings.enabled:
            raise HTTPException(409, 'Legendas desativadas nesta análise.')
        previous_end = candidate.start_s
        for word in data.words:
            if (word.start_s < candidate.start_s or word.end_s > candidate.end_s or
                    word.start_s < previous_end or not word.text.strip() or
                    word.end_s - word.start_s < .025):
                raise HTTPException(422, 'Palavras devem estar em ordem e dentro do corte, com horários válidos.')
            previous_end = word.end_s
        payload = {'revision_id': exports[-1].payload['revision_id'],
                   'candidate_id': candidate_id, 'analysis_id': analysis_id,
                   'auto': True,
                   'subtitle_words': [word.model_dump(exclude={'schema_version'}) for word in data.words],
                   'subtitle_settings': effective_settings.model_dump(mode='json')}
        return store.enqueue(job.project_id, 'export', 'subtitle-correction-' + uuid.uuid4().hex, payload)

    @app.post('/analyses/{analysis_id}/exports', response_model=list[Job])
    def prepare_candidate_exports(analysis_id: str):
        return store.ensure_auto_exports(analysis_id)

    @app.get('/projects/{project_id}/media-versions', response_model=list[ClipMediaVariants])
    def project_media_versions(project_id: str):
        store.get_project(project_id)
        return store.project_media_variants(project_id)

    @app.get('/analyses/{analysis_id}/candidates/{candidate_id}/media-versions',
             response_model=ClipMediaVariants)
    def clip_media_versions(analysis_id: str, candidate_id: str):
        return store.media_variants(analysis_id, candidate_id)

    @app.put('/analyses/{analysis_id}/candidates/{candidate_id}/media-selection',
             response_model=ClipMediaVariants)
    def select_clip_media(analysis_id: str, candidate_id: str, data: MediaSelectionInput):
        return store.select_media_variant(analysis_id, candidate_id, data.export_id)

    @app.delete('/analyses/{analysis_id}/candidates/{candidate_id}/media-versions/{export_id}',
                response_model=ClipMediaVariants)
    def delete_clip_media_version(analysis_id: str, candidate_id: str, export_id: str):
        exported = store.get_export(export_id)
        path = Path(exported.local_path).resolve()
        if not path.is_relative_to(root) or path.parent.name != 'exports' or path.suffix != '.mp4':
            raise HTTPException(422, 'Caminho da versão inválido; arquivo preservado para inspeção.')
        store.hide_media_variant(analysis_id, candidate_id, export_id)
        for file in (path, path.with_suffix('.export.json'), path.with_suffix('.preview.jpg')):
            file.unlink(missing_ok=True)
        return store.media_variants(analysis_id, candidate_id)

    @app.get('/analyses/{analysis_id}/discarded', response_model=list[str])
    def discarded(analysis_id: str):
        return store.list_discarded(analysis_id)

    @app.delete('/analyses/{analysis_id}/candidates/{candidate_id}')
    def discard_candidate(analysis_id: str, candidate_id: str):
        outputs = store.discard_candidate(analysis_id, candidate_id)
        revision_ids = {item.revision_id for item in outputs}
        if outputs:
            export_dir = Path(outputs[0].local_path).resolve().parent
            if export_dir.is_relative_to(root) and export_dir.name == 'exports':
                for sidecar in export_dir.glob('*.export.json'):
                    try:
                        record = Export.model_validate_json(sidecar.read_text(encoding='utf-8'))
                    except (ValueError, OSError):
                        continue
                    if record.revision_id in revision_ids and record.export_id not in {
                            item.export_id for item in outputs}:
                        outputs.append(record)
        for exported in outputs:
            path = Path(exported.local_path).resolve()
            if not path.is_relative_to(root) or path.parent.name != 'exports' or path.suffix != '.mp4':
                raise HTTPException(422, 'Caminho do corte inválido; arquivo preservado para inspeção.')
            sidecar = path.with_suffix('.export.json').resolve()
            if not sidecar.is_relative_to(root):
                raise HTTPException(422, 'Manifesto do corte inválido; arquivo preservado para inspeção.')
            path.unlink(missing_ok=True)
            sidecar.unlink(missing_ok=True)
            path.with_suffix('.preview.jpg').unlink(missing_ok=True)
        return {'status': 'discarded', 'removed_exports': len(outputs)}

    @app.post('/analyses/{analysis_id}/candidates/{candidate_id}/feedback',
              response_model=CandidateFeedback, status_code=201)
    def add_candidate_feedback(analysis_id: str, candidate_id: str, data: CandidateFeedbackInput):
        return store.add_feedback(analysis_id, candidate_id, data.rating, data.note)

    @app.get('/analyses/{analysis_id}/candidates/{candidate_id}/feedback',
             response_model=list[CandidateFeedback])
    def candidate_feedback(analysis_id: str, candidate_id: str):
        return store.list_feedback(analysis_id, candidate_id)

    @app.post('/candidates/{candidate_id}/revisions', response_model=ClipRevision, status_code=201)
    def revise(candidate_id: str, data: RevisionInput):
        result = store.get_analysis(data.analysis_id)
        candidate = next((item for item in result.candidates if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise HTTPException(404, 'Candidato não encontrado nesta análise.')
        if candidate_id in store.list_discarded(data.analysis_id):
            raise HTTPException(409, 'Corte excluído desta análise.')
        boundaries = Interval(start_s=data.start_s, end_s=data.end_s)
        if boundaries.end_s > result.asset.duration_s:
            raise HTTPException(422, 'Intervalo excede a gravação.')
        if data.parent_revision_id:
            parent = store.get_revision(data.parent_revision_id)
            if parent.candidate_id != candidate_id or parent.asset_id != result.asset.asset_id:
                raise HTTPException(422, 'Revisão anterior pertence a outro corte.')
        revision = ClipRevision(revision_id=uuid.uuid4().hex, candidate_id=candidate_id,
            asset_id=result.asset.asset_id, analysis_id=data.analysis_id,
            boundaries=boundaries, editor_changes=data.editor_changes,
            parent_revision_id=data.parent_revision_id)
        store.put_revision(revision)
        return revision

    @app.post('/revisions/{revision_id}/exports', response_model=Job, status_code=202)
    def export(revision_id: str, idempotency_key: str = Header(min_length=1)):
        revision = store.get_revision(revision_id)
        # A revisão identifica a mídia; resolver projeto no catálogo, nunca aceitar caminho do cliente.
        project = next((p for p in store.list_projects() if p.asset_id == revision.asset_id), None)
        if project is None:
            raise HTTPException(422, 'Projeto da revisão indisponível.')
        return store.enqueue(project.project_id, 'export', idempotency_key, {'revision_id': revision_id})

    @app.get('/exports/{export_id}/download')
    def download(export_id: str):
        exported = store.get_export(export_id)
        return FileResponse(authorized_file(exported.local_path), media_type='video/mp4',
                            filename=f'corte-{exported.export_id}.mp4')

    @app.get('/exports/{export_id}/media')
    def exported_media(export_id: str):
        exported = store.get_export(export_id)
        return FileResponse(authorized_file(exported.local_path), media_type='video/mp4')

    @app.get('/exports/{export_id}/thumbnail')
    def exported_thumbnail(export_id: str):
        exported = store.get_export(export_id)
        video = authorized_file(exported.local_path)
        if video.parent.name != 'exports' or video.suffix != '.mp4':
            raise HTTPException(422, 'Caminho do corte inválido.')
        thumbnail = video.with_suffix('.preview.jpg')
        if thumbnail.is_symlink() or not thumbnail.resolve().is_relative_to(root):
            raise HTTPException(422, 'Caminho da capa inválido.')
        if not thumbnail.is_file():
            temporary = video.with_name('.preview-' + uuid.uuid4().hex + '.jpg')
            try:
                run_tool('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-nostdin', '-y',
                                    '-ss', str(min(1., exported.duration_s / 3)),
                                    '-protocol_whitelist', 'file,pipe', '-format_whitelist', AV_DEMUXERS,
                                    '-i', str(video), '-frames:v', '1', '-vf', 'scale=640:-2',
                                    '-q:v', '4', str(temporary)], timeout=60)
                if not temporary.is_file() or temporary.stat().st_size == 0:
                    raise HTTPException(500, 'Não foi possível gerar a capa do corte.')
                os.replace(temporary, thumbnail)
            finally:
                temporary.unlink(missing_ok=True)
        return FileResponse(thumbnail, media_type='image/jpeg')

    @app.post('/publications', response_model=Publication, status_code=201)
    def create_publication(data: PublicationInput, background_tasks: BackgroundTasks):
        if data.posted_at and (data.posted_at.tzinfo is None or data.posted_at.utcoffset() is None):
            raise HTTPException(422, 'Data da publicação precisa de fuso horário.')
        if not data.posted_at and data.platform.lower() != 'tiktok':
            raise HTTPException(422, 'Informe a data da publicação.')
        if data.platform.lower() == 'tiktok':
            project = store.project_for_revision(data.revision_id)
            if not project.account_open_id or project.account_open_id != data.account_open_id:
                raise HTTPException(422, 'Adicione esta conta TikTok à pasta da live antes de vincular o vídeo.')
            linked = account(root, data.account_open_id)
            if not linked or 'video.list' not in linked.get('scopes', []):
                raise HTTPException(422, 'A conta precisa autorizar video.list para coletar métricas.')
            if not data.external_video_id and not VIDEO_URL.fullmatch(data.publication_url):
                raise HTTPException(422, 'Informe o link completo do vídeo TikTok ou escolha um vídeo da conta.')
        elif data.account_open_id:
            raise HTTPException(422, 'Conta TikTok só pode ser usada em publicações TikTok.')
        observed = None
        posted_at = data.posted_at
        if data.platform.lower() == 'tiktok' and posted_at is None:
            try:
                observed = query_video_details(SimpleNamespace(platform='tiktok',
                    account_open_id=data.account_open_id, external_video_id=data.external_video_id,
                    publication_url=data.publication_url), root)
            except TikTokCollectionError as exc:
                raise HTTPException(422, f'Não foi possível consultar o vídeo: {exc.code}. Informe a data da postagem para salvar o vínculo.') from exc
            if observed[2] is None:
                raise HTTPException(422, 'O TikTok não informou a data da postagem. Informe a data para salvar o vínculo.')
            if observed[2] > datetime.now(timezone.utc):
                raise HTTPException(422, 'O TikTok informou uma data futura. Confira a postagem antes de vincular.')
            posted_at = observed[2]
        publication = store.create_publication(data.revision_id, data.platform.strip(),
            data.account.strip(), posted_at, data.publication_url,
            data.account_open_id, data.external_video_id)
        if data.platform.lower() == 'tiktok':
            run, created = store.begin_collection(publication.publication_id,
                'manual-link:' + publication.publication_id, 'explicit_user_action')
            if created:
                if observed:
                    store.finish_collection(run.collection_id, observed[0], observed[1])
                else:
                    background_tasks.add_task(run_collection, run.collection_id, publication.publication_id)
        return publication

    @app.get('/publications', response_model=list[Publication])
    def list_publications():
        return store.list_publications()

    @app.get('/integrations/tiktok')
    def tiktok_status():
        return connection_status(root)

    @app.get('/integrations/tiktok/app')
    def tiktok_app_status():
        return app_status(root)

    @app.put('/integrations/tiktok/app')
    def configure_tiktok(data: TikTokAppInput):
        return save_app(root, data.client_key.strip(), data.client_secret,
                        data.redirect_uri.strip(), data.request_publish_scope)

    @app.get('/integrations/tiktok/accounts')
    def tiktok_accounts():
        return accounts(root)

    @app.get('/integrations/tiktok/authorize')
    def authorize_tiktok(request: Request):
        config = app_status(root)
        if not config['configured']:
            raise HTTPException(409, 'Configure o aplicativo TikTok antes de vincular contas.')
        redirect = urlparse(config['redirect_uri'])
        if request.url.hostname != redirect.hostname:
            raise HTTPException(409, 'Abra o painel pelo domínio HTTPS configurado para o TikTok.')
        state = secrets.token_urlsafe(32)
        response = JSONResponse({'url': authorization_url(root, state)})
        response.set_cookie('tiktok_oauth_state', state, max_age=600, secure=True,
                            httponly=True, samesite='lax', path='/integrations/tiktok')
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/integrations/tiktok/callback', include_in_schema=True)
    def tiktok_callback(request: Request, state: str = '', code: str = '', error: str = ''):
        cookie = request.cookies.get('tiktok_oauth_state', '')
        if not state or not cookie or not hmac.compare_digest(state, cookie):
            raise HTTPException(400, 'Estado de autorização TikTok inválido ou expirado.')
        if error:
            destination = '/?tiktok=denied'
        elif not code:
            raise HTTPException(400, 'Código de autorização TikTok ausente.')
        else:
            try:
                exchange_code(root, code)
                destination = '/?tiktok=connected'
            except TikTokOAuthError:
                destination = '/?tiktok=failed'
        response = RedirectResponse(destination, status_code=303)
        response.delete_cookie('tiktok_oauth_state', path='/integrations/tiktok')
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.delete('/integrations/tiktok/accounts/{open_id}', status_code=204)
    def disconnect_tiktok(open_id: str):
        disconnect(root, open_id)

    @app.patch('/publications/{publication_id}/account', response_model=Publication)
    def link_tiktok_publication(publication_id: str, data: PublicationAccountInput,
                                background_tasks: BackgroundTasks):
        linked = account(root, data.account_open_id)
        if not linked or 'video.list' not in linked.get('scopes', []):
            raise HTTPException(422, 'Conta TikTok sem permissão video.list.')
        publication = store.get_publication_record(publication_id).publication
        project = store.project_for_revision(publication.revision_id)
        if project.account_open_id != data.account_open_id:
            raise HTTPException(422, 'Adicione esta conta TikTok à pasta da live primeiro.')
        updated = store.link_publication_account(publication_id, data.account_open_id)
        run, created = store.begin_collection(publication_id, 'manual-relink:' + str(uuid.uuid4()),
            'explicit_user_action')
        if created:
            background_tasks.add_task(run_collection, run.collection_id, publication_id)
        return updated

    @app.post('/integrations/tiktok/accounts/{open_id}/videos/list')
    def tiktok_video_list(open_id: str, data: TikTokVideoListInput):
        return list_videos(root, open_id, data.cursor)

    @app.post('/integrations/tiktok/accounts/{open_id}/creator-info/query')
    def tiktok_creator_info(open_id: str):
        return creator_info(root, open_id)

    def check_publish(attempt_id: str):
        attempt = store.get_tiktok_publish(attempt_id)
        if not attempt.publish_id:
            return attempt
        result = fetch_post_status(root, attempt.account_open_id, attempt.publish_id)
        if result['status'] == 'FAILED':
            return store.update_tiktok_publish(attempt_id, 'failed',
                error_code=result['fail_reason'] or 'tiktok_publish_failed')
        if result['status'] == 'PUBLISH_COMPLETE':
            post_id = result['post_ids'][0] if result['post_ids'] else None
            if attempt.status == 'completed':
                return store.update_tiktok_post_id(attempt_id, post_id) if post_id else attempt
            return store.complete_tiktok_publish(attempt_id, post_id)
        return attempt

    def run_tiktok_publish(attempt_id: str, file_path: str, options: dict):
        try:
            attempt = store.get_tiktok_publish(attempt_id)
            def initialized(publish_id):
                store.update_tiktok_publish(attempt_id, 'uploading', publish_id)
            publish_id = direct_post(root, attempt.account_open_id, file_path,
                attempt.caption, attempt.privacy_level,
                options['disable_comment'], options['disable_duet'], options['disable_stitch'],
                on_initialized=initialized)
            store.update_tiktok_publish(attempt_id, 'processing', publish_id)
            for delay in (0, 5, 10, 20, 30, 60):
                if delay:
                    time.sleep(delay)
                try:
                    current = check_publish(attempt_id)
                except TikTokPostingError:
                    continue
                if current.status in {'completed', 'failed'}:
                    return
        except TikTokPostingError as exc:
            store.update_tiktok_publish(attempt_id, 'failed', error_code=exc.code)
        except Exception:
            store.update_tiktok_publish(attempt_id, 'failed', error_code='posting_failed')

    @app.get('/tiktok-posts', response_model=list[TikTokPublishAttempt])
    def tiktok_posts():
        return store.list_tiktok_publishes()

    @app.post('/tiktok-posts/schedule', response_model=list[TikTokPublishAttempt], status_code=202)
    def schedule_tiktok_posts(data: TikTokScheduleInput):
        if not data.consent:
            raise HTTPException(422, 'Confirme o agendamento para a conta selecionada.')
        linked = account(root, data.account_open_id)
        if not linked or 'video.publish' not in linked.get('scopes', []):
            raise HTTPException(422, 'Conta sem permissão video.publish.')
        if data.mode == 'interval':
            if not data.start_at or data.start_at.tzinfo is None or not data.interval_hours:
                raise HTTPException(422, 'Informe data inicial com fuso e intervalo em horas.')
            if any(item.scheduled_at for item in data.items):
                raise HTTPException(422, 'No modo intervalo, os horários são calculados automaticamente.')
        elif data.start_at or data.interval_hours or any(item.scheduled_at is None for item in data.items):
            raise HTTPException(422, 'Informe um horário com fuso para cada vídeo.')
        prepared = []
        for index, item in enumerate(data.items):
            if store.project_for_revision(item.revision_id).account_open_id != data.account_open_id:
                raise HTTPException(422, 'Adicione esta conta TikTok à pasta da live primeiro.')
            scheduled_at = (data.start_at + timedelta(hours=data.interval_hours * index)
                if data.mode == 'interval' else item.scheduled_at)
            if scheduled_at.tzinfo is None:
                raise HTTPException(422, 'Horários precisam incluir fuso horário.')
            exported = store.get_export(item.export_id)
            authorized_file(exported.local_path)
            prepared.append({**item.model_dump(exclude={'scheduled_at'}),
                             'scheduled_at': scheduled_at.astimezone(timezone.utc)})
        return store.schedule_tiktok_publishes(data.batch_id, data.account_open_id,
            linked['display_name'], prepared)

    @app.post('/tiktok-posts/{attempt_id}/cancel', response_model=TikTokPublishAttempt)
    def cancel_tiktok_post(attempt_id: str):
        return store.cancel_tiktok_publish(attempt_id)

    @app.post('/tiktok-posts', response_model=TikTokPublishAttempt, status_code=202)
    def start_tiktok_post(data: TikTokPostInput, background_tasks: BackgroundTasks):
        if not data.consent:
            raise HTTPException(422, 'Confirme o envio deste vídeo ao TikTok.')
        if store.project_for_revision(data.revision_id).account_open_id != data.account_open_id:
            raise HTTPException(422, 'Adicione esta conta TikTok à pasta da live primeiro.')
        linked = account(root, data.account_open_id)
        if not linked or 'video.publish' not in linked.get('scopes', []):
            raise HTTPException(422, 'Conta sem permissão video.publish.')
        exported = store.get_export(data.export_id)
        file_path = authorized_file(exported.local_path)
        attempt, created = store.begin_tiktok_publish(data.request_id, data.revision_id,
            data.export_id, data.account_open_id, linked['display_name'],
            data.caption, data.privacy_level)
        if created:
            background_tasks.add_task(run_tiktok_publish, attempt.attempt_id, str(file_path),
                {'disable_comment': data.disable_comment, 'disable_duet': data.disable_duet,
                 'disable_stitch': data.disable_stitch})
        return attempt

    @app.post('/tiktok-posts/{attempt_id}/refresh', response_model=TikTokPublishAttempt)
    def refresh_tiktok_post(attempt_id: str):
        try:
            return check_publish(attempt_id)
        except TikTokPostingError as exc:
            raise HTTPException(502, exc.code) from exc

    def run_collection(run_id: str, publication_id: str):
        publication = store.get_publication_record(publication_id).publication
        try:
            values, reference = query_metrics(publication, root)
            store.finish_collection(run_id, values, reference)
        except TikTokCollectionError as exc:
            store.finish_collection(run_id, {}, 'tiktok:unavailable', exc.code)
        except Exception:
            store.finish_collection(run_id, {}, 'tiktok:unavailable', 'connector_error')

    @app.post('/publications/collect-session', response_model=list[PublicationCollectionRun], status_code=202)
    def collect_session(data: CollectionInput, background_tasks: BackgroundTasks):
        if not connection_status(root)['connected']:
            raise HTTPException(409, 'Conecte uma conta TikTok autorizada antes da coleta.')
        runs = []
        for publication in store.list_publications():
            if data.profile_id is not None:
                try:
                    project = store.project_for_revision(publication.revision_id)
                except KeyError:
                    continue
                if (project.profile_id or 'unassigned') != data.profile_id:
                    continue
            if publication.platform.lower() != 'tiktok':
                continue
            if not publication.external_video_id and not publication.publication_url:
                continue
            if accounts(root) and (not publication.account_open_id or
                                   not account(root, publication.account_open_id)):
                continue
            run, created = store.begin_collection(publication.publication_id,
                data.request_id + ':' + publication.publication_id, data.trigger)
            runs.append(run)
            if created:
                background_tasks.add_task(run_collection, run.collection_id, publication.publication_id)
        return runs

    @app.get('/publications/{publication_id}', response_model=PublicationRecord)
    def publication_record(publication_id: str):
        return store.get_publication_record(publication_id)

    @app.post('/publications/{publication_id}/metrics', response_model=MetricSnapshot, status_code=201)
    def add_manual_metric(publication_id: str, data: ManualMetricInput):
        return store.add_manual_metric(publication_id, data.metric_name, data.value,
            data.reviewer.strip())

    frontend = Path(__file__).resolve().parents[3] / 'frontend' / 'dist'
    if (frontend / 'index.html').is_file() and (frontend / 'app-assets').is_dir():
        app.mount('/app-assets', StaticFiles(directory=frontend / 'app-assets'), name='app-assets')

        @app.get('/', include_in_schema=False)
        def frontend_index():
            return FileResponse(frontend / 'index.html')

    return app
