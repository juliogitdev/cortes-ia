"""API local: mídia autorizada, fila persistida e resultados validados."""
import os
from pathlib import Path
import shutil
import uuid

from fastapi import FastAPI, Header, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from clip_platform.shared.contracts import AnalysisRequest, AnalysisResult, ClipRevision, Interval, MediaAsset
from clip_platform.shared.jobs import Project, Job
from clip_platform.services.store import Store
from clip_platform.ingestion.local import ingest_file


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=200)


class RevisionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    analysis_id: str
    start_s: float = Field(ge=0, allow_inf_nan=False)
    end_s: float = Field(gt=0, allow_inf_nan=False)
    editor_changes: list[str] = Field(default_factory=list)
    parent_revision_id: str | None = None


def create_app(storage_root=None):
    root = Path(storage_root or os.environ.get('CLIP_STORAGE', 'storage')).resolve()
    store = Store(root)
    app = FastAPI(title='Cortes IA — local', version='0.1.0')
    app.state.store = store

    @app.exception_handler(KeyError)
    async def missing(_, exc):
        return JSONResponse(status_code=404, content={'detail': 'Registro não encontrado.'})

    @app.exception_handler(ValueError)
    async def invalid(_, exc):
        return JSONResponse(status_code=422, content={'detail': str(exc)})

    def authorized_file(raw):
        path = Path(raw).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(404, 'Arquivo indisponível na área autorizada.')
        return path

    @app.get('/health')
    def health():
        return {'status': 'ok', 'mode': 'local', 'baseline': 'speech_only'}

    @app.post('/projects', response_model=Project, status_code=201)
    def create_project(data: ProjectInput):
        return store.create_project(data.name.strip() or 'Projeto')

    @app.get('/projects', response_model=list[Project])
    def projects():
        return store.list_projects()

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

    @app.post('/candidates/{candidate_id}/revisions', response_model=ClipRevision, status_code=201)
    def revise(candidate_id: str, data: RevisionInput):
        result = store.get_analysis(data.analysis_id)
        candidate = next((item for item in result.candidates if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise HTTPException(404, 'Candidato não encontrado nesta análise.')
        boundaries = Interval(start_s=data.start_s, end_s=data.end_s)
        if boundaries.end_s > result.asset.duration_s:
            raise HTTPException(422, 'Intervalo excede a gravação.')
        if data.parent_revision_id:
            parent = store.get_revision(data.parent_revision_id)
            if parent.candidate_id != candidate_id or parent.asset_id != result.asset.asset_id:
                raise HTTPException(422, 'Revisão anterior pertence a outro corte.')
        revision = ClipRevision(revision_id=uuid.uuid4().hex, candidate_id=candidate_id,
            asset_id=result.asset.asset_id, boundaries=boundaries, editor_changes=data.editor_changes,
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

    return app
