"""SQLite local, fila serial e leases; owner é único por execução do worker."""
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from clip_platform.shared.contracts import AnalysisResult, ClipRevision, MediaAsset
from clip_platform.shared.jobs import Export, Job, Project


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

    def create_project(self, name):
        project = Project(project_id=str(uuid4()), name=name, created_at=self._now())
        with self._transaction() as db:
            self._put(db, "project", project.project_id, project)
        return project

    def list_projects(self):
        with closing(self._connect()) as db:
            return [Project.model_validate_json(row["data"]) for row in db.execute("SELECT data FROM objects WHERE kind='project' ORDER BY rowid")]

    def get_project(self, project_id):
        with closing(self._connect()) as db:
            return self._get(db, "project", project_id, Project)

    def put_asset(self, project_id, asset):
        asset = MediaAsset.model_validate(asset)
        with self._transaction() as db:
            project = self._get(db, "project", project_id, Project)
            self._put(db, "asset", asset.asset_id, asset)
            project.asset_id = asset.asset_id
            db.execute("UPDATE objects SET data=? WHERE kind='project' AND id=?", (project.model_dump_json(), project_id))

    def get_asset(self, asset_id):
        with closing(self._connect()) as db:
            return self._get(db, "asset", asset_id, MediaAsset)

    def enqueue(self, project_id, kind, request_id, payload):
        canonical = self._encode(payload)
        with self._transaction() as db:
            self._get(db, "project", project_id, Project)
            row = db.execute("SELECT * FROM jobs WHERE project_id=? AND kind=? AND request_id=?", (project_id, kind, request_id)).fetchone()
            if row:
                if row["payload"] != canonical:
                    raise ValueError("chave de idempotência com payload divergente")
                return Job.model_validate_json(row["data"])
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
            self._get(db, 'project', project_id, Project)
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

    def _complete(self, job_id, owner, status, result=None, error=None):
        with self._transaction() as db:
            job = self._owned(db, job_id, owner)
            if status == "completed":
                model = AnalysisResult if job.kind == "analysis" else Export
                validated = model.model_validate(result)
                result = validated.model_dump(mode="json")
                if job.kind == "export":
                    revision = self._get(db, "revision", validated.revision_id, ClipRevision)
                    if revision.asset_id != validated.asset_id:
                        raise ValueError("export de outra mídia")
                    if job.payload.get("revision_id") not in {None, validated.revision_id}:
                        raise ValueError("export de outra revisão")
                    self._put(db, "export", validated.export_id, validated)
                else:
                    if job.payload.get("asset_id") not in {None, validated.asset.asset_id}:
                        raise ValueError("análise de outra mídia")
            job.status = status
            job.stage = status
            job.result = result
            job.error = error
            job.updated_at = self._now()
            db.execute("UPDATE jobs SET data=? WHERE id=?", (job.model_dump_json(), job_id))

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
            return self._get(db, "export", export_id, Export)

    def get_analysis(self, job_id):
        job = self.get_job(job_id)
        if job.kind != "analysis" or job.status != "completed":
            raise ValueError("análise ainda não concluída")
        return AnalysisResult.model_validate(job.result)
