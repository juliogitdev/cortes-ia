"""SQLite local, fila serial e leases; owner é único por execução do worker."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from clip_platform.shared.contracts import (AnalysisResult, ClipRevision, Interval, MediaAsset,
    Publication, PublicationRecord, PublicationCollectionRun, MetricSnapshot, TikTokPublishAttempt)
from clip_platform.shared.jobs import (CandidateFeedback, ClipEditorial, ClipMediaVariants,
    EditorialProfile, Export, Job, MediaVariant, Project)


class Store:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = time.time
        self._db = self.root / "platform.sqlite3"
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS objects(kind TEXT, id TEXT, data TEXT NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
                    kind TEXT NOT NULL, request_id TEXT NOT NULL, payload TEXT NOT NULL,
                    data TEXT NOT NULL, owner TEXT, lease_until REAL,
                    UNIQUE(project_id,kind,request_id));
                CREATE TABLE IF NOT EXISTS retired_owners(job_id TEXT, owner TEXT,
                    PRIMARY KEY(job_id,owner));
                CREATE TABLE IF NOT EXISTS discarded_candidates(analysis_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL, discarded_at TEXT NOT NULL,
                    PRIMARY KEY(analysis_id,candidate_id));
                CREATE TABLE IF NOT EXISTS feedback_events(id TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL, candidate_id TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS deleted_projects(project_id TEXT PRIMARY KEY,
                    deleted_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS clip_media_selection(
                    analysis_id TEXT NOT NULL, candidate_id TEXT NOT NULL, export_id TEXT NOT NULL,
                    PRIMARY KEY(analysis_id,candidate_id));
                CREATE TABLE IF NOT EXISTS deleted_media_variants(
                    export_id TEXT PRIMARY KEY, deleted_at TEXT NOT NULL);
            """)

    def _connect(self):
        db = sqlite3.connect(self._db, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    @contextmanager
    def _transaction(self):
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _now(self):
        return datetime.fromtimestamp(self._clock(), timezone.utc)

    @staticmethod
    def _encode(data):
        return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)

    def _get(self, db, kind, identifier, model):
        row = db.execute("SELECT data FROM objects WHERE kind=? AND id=?", (kind, identifier)).fetchone()
        if row is None:
            raise KeyError(identifier)
        return model.model_validate_json(row["data"])

    def _put(self, db, kind, identifier, value):
        existing = db.execute("SELECT data FROM objects WHERE kind=? AND id=?", (kind, identifier)).fetchone()
        encoded = value.model_dump_json()
        if existing and existing["data"] != encoded:
            raise ValueError("identificador imutável já contém outro objeto")
        db.execute("INSERT OR IGNORE INTO objects VALUES(?,?,?)", (kind, identifier, encoded))

    def create_project(self, name, profile_id=None):
        with self._transaction() as db:
            profile = self._get(db, 'profile', profile_id, EditorialProfile) if profile_id else None
            project = Project(project_id=str(uuid4()), name=name, created_at=self._now(),
                profile_id=profile_id, account_open_id=profile.account_open_id if profile else None)
            self._put(db, "project", project.project_id, project)
        return project

    def create_profile(self, name, platforms, account_open_id=None):
        if not name.strip():
            raise ValueError('Informe um nome para o perfil.')
        profile = EditorialProfile(profile_id=str(uuid4()), name=name.strip(),
            platforms=sorted(set(platforms)), account_open_id=account_open_id, created_at=self._now())
        with self._transaction() as db:
            self._put(db, 'profile', profile.profile_id, profile)
        return profile

    def list_profiles(self):
        with closing(self._connect()) as db:
            return [EditorialProfile.model_validate_json(row['data']) for row in db.execute(
                "SELECT data FROM objects WHERE kind='profile' ORDER BY rowid")]

    def get_profile(self, profile_id):
        with closing(self._connect()) as db:
            return self._get(db, 'profile', profile_id, EditorialProfile)

    def save_profile_branding(self, profile_id, tiktok_url, brand_name):
        with self._transaction() as db:
            profile = self._get(db, 'profile', profile_id, EditorialProfile)
            profile.tiktok_url = tiktok_url
            profile.brand_name = brand_name
            db.execute("UPDATE objects SET data=? WHERE kind='profile' AND id=?",
                       (profile.model_dump_json(), profile_id))
            return profile

    def bump_profile_avatar(self, profile_id):
        with self._transaction() as db:
            profile = self._get(db, 'profile', profile_id, EditorialProfile)
            profile.avatar_version += 1
            db.execute("UPDATE objects SET data=? WHERE kind='profile' AND id=?",
                       (profile.model_dump_json(), profile_id))
            return profile

    def update_profile(self, profile_id, name, platforms, account_open_id):
        if not name.strip():
            raise ValueError('Informe um nome para o perfil.')
        with self._transaction() as db:
            profile = self._get(db, 'profile', profile_id, EditorialProfile)
            if profile.account_open_id != account_open_id:
                for row in db.execute("SELECT data FROM objects WHERE kind='project'").fetchall():
                    project = Project.model_validate_json(row['data'])
                    if project.profile_id == profile_id and not db.execute(
                        'SELECT 1 FROM deleted_projects WHERE project_id=?', (project.project_id,)).fetchone():
                        self._set_project_account(db, project, account_open_id)
            profile.name = name.strip()
            profile.platforms = sorted(set(platforms))
            profile.account_open_id = account_open_id
            db.execute("UPDATE objects SET data=? WHERE kind='profile' AND id=?",
                (profile.model_dump_json(), profile_id))
            return profile

    def delete_profile(self, profile_id):
        """Remove only the editorial folder; keep lives, media and social links."""
        with self._transaction() as db:
            profile = self._get(db, 'profile', profile_id, EditorialProfile)
            for row in db.execute("SELECT id,data FROM objects WHERE kind='project'").fetchall():
                project = Project.model_validate_json(row['data'])
                if project.profile_id == profile_id:
                    project.profile_id = None
                    db.execute("UPDATE objects SET data=? WHERE kind='project' AND id=?",
                        (project.model_dump_json(), project.project_id))
            db.execute("DELETE FROM objects WHERE kind='profile' AND id=?", (profile_id,))
            return profile

    def assign_project_profile(self, project_id, profile_id):
        with self._transaction() as db:
            project = self._active_project(db, project_id)
            profile = self._get(db, 'profile', profile_id, EditorialProfile) if profile_id else None
            if profile and profile.account_open_id and project.account_open_id not in (None, profile.account_open_id):
                raise ValueError('A live já está vinculada a outra conta TikTok.')
            if profile and profile.account_open_id and not project.account_open_id:
                project = self._set_project_account(db, project, profile.account_open_id)
            project.profile_id = profile_id
            db.execute("UPDATE objects SET data=? WHERE kind='project' AND id=?",
                (project.model_dump_json(), project_id))
            return project

    def get_clip_editorial(self, analysis_id, candidate_id):
        analysis = self.get_analysis(analysis_id)
        candidate = next((item for item in analysis.candidates if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise KeyError(candidate_id)
        with closing(self._connect()) as db:
            row = db.execute("SELECT data FROM objects WHERE kind='clip_editorial' AND id=?",
                (analysis_id + ':' + candidate_id,)).fetchone()
        from clip_platform.selection.social_caption import suggest_caption, suggest_hashtags, suggest_headline
        can_suggest = hasattr(analysis, 'evidence') and hasattr(candidate, 'evidence_ids')
        project_name = self.get_project(self.get_job(analysis_id).project_id).name if can_suggest else ''
        source_uri = analysis.asset.source_uri if can_suggest else ''
        if row:
            saved = ClipEditorial.model_validate_json(row['data'])
            if can_suggest and 'hashtags' not in json.loads(row['data']):
                saved.hashtags = suggest_hashtags(analysis, candidate, project_name, source_uri)
            if can_suggest and not saved.headline:
                saved.headline = suggest_headline(analysis, candidate)
            return saved
        return ClipEditorial(analysis_id=analysis_id, candidate_id=candidate_id,
                             caption=suggest_caption(analysis, candidate, project_name, source_uri) if can_suggest else '',
                             hashtags=suggest_hashtags(analysis, candidate, project_name, source_uri) if can_suggest else '',
                             headline=suggest_headline(analysis, candidate) if can_suggest else '')

    def save_clip_editorial(self, value):
        self.get_clip_editorial(value.analysis_id, value.candidate_id)
        with self._transaction() as db:
            db.execute("INSERT INTO objects(kind,id,data) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data",
                ('clip_editorial', value.analysis_id + ':' + value.candidate_id, value.model_dump_json()))
        return value

    def list_projects(self):
        with closing(self._connect()) as db:
            return [Project.model_validate_json(row["data"]) for row in db.execute(
                "SELECT data FROM objects WHERE kind='project' AND id NOT IN "
                "(SELECT project_id FROM deleted_projects) ORDER BY rowid")]

    def _active_project(self, db, project_id):
        project = self._get(db, 'project', project_id, Project)
        if db.execute('SELECT 1 FROM deleted_projects WHERE project_id=?', (project_id,)).fetchone():
            raise KeyError(project_id)
        return project

    def get_project(self, project_id):
        with closing(self._connect()) as db:
            return self._active_project(db, project_id)

    def project_for_cleanup(self, project_id):
        with closing(self._connect()) as db:
            return self._get(db, 'project', project_id, Project)

    def archive_project(self, project_id):
        """Hide a live after checking that no job or TikTok send can write its media."""
        with self._transaction() as db:
            project = self._get(db, 'project', project_id, Project)
            if db.execute('SELECT 1 FROM deleted_projects WHERE project_id=?', (project_id,)).fetchone():
                return project
            for row in db.execute('SELECT data FROM jobs WHERE project_id=?', (project_id,)):
                if Job.model_validate_json(row['data']).status in {'queued', 'running'}:
                    raise ValueError('Cancele ou conclua as tarefas desta live antes de excluí-la.')
            if project.asset_id:
                revisions = {revision.revision_id for row in db.execute(
                    "SELECT data FROM objects WHERE kind='revision'")
                    if (revision := ClipRevision.model_validate_json(row['data'])).asset_id == project.asset_id}
                for row in db.execute("SELECT data FROM objects WHERE kind='tiktok_publish'"):
                    item = TikTokPublishAttempt.model_validate_json(row['data'])
                    if item.revision_id in revisions and item.status in {
                            'scheduled', 'requested', 'uploading', 'processing'}:
                        raise ValueError('Cancele ou conclua as publicações TikTok pendentes antes de excluir a live.')
            db.execute('INSERT INTO deleted_projects VALUES(?,?)', (project_id, self._now().isoformat()))
            return project

    def rename_project(self, project_id, name):
        name = name.strip()
        if not name:
            raise ValueError('Nome do projeto não pode ser vazio.')
        with self._transaction() as db:
            project = self._active_project(db, project_id)
            project.name = name
            db.execute("UPDATE objects SET data=? WHERE kind='project' AND id=?",
                       (project.model_dump_json(), project_id))
            return project

    def assign_project_account(self, project_id, account_open_id):
        with self._transaction() as db:
            project = self._active_project(db, project_id)
            return self._set_project_account(db, project, account_open_id)

    def _set_project_account(self, db, project, account_open_id):
        if account_open_id and project.asset_id:
            revisions = {revision.revision_id for row in db.execute(
                "SELECT data FROM objects WHERE kind='revision'")
                if (revision := ClipRevision.model_validate_json(row['data'])).asset_id == project.asset_id}
            for row in db.execute("SELECT data FROM objects WHERE kind='publication'"):
                publication = Publication.model_validate_json(row['data'])
                if (publication.revision_id in revisions and publication.account_open_id and
                        publication.account_open_id != account_open_id):
                    raise ValueError('Esta live já possui publicação vinculada a outra conta TikTok.')
            for row in db.execute("SELECT data FROM objects WHERE kind='tiktok_publish'"):
                attempt = TikTokPublishAttempt.model_validate_json(row['data'])
                if (attempt.revision_id in revisions and attempt.account_open_id != account_open_id and
                        attempt.status in {'scheduled', 'requested', 'uploading', 'processing'}):
                    raise ValueError('Esta live possui envio pendente em outra conta TikTok.')
        project.account_open_id = account_open_id
        db.execute("UPDATE objects SET data=? WHERE kind='project' AND id=?",
            (project.model_dump_json(), project.project_id))
        return project

    def project_for_revision(self, revision_id):
        with closing(self._connect()) as db:
            revision = self._get(db, 'revision', revision_id, ClipRevision)
            for row in db.execute("SELECT data FROM objects WHERE kind='project'"):
                project = Project.model_validate_json(row['data'])
                if db.execute('SELECT 1 FROM deleted_projects WHERE project_id=?',
                              (project.project_id,)).fetchone():
                    continue
                if project.asset_id == revision.asset_id:
                    return project
        raise KeyError(revision_id)

    def put_asset(self, project_id, asset):
        asset = MediaAsset.model_validate(asset)
        with self._transaction() as db:
            project = self._active_project(db, project_id)
            self._put(db, "asset", asset.asset_id, asset)
            project.asset_id = asset.asset_id
            db.execute("UPDATE objects SET data=? WHERE kind='project' AND id=?", (project.model_dump_json(), project_id))

    def get_asset(self, asset_id):
        with closing(self._connect()) as db:
            return self._get(db, "asset", asset_id, MediaAsset)

    def enqueue(self, project_id, kind, request_id, payload):
        canonical = self._encode(payload)
        with self._transaction() as db:
            project = self._active_project(db, project_id)
            row = db.execute("SELECT * FROM jobs WHERE project_id=? AND kind=? AND request_id=?", (project_id, kind, request_id)).fetchone()
            if row:
                if row["payload"] != canonical:
                    raise ValueError("chave de idempotência com payload divergente")
                return Job.model_validate_json(row["data"])
            if kind == 'download':
                if project.asset_id:
                    raise ValueError('Esta live já possui uma gravação; não é necessário baixar novamente.')
                for existing in db.execute("SELECT data FROM jobs WHERE project_id=? AND kind='download' ORDER BY rowid DESC", (project_id,)):
                    previous = Job.model_validate_json(existing['data'])
                    if previous.status in {'queued', 'running'}:
                        if previous.payload == payload:
                            return previous
                        raise ValueError('Já existe outro download em andamento nesta live.')
            job = Job(job_id=str(uuid4()), project_id=project_id, kind=kind, request_id=request_id,
                      status="queued", stage="queued", payload=payload, created_at=self._now(), updated_at=self._now())
            db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,NULL,NULL)", (job.job_id, project_id, kind, request_id, canonical, job.model_dump_json()))
            return job

    def _job(self, db, job_id):
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return row, Job.model_validate_json(row["data"])

    def get_job(self, job_id):
        with closing(self._connect()) as db:
            return self._job(db, job_id)[1]

    def list_jobs(self, project_id):
        with closing(self._connect()) as db:
            self._active_project(db, project_id)
            rows = db.execute('SELECT data FROM jobs WHERE project_id=? ORDER BY rowid DESC', (project_id,))
            return [Job.model_validate_json(row['data']) for row in rows]

    def claim(self, owner, lease_s=60):
        if not owner or lease_s <= 0:
            raise ValueError("owner e lease positivo obrigatórios")
        with self._transaction() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY rowid").fetchall()
            if any(row["owner"] and row["lease_until"] is not None and row["lease_until"] > self._clock() for row in rows):
                return None
            # Reclaim expirado precede novos jobs: continua reserva global serial.
            eligible = [row for row in rows if Job.model_validate_json(row["data"]).status == "running"]
            eligible += [row for row in rows if Job.model_validate_json(row["data"]).status == "queued"]
            if not eligible:
                return None
            row = eligible[0]
            if db.execute("SELECT 1 FROM retired_owners WHERE job_id=? AND owner=?", (row["id"], owner)).fetchone() or row["owner"] == owner:
                raise ValueError("owner deve ser novo por execução/reclaim")
            if row["owner"]:
                db.execute("INSERT OR IGNORE INTO retired_owners VALUES(?,?)", (row["id"], row["owner"]))
            job = Job.model_validate_json(row["data"])
            job.status = "running"
            job.attempts += 1
            job.progress = None
            job.stage_progress = None
            job.eta_s = None
            job.progress_at = None
            job.updated_at = self._now()
            db.execute("UPDATE jobs SET data=?,owner=?,lease_until=? WHERE id=?", (job.model_dump_json(), owner, self._clock()+lease_s, job.job_id))
            return job

    def _owned(self, db, job_id, owner):
        row, job = self._job(db, job_id)
        if job.status != "running" or row["owner"] != owner or row["lease_until"] <= self._clock():
            raise ValueError("worker sem lease vigente; escrita rejeitada")
        return job

    def heartbeat(self, job_id, owner, lease_s=60):
        if lease_s <= 0:
            raise ValueError("lease deve ser positivo")
        with self._transaction() as db:
            job = self._owned(db, job_id, owner)
            job.updated_at = self._now()
            db.execute("UPDATE jobs SET data=?,lease_until=? WHERE id=?", (job.model_dump_json(), self._clock()+lease_s, job_id))

    def set_stage(self, job_id, owner, stage):
        if not stage:
            raise ValueError("etapa vazia")
        with self._transaction() as db:
            job = self._owned(db, job_id, owner)
            job.stage = stage
            job.updated_at = self._now()
            db.execute("UPDATE jobs SET data=? WHERE id=?", (job.model_dump_json(), job_id))

    def set_progress(self, job_id, owner, stage, progress, stage_progress=None, eta_s=None):
        if not 0 <= progress <= 1 or stage_progress is not None and not 0 <= stage_progress <= 1:
            raise ValueError('Progresso fora da faixa de 0 a 1.')
        if eta_s is not None and not 0 <= eta_s <= 24 * 60 * 60:
            raise ValueError('Estimativa de tempo inválida.')
        with self._transaction() as db:
            job = self._owned(db, job_id, owner)
            if job.progress is not None and progress < job.progress:
                progress = job.progress
            job.stage = stage
            job.progress = progress
            job.stage_progress = stage_progress
            job.eta_s = eta_s
            job.progress_at = self._now()
            job.updated_at = job.progress_at
            db.execute("UPDATE jobs SET data=? WHERE id=?", (job.model_dump_json(), job_id))

    def _complete(self, job_id, owner, status, result=None, error=None):
        with self._transaction() as db:
            job = self._owned(db, job_id, owner)
            if status == "completed":
                model = {'analysis': AnalysisResult, 'export': Export, 'download': MediaAsset}[job.kind]
                validated = model.model_validate(result)
                result = validated.model_dump(mode="json")
                if job.kind == "download":
                    project = self._get(db, "project", job.project_id, Project)
                    if project.asset_id and project.asset_id != validated.asset_id:
                        raise ValueError("projeto já contém outra gravação")
                    if job.payload.get('url') != validated.source_uri:
                        raise ValueError("origem do download divergente")
                    self._put(db, 'asset', validated.asset_id, validated)
                    project.asset_id = validated.asset_id
                    db.execute("UPDATE objects SET data=? WHERE kind='project' AND id=?", (project.model_dump_json(), project.project_id))
                elif job.kind == "export":
                    revision = self._get(db, "revision", validated.revision_id, ClipRevision)
                    if revision.asset_id != validated.asset_id:
                        raise ValueError("export de outra mídia")
                    if job.payload.get("revision_id") not in {None, validated.revision_id}:
                        raise ValueError("export de outra revisão")
                    self._put(db, "export", validated.export_id, validated)
                    if revision.analysis_id and revision.candidate_id:
                        db.execute('INSERT OR REPLACE INTO clip_media_selection VALUES(?,?,?)',
                                   (revision.analysis_id, revision.candidate_id, validated.export_id))
                else:
                    if job.payload.get("asset_id") not in {None, validated.asset.asset_id}:
                        raise ValueError("análise de outra mídia")
            job.status = status
            job.stage = status
            if status == 'completed':
                job.progress = 1.0
                job.stage_progress = 1.0
                job.eta_s = 0.0
                job.progress_at = self._now()
            else:
                job.eta_s = None
            job.result = result
            job.error = error
            job.updated_at = self._now()
            db.execute("UPDATE jobs SET data=? WHERE id=?", (job.model_dump_json(), job_id))
            if status == 'completed' and job.kind == 'analysis':
                self._auto_exports(db, job, validated)

    def _auto_exports(self, db, analysis_job, result):
        jobs = []
        for candidate in result.candidates:
            if db.execute('SELECT 1 FROM discarded_candidates WHERE analysis_id=? AND candidate_id=?',
                          (analysis_job.job_id, candidate.candidate_id)).fetchone():
                continue
            revision_id = 'auto-' + hashlib.sha256(
                f'{analysis_job.job_id}:{candidate.candidate_id}'.encode()).hexdigest()[:32]
            revision = ClipRevision(revision_id=revision_id, candidate_id=candidate.candidate_id,
                asset_id=result.asset.asset_id, analysis_id=analysis_job.job_id,
                boundaries=Interval(start_s=candidate.start_s, end_s=candidate.end_s),
                editor_changes=['Limites iniciais sugeridos automaticamente'])
            self._put(db, 'revision', revision_id, revision)
            request_id = 'auto-export-' + revision_id
            payload = {'revision_id': revision_id, 'candidate_id': candidate.candidate_id,
                       'analysis_id': analysis_job.job_id, 'auto': True}
            canonical = self._encode(payload)
            row = db.execute('SELECT * FROM jobs WHERE project_id=? AND kind=? AND request_id=?',
                (analysis_job.project_id, 'export', request_id)).fetchone()
            if row:
                if row['payload'] != canonical:
                    raise ValueError('exportação automática existente com payload divergente')
                jobs.append(Job.model_validate_json(row['data']))
                continue
            job = Job(job_id=str(uuid4()), project_id=analysis_job.project_id, kind='export',
                request_id=request_id, status='queued', stage='queued', payload=payload,
                created_at=self._now(), updated_at=self._now())
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,NULL,NULL)',
                (job.job_id, job.project_id, job.kind, request_id, canonical, job.model_dump_json()))
            jobs.append(job)
        return jobs

    def ensure_auto_exports(self, analysis_id):
        """Prepara também análises concluídas antes desta funcionalidade, sem duplicar cortes."""
        with self._transaction() as db:
            _, job = self._job(db, analysis_id)
            self._active_project(db, job.project_id)
            if job.kind != 'analysis' or job.status != 'completed':
                raise ValueError('análise ainda não concluída')
            return self._auto_exports(db, job, AnalysisResult.model_validate(job.result))

    def list_discarded(self, analysis_id):
        self.get_analysis(analysis_id)
        with closing(self._connect()) as db:
            return [row['candidate_id'] for row in db.execute(
                'SELECT candidate_id FROM discarded_candidates WHERE analysis_id=?', (analysis_id,))]

    def discard_candidate(self, analysis_id, candidate_id):
        """Oculta candidato, cancela seus exports e retorna arquivos automáticos para remoção."""
        with self._transaction() as db:
            _, analysis_job = self._job(db, analysis_id)
            self._active_project(db, analysis_job.project_id)
            if analysis_job.kind != 'analysis' or analysis_job.status != 'completed':
                raise ValueError('análise ainda não concluída')
            analysis = AnalysisResult.model_validate(analysis_job.result)
            if candidate_id not in {item.candidate_id for item in analysis.candidates}:
                raise KeyError(candidate_id)
            revisions = {revision.revision_id for row in db.execute(
                "SELECT data FROM objects WHERE kind='revision'")
                if (revision := ClipRevision.model_validate_json(row['data'])).asset_id == analysis.asset.asset_id
                and revision.candidate_id == candidate_id}
            for row in db.execute("SELECT data FROM objects WHERE kind='tiktok_publish'"):
                attempt = TikTokPublishAttempt.model_validate_json(row['data'])
                if attempt.revision_id in revisions and attempt.status in {
                        'scheduled', 'requested', 'uploading', 'processing'}:
                    raise ValueError('Cancele ou conclua a publicação TikTok antes de excluir este corte.')
            db.execute('INSERT OR IGNORE INTO discarded_candidates VALUES(?,?,?)',
                       (analysis_id, candidate_id, self._now().isoformat()))
            outputs = []
            seen_exports = set()
            rows = db.execute('SELECT * FROM jobs WHERE project_id=? AND kind=?',
                              (analysis_job.project_id, 'export')).fetchall()
            for row in rows:
                job = Job.model_validate_json(row['data'])
                if (job.payload.get('revision_id') not in revisions and
                        (job.payload.get('analysis_id') != analysis_id or
                         job.payload.get('candidate_id') != candidate_id)):
                    continue
                if job.status in {'queued', 'running'}:
                    job.status = 'cancelled'
                    job.stage = 'cancelled'
                    job.updated_at = self._now()
                    db.execute('UPDATE jobs SET data=? WHERE id=?', (job.model_dump_json(), job.job_id))
                elif job.status == 'completed' and job.result:
                    exported = Export.model_validate(job.result)
                    if exported.export_id not in seen_exports:
                        outputs.append(exported)
                        seen_exports.add(exported.export_id)
            return outputs

    def add_feedback(self, analysis_id, candidate_id, rating, note=''):
        with self._transaction() as db:
            _, job = self._job(db, analysis_id)
            if job.kind != 'analysis' or job.status != 'completed':
                raise ValueError('análise ainda não concluída')
            result = AnalysisResult.model_validate(job.result)
            if candidate_id not in {item.candidate_id for item in result.candidates}:
                raise KeyError(candidate_id)
            feedback = CandidateFeedback(feedback_id=str(uuid4()), analysis_id=analysis_id,
                candidate_id=candidate_id, rating=rating, note=note, created_at=self._now())
            db.execute('INSERT INTO feedback_events VALUES(?,?,?,?)',
                       (feedback.feedback_id, analysis_id, candidate_id, feedback.model_dump_json()))
            return feedback

    def list_feedback(self, analysis_id, candidate_id):
        self.get_analysis(analysis_id)
        with closing(self._connect()) as db:
            return [CandidateFeedback.model_validate_json(row['data']) for row in db.execute(
                'SELECT data FROM feedback_events WHERE analysis_id=? AND candidate_id=? ORDER BY rowid',
                (analysis_id, candidate_id))]

    def finish(self, job_id, owner, result):
        self._complete(job_id, owner, "completed", result=result)

    def fail(self, job_id, owner, error):
        if not error:
            raise ValueError("erro obrigatório")
        self._complete(job_id, owner, "failed", error=str(error))

    def cancel(self, job_id):
        with self._transaction() as db:
            _, job = self._job(db, job_id)
            if job.status == "cancelled":
                return
            if job.status not in {"queued", "running"}:
                raise ValueError("job terminal não pode ser cancelado")
            job.status = "cancelled"
            job.stage = "cancelled"
            job.eta_s = None
            job.updated_at = self._now()
            db.execute("UPDATE jobs SET data=? WHERE id=?", (job.model_dump_json(), job_id))

    def release(self, job_id, owner):
        """Somente após processo filho encerrado: libera reserva de job terminal."""
        with self._transaction() as db:
            row, job = self._job(db, job_id)
            if job.status not in {"completed", "failed", "cancelled"}:
                raise ValueError("reserva de job ativo não pode ser liberada")
            if row["owner"] != owner:
                if row["owner"] is None and db.execute("SELECT 1 FROM retired_owners WHERE job_id=? AND owner=?", (job_id, owner)).fetchone():
                    return
                raise ValueError("owner incorreto para release")
            db.execute("INSERT OR IGNORE INTO retired_owners VALUES(?,?)", (job_id, owner))
            db.execute("UPDATE jobs SET owner=NULL,lease_until=NULL WHERE id=?", (job_id,))

    def put_revision(self, revision):
        revision = ClipRevision.model_validate(revision)
        with self._transaction() as db:
            asset = self._get(db, "asset", revision.asset_id, MediaAsset)
            if revision.boundaries.end_s > asset.duration_s:
                raise ValueError("revisão fora da mídia")
            if revision.analysis_id:
                _, analysis_job = self._job(db, revision.analysis_id)
                if analysis_job.kind != 'analysis' or analysis_job.status != 'completed':
                    raise ValueError('análise da revisão indisponível')
                analysis = AnalysisResult.model_validate(analysis_job.result)
                if (analysis.asset.asset_id != revision.asset_id or
                        revision.candidate_id not in {item.candidate_id for item in analysis.candidates}):
                    raise ValueError('revisão não pertence à análise')
            if revision.parent_revision_id:
                parent = self._get(db, "revision", revision.parent_revision_id, ClipRevision)
                if parent.candidate_id != revision.candidate_id or parent.asset_id != revision.asset_id:
                    raise ValueError("revisão pai incompatível")
            self._put(db, "revision", revision.revision_id, revision)

    def get_revision(self, revision_id):
        with closing(self._connect()) as db:
            return self._get(db, "revision", revision_id, ClipRevision)

    def put_export(self, export):
        export = Export.model_validate(export)
        with self._transaction() as db:
            revision = self._get(db, "revision", export.revision_id, ClipRevision)
            if revision.asset_id != export.asset_id:
                raise ValueError("export de outra mídia")
            self._put(db, "export", export.export_id, export)

    def get_export(self, export_id):
        with closing(self._connect()) as db:
            if db.execute('SELECT 1 FROM deleted_media_variants WHERE export_id=?',
                          (export_id,)).fetchone():
                raise KeyError(export_id)
            return self._get(db, "export", export_id, Export)

    def _media_context(self, db, analysis_id, candidate_id):
        _, job = self._job(db, analysis_id)
        self._active_project(db, job.project_id)
        if job.kind != 'analysis' or job.status != 'completed':
            raise ValueError('análise ainda não concluída')
        result = AnalysisResult.model_validate(job.result)
        if candidate_id not in {item.candidate_id for item in result.candidates}:
            raise KeyError(candidate_id)
        if db.execute('SELECT 1 FROM discarded_candidates WHERE analysis_id=? AND candidate_id=?',
                      (analysis_id, candidate_id)).fetchone():
            raise KeyError(candidate_id)
        revision_ids = {revision.revision_id for row in db.execute(
            "SELECT data FROM objects WHERE kind='revision'")
            if (revision := ClipRevision.model_validate_json(row['data'])).asset_id == result.asset.asset_id
            and revision.candidate_id == candidate_id
            and revision.analysis_id in {None, analysis_id}}
        return job, revision_ids

    def media_variants(self, analysis_id, candidate_id):
        with self._transaction() as db:
            analysis_job, revision_ids = self._media_context(db, analysis_id, candidate_id)
            directory = (self.root / 'projects' / analysis_job.project_id / 'exports').resolve()
            jobs = [Job.model_validate_json(row['data']) for row in db.execute(
                "SELECT data FROM jobs WHERE project_id=? AND kind='export' ORDER BY rowid DESC",
                (analysis_job.project_id,))]
            created = {item.result['export_id']: item.created_at for item in jobs
                       if item.status == 'completed' and item.result and item.result.get('export_id')}
            variants = []
            if directory.is_dir():
                for sidecar in directory.glob('*.export.json'):
                    if sidecar.is_symlink():
                        continue
                    try:
                        exported = Export.model_validate_json(sidecar.read_text(encoding='utf-8'))
                        path = Path(exported.local_path).resolve(strict=True)
                    except (ValueError, OSError):
                        continue
                    if (exported.revision_id not in revision_ids or path.parent != directory
                            or path.suffix != '.mp4' or path.with_suffix('.export.json') != sidecar.resolve()
                            or db.execute('SELECT 1 FROM deleted_media_variants WHERE export_id=?',
                                          (exported.export_id,)).fetchone()):
                        continue
                    self._put(db, 'export', exported.export_id, exported)
                    variants.append(MediaVariant(export_id=exported.export_id,
                        revision_id=exported.revision_id,
                        kind='captioned' if exported.export_id.startswith('export-subtitle-') else 'original',
                        duration_s=exported.duration_s,
                        created_at=created.get(exported.export_id) or
                            datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)))
            variants.sort(key=lambda item: (item.created_at, item.export_id), reverse=True)
            row = db.execute('SELECT export_id FROM clip_media_selection WHERE analysis_id=? AND candidate_id=?',
                             (analysis_id, candidate_id)).fetchone()
            selected = row['export_id'] if row and any(
                item.export_id == row['export_id'] for item in variants) else None
            if not selected:
                selected = next((item.result['export_id'] for item in jobs
                    if item.status == 'completed' and item.result and
                    item.result.get('export_id') in {v.export_id for v in variants} and
                    item.payload.get('candidate_id') == candidate_id and
                    item.payload.get('analysis_id') == analysis_id), None)
            if not selected and variants:
                selected = variants[0].export_id
            for item in variants:
                item.selected = item.export_id == selected
            return ClipMediaVariants(analysis_id=analysis_id, candidate_id=candidate_id,
                                     selected_export_id=selected, variants=variants)

    def project_media_variants(self, project_id):
        jobs = self.list_jobs(project_id)
        groups = []
        for job in jobs:
            if job.kind != 'analysis' or job.status != 'completed':
                continue
            analysis = AnalysisResult.model_validate(job.result)
            for candidate in analysis.candidates:
                try:
                    groups.append(self.media_variants(job.job_id, candidate.candidate_id))
                except KeyError:
                    pass  # Corte descartado.
        return groups

    def select_media_variant(self, analysis_id, candidate_id, export_id):
        group = self.media_variants(analysis_id, candidate_id)
        if export_id not in {item.export_id for item in group.variants}:
            raise KeyError(export_id)
        with self._transaction() as db:
            self._media_context(db, analysis_id, candidate_id)
            db.execute('INSERT OR REPLACE INTO clip_media_selection VALUES(?,?,?)',
                       (analysis_id, candidate_id, export_id))
        return self.media_variants(analysis_id, candidate_id)

    def hide_media_variant(self, analysis_id, candidate_id, export_id):
        group = self.media_variants(analysis_id, candidate_id)
        item = next((variant for variant in group.variants if variant.export_id == export_id), None)
        if item is None:
            raise KeyError(export_id)
        if item.kind != 'captioned':
            raise ValueError('O vídeo original deve ser preservado.')
        with self._transaction() as db:
            self._media_context(db, analysis_id, candidate_id)
            for row in db.execute("SELECT data FROM objects WHERE kind='tiktok_publish'"):
                attempt = TikTokPublishAttempt.model_validate_json(row['data'])
                if attempt.export_id == export_id and attempt.status in {
                        'scheduled', 'requested', 'uploading', 'processing'}:
                    raise ValueError('Cancele ou conclua o envio antes de excluir esta versão.')
            db.execute('INSERT OR IGNORE INTO deleted_media_variants VALUES(?,?)',
                       (export_id, self._now().isoformat()))
            if group.selected_export_id == export_id:
                original = next((variant for variant in group.variants if variant.kind == 'original'), None)
                replacement = original or next((variant for variant in group.variants
                    if variant.export_id != export_id), None)
                if replacement:
                    db.execute('INSERT OR REPLACE INTO clip_media_selection VALUES(?,?,?)',
                               (analysis_id, candidate_id, replacement.export_id))
                else:
                    db.execute('DELETE FROM clip_media_selection WHERE analysis_id=? AND candidate_id=?',
                               (analysis_id, candidate_id))
        return self._get_export_record(export_id)

    def _get_export_record(self, export_id):
        with closing(self._connect()) as db:
            return self._get(db, 'export', export_id, Export)

    def get_analysis(self, job_id):
        job = self.get_job(job_id)
        if job.kind != "analysis" or job.status != "completed":
            raise ValueError("análise ainda não concluída")
        return AnalysisResult.model_validate(job.result)

    def create_publication(self, revision_id, platform, account, posted_at, publication_url,
                           account_open_id=None, external_video_id=None):
        with self._transaction() as db:
            self._get(db, 'revision', revision_id, ClipRevision)
            publication = Publication(publication_id=str(uuid4()), revision_id=revision_id,
                platform=platform, account=account, account_open_id=account_open_id, posted_at=posted_at,
                publication_url=publication_url, external_video_id=external_video_id,
                link_type='manual')
            self._put(db, 'publication', publication.publication_id, publication)
            return publication

    def begin_tiktok_publish(self, request_id, revision_id, export_id, account_open_id,
                             account_name, caption, privacy_level):
        with self._transaction() as db:
            if db.execute('SELECT 1 FROM deleted_media_variants WHERE export_id=?',
                          (export_id,)).fetchone():
                raise KeyError(export_id)
            export = self._get(db, 'export', export_id, Export)
            if export.revision_id != revision_id:
                raise ValueError('Exportação não pertence ao corte selecionado.')
            self._get(db, 'revision', revision_id, ClipRevision)
            existing = [TikTokPublishAttempt.model_validate_json(row['data']) for row in db.execute(
                "SELECT data FROM objects WHERE kind='tiktok_publish' ORDER BY rowid")]
            for item in existing:
                if item.request_id == request_id:
                    return item, False
            if any(item.revision_id == revision_id and item.account_open_id == account_open_id and
                   item.status in {'scheduled', 'requested', 'uploading', 'processing'} for item in existing):
                raise ValueError('Este corte já tem uma publicação em andamento nesta conta.')
            now = self._now()
            item = TikTokPublishAttempt(attempt_id=str(uuid4()), request_id=request_id,
                revision_id=revision_id, export_id=export_id, account_open_id=account_open_id,
                account_name=account_name, caption=caption, privacy_level=privacy_level,
                requested_at=now, updated_at=now, status='requested')
            self._put(db, 'tiktok_publish', item.attempt_id, item)
            return item, True

    def get_tiktok_publish(self, attempt_id):
        with closing(self._connect()) as db:
            return self._get(db, 'tiktok_publish', attempt_id, TikTokPublishAttempt)

    def schedule_tiktok_publishes(self, batch_id, account_open_id, account_name, items):
        """Create a complete batch in one transaction; nothing is posted here."""
        with self._transaction() as db:
            existing = [TikTokPublishAttempt.model_validate_json(row['data']) for row in db.execute(
                "SELECT data FROM objects WHERE kind='tiktok_publish' ORDER BY rowid")]
            previous = [item for item in existing if item.batch_id == batch_id]
            if previous:
                return previous
            if len({item['export_id'] for item in items}) != len(items):
                raise ValueError('O mesmo vídeo aparece mais de uma vez no lote.')
            now = self._now()
            created = []
            for data in items:
                if db.execute('SELECT 1 FROM deleted_media_variants WHERE export_id=?',
                              (data['export_id'],)).fetchone():
                    raise KeyError(data['export_id'])
                export = self._get(db, 'export', data['export_id'], Export)
                if export.revision_id != data['revision_id']:
                    raise ValueError('Exportação não pertence ao corte selecionado.')
                self._get(db, 'revision', data['revision_id'], ClipRevision)
                if data['scheduled_at'] <= now:
                    raise ValueError('Escolha um horário futuro para cada vídeo.')
                if any(item.revision_id == data['revision_id'] and
                       item.account_open_id == account_open_id and
                       item.status in {'scheduled', 'requested', 'uploading', 'processing'}
                       for item in existing):
                    raise ValueError('Este corte já tem uma publicação pendente nesta conta.')
                attempt = TikTokPublishAttempt(attempt_id=str(uuid4()), request_id=str(uuid4()),
                    revision_id=data['revision_id'], export_id=data['export_id'],
                    account_open_id=account_open_id, account_name=account_name,
                    caption=data['caption'], privacy_level=data['privacy_level'],
                    disable_comment=data['disable_comment'], disable_duet=data['disable_duet'],
                    disable_stitch=data['disable_stitch'], requested_at=now, updated_at=now,
                    scheduled_at=data['scheduled_at'], batch_id=batch_id, status='scheduled')
                created.append(attempt)
                existing.append(attempt)
            for attempt in created:
                self._put(db, 'tiktok_publish', attempt.attempt_id, attempt)
            return created

    def claim_due_tiktok_publish(self):
        """Claim exactly one due post across scheduler processes."""
        with self._transaction() as db:
            now = self._now()
            for row in db.execute("SELECT data FROM objects WHERE kind='tiktok_publish' ORDER BY rowid"):
                item = TikTokPublishAttempt.model_validate_json(row['data'])
                if item.status == 'scheduled' and item.scheduled_at <= now:
                    item.status = 'requested'
                    item.updated_at = now
                    db.execute("UPDATE objects SET data=? WHERE kind='tiktok_publish' AND id=?",
                               (item.model_dump_json(), item.attempt_id))
                    return item
            return None

    def cancel_tiktok_publish(self, attempt_id):
        with self._transaction() as db:
            item = self._get(db, 'tiktok_publish', attempt_id, TikTokPublishAttempt)
            if item.status != 'scheduled':
                raise ValueError('Só é possível cancelar um envio ainda agendado.')
            item.status = 'cancelled'
            item.updated_at = self._now()
            db.execute("UPDATE objects SET data=? WHERE kind='tiktok_publish' AND id=?",
                       (item.model_dump_json(), attempt_id))
            return item

    def mark_interrupted_tiktok_publishes(self):
        """Never retry an uncertain upload automatically after process restart."""
        with self._transaction() as db:
            count = 0
            for row in db.execute("SELECT data FROM objects WHERE kind='tiktok_publish'"):
                item = TikTokPublishAttempt.model_validate_json(row['data'])
                if item.scheduled_at and item.status == 'requested':
                    item.status = 'failed'
                    item.error_code = 'scheduler_interrupted_check_tiktok'
                    item.updated_at = self._now()
                    db.execute("UPDATE objects SET data=? WHERE kind='tiktok_publish' AND id=?",
                               (item.model_dump_json(), item.attempt_id))
                    count += 1
            return count

    def list_tiktok_publishes(self):
        with closing(self._connect()) as db:
            return [TikTokPublishAttempt.model_validate_json(row['data']) for row in db.execute(
                "SELECT data FROM objects WHERE kind='tiktok_publish' ORDER BY rowid DESC")]

    def update_tiktok_publish(self, attempt_id, status, publish_id=None, error_code=None):
        with self._transaction() as db:
            item = self._get(db, 'tiktok_publish', attempt_id, TikTokPublishAttempt)
            if item.status in {'completed', 'failed', 'cancelled'}:
                return item
            data = item.model_dump()
            data.update(status=status, updated_at=self._now(),
                        publish_id=publish_id or item.publish_id, error_code=error_code)
            updated = TikTokPublishAttempt.model_validate(data)
            db.execute("UPDATE objects SET data=? WHERE kind='tiktok_publish' AND id=?",
                       (updated.model_dump_json(), attempt_id))
            return updated

    def complete_tiktok_publish(self, attempt_id, external_video_id=None):
        with self._transaction() as db:
            item = self._get(db, 'tiktok_publish', attempt_id, TikTokPublishAttempt)
            if item.status == 'completed':
                return item
            if not item.publish_id:
                raise ValueError('Tentativa sem publish_id.')
            now = self._now()
            publication = Publication(publication_id=str(uuid4()), revision_id=item.revision_id,
                platform='tiktok', account=item.account_name, account_open_id=item.account_open_id,
                posted_at=now, publication_url=None, external_video_id=external_video_id,
                link_type='automatic', publish_id=item.publish_id)
            self._put(db, 'publication', publication.publication_id, publication)
            data = item.model_dump()
            data.update(status='completed', updated_at=now, publication_id=publication.publication_id,
                        external_video_id=external_video_id)
            updated = TikTokPublishAttempt.model_validate(data)
            db.execute("UPDATE objects SET data=? WHERE kind='tiktok_publish' AND id=?",
                       (updated.model_dump_json(), attempt_id))
            return updated

    def update_tiktok_post_id(self, attempt_id, external_video_id):
        with self._transaction() as db:
            item = self._get(db, 'tiktok_publish', attempt_id, TikTokPublishAttempt)
            if item.status != 'completed' or not item.publication_id:
                raise ValueError('Publicação ainda não concluída.')
            if item.external_video_id == external_video_id:
                return item
            publication = self._get(db, 'publication', item.publication_id, Publication)
            publication.external_video_id = external_video_id
            db.execute("UPDATE objects SET data=? WHERE kind='publication' AND id=?",
                       (publication.model_dump_json(), publication.publication_id))
            item.external_video_id = external_video_id
            item.updated_at = self._now()
            db.execute("UPDATE objects SET data=? WHERE kind='tiktok_publish' AND id=?",
                       (item.model_dump_json(), attempt_id))
            return item

    def link_publication_account(self, publication_id, open_id):
        with self._transaction() as db:
            publication = self._get(db, 'publication', publication_id, Publication)
            if publication.platform.lower() != 'tiktok':
                raise ValueError('Somente publicações TikTok aceitam esta vinculação.')
            if publication.link_type == 'automatic':
                raise ValueError('A conta de uma publicação automática não pode ser trocada.')
            publication.account_open_id = open_id
            db.execute("UPDATE objects SET data=? WHERE kind='publication' AND id=?",
                       (publication.model_dump_json(), publication_id))
            return publication

    def list_publications(self):
        with closing(self._connect()) as db:
            rows = db.execute("SELECT data FROM objects WHERE kind='publication' ORDER BY rowid DESC")
            return [Publication.model_validate_json(row['data']) for row in rows]

    def get_publication_record(self, publication_id):
        with closing(self._connect()) as db:
            publication = self._get(db, 'publication', publication_id, Publication)
            runs = [PublicationCollectionRun.model_validate_json(row['data']) for row in db.execute(
                "SELECT data FROM objects WHERE kind='collection' ORDER BY rowid")]
            rows = db.execute("SELECT data FROM objects WHERE kind='metric' ORDER BY rowid")
            snapshots = [MetricSnapshot.model_validate_json(row['data']) for row in rows]
            return PublicationRecord(publication=publication,
                collections=[item for item in runs if item.publication_id == publication_id],
                snapshots=[item for item in snapshots if item.publication_id == publication_id])

    def begin_collection(self, publication_id, request_id, trigger='authorized_session_start'):
        with self._transaction() as db:
            publication = self._get(db, 'publication', publication_id, Publication)
            rows = db.execute("SELECT data FROM objects WHERE kind='collection' ORDER BY rowid").fetchall()
            runs = [PublicationCollectionRun.model_validate_json(row['data']) for row in rows]
            for run in runs:
                if run.publication_id == publication_id and run.request_id == request_id:
                    return run, False
            active = next((run for run in runs if run.publication_id == publication_id and
                           run.status in {'requested', 'collecting'}), None)
            if active:
                if (self._now() - active.requested_at).total_seconds() < 90:
                    return active, False
                active.status = 'failed'
                active.finished_at = self._now()
                active.error_code = 'stale_collection'
                db.execute("UPDATE objects SET data=? WHERE kind='collection' AND id=?",
                           (active.model_dump_json(), active.collection_id))
            now = self._now()
            if now < publication.posted_at:
                raise ValueError('Publicação futura não pode ser coletada.')
            run = PublicationCollectionRun(collection_id=str(uuid4()), publication_id=publication_id,
                requested_at=now, started_at=now, status='collecting',
                connector_version='tiktok-display-v1', request_id=request_id,
                trigger=trigger)
            self._put(db, 'collection', run.collection_id, run)
            return run, True

    def finish_collection(self, collection_id, values, source_reference, error_code=None):
        with self._transaction() as db:
            run = self._get(db, 'collection', collection_id, PublicationCollectionRun)
            if run.status in {'completed', 'partial', 'failed'}:
                return run
            publication = self._get(db, 'publication', run.publication_id, Publication)
            now = self._now()
            for name, value in values.items():
                if name not in {'views', 'likes', 'comments', 'shares'} or type(value) is not int or value < 0:
                    raise ValueError('Métrica do conector inválida.')
                snapshot = MetricSnapshot(snapshot_id=str(uuid4()), publication_id=run.publication_id,
                    collection_id=collection_id, observed_at=now,
                    age_hours=(now - publication.posted_at).total_seconds() / 3600,
                    metric_name=name, metric_definition=name, value=value, source='connector',
                    quality='available', source_reference=source_reference)
                self._put(db, 'metric', snapshot.snapshot_id, snapshot)
            run.status = ('completed' if len(values) == 4 else 'partial') if values else 'failed'
            run.finished_at = now
            run.error_code = (error_code or 'metrics_unavailable') if run.status == 'failed' else None
            db.execute("UPDATE objects SET data=? WHERE kind='collection' AND id=?",
                       (run.model_dump_json(), collection_id))
            return run

    def add_manual_metric(self, publication_id, metric_name, value, reviewer):
        with self._transaction() as db:
            publication = self._get(db, 'publication', publication_id, Publication)
            observed = self._now()
            age = (observed - publication.posted_at).total_seconds() / 3600
            if age < 0:
                raise ValueError('Publicação futura não aceita métricas observadas agora.')
            snapshot = MetricSnapshot(snapshot_id=str(uuid4()), publication_id=publication_id,
                observed_at=observed, age_hours=age, metric_name=metric_name,
                metric_definition=metric_name, value=value, source='manual', quality='available',
                source_reference='manual-entry', reviewer=reviewer)
            self._put(db, 'metric', snapshot.snapshot_id, snapshot)
            return snapshot
