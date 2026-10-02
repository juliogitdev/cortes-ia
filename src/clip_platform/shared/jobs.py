"""Contratos aditivos para a fatia local da onda 1."""
from typing import Literal
from pydantic import AwareDatetime, Field
from .contracts import Contract, Identifier, NonNegative

class Project(Contract):
    project_id: Identifier
    name: Identifier
    created_at: AwareDatetime
    asset_id: Identifier | None = None

class Job(Contract):
    job_id: Identifier
    project_id: Identifier
    kind: Literal['analysis', 'export']
    request_id: Identifier
    status: Literal['queued', 'running', 'completed', 'failed', 'cancelled']
    stage: str
    payload: dict
    result: dict | None = None
    error: str | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    progress: float | None = Field(default=None, ge=0, le=1)
    attempts: int = Field(default=0, ge=0)

class Export(Contract):
    export_id: Identifier
    revision_id: Identifier
    asset_id: Identifier
    local_path: Identifier
    duration_s: NonNegative
    content_hash: Identifier
