"""Contratos aditivos para a fatia local da onda 1."""
from typing import Literal
from pydantic import AwareDatetime, Field
from .contracts import Contract, Identifier, NonNegative

class Project(Contract):
    schema_version: Literal['1.0.0', '1.1.0', '1.2.0'] = '1.2.0'
    project_id: Identifier
    name: Identifier
    created_at: AwareDatetime
    asset_id: Identifier | None = None
    account_open_id: Identifier | None = None
    profile_id: Identifier | None = None

class EditorialProfile(Contract):
    schema_version: Literal['1.0.0', '1.1.0'] = '1.1.0'
    profile_id: Identifier
    name: Identifier
    platforms: list[Literal['tiktok', 'instagram']] = Field(min_length=1, max_length=2)
    account_open_id: Identifier | None = None
    created_at: AwareDatetime
    tiktok_url: str = ''
    brand_name: str = ''
    avatar_version: int = 0

class ClipEditorial(Contract):
    schema_version: Literal['1.0.0', '1.1.0', '1.2.0'] = '1.2.0'
    analysis_id: Identifier
    candidate_id: Identifier
    caption: str = Field(default='', max_length=2200)
    hashtags: str = Field(default='', max_length=300)
    headline: str = Field(default='', max_length=120)
    status: Literal['draft', 'review', 'approved'] = 'draft'

class Job(Contract):
    schema_version: Literal['1.0.0', '2.0.0', '2.1.0'] = '2.1.0'
    job_id: Identifier
    project_id: Identifier
    kind: Literal['analysis', 'export', 'download']
    request_id: Identifier
    status: Literal['queued', 'running', 'completed', 'failed', 'cancelled']
    stage: str
    payload: dict
    result: dict | None = None
    error: str | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime
    progress: float | None = Field(default=None, ge=0, le=1)
    stage_progress: float | None = Field(default=None, ge=0, le=1)
    eta_s: float | None = Field(default=None, ge=0)
    progress_at: AwareDatetime | None = None
    attempts: int = Field(default=0, ge=0)

class Export(Contract):
    export_id: Identifier
    revision_id: Identifier
    asset_id: Identifier
    local_path: Identifier
    duration_s: NonNegative
    content_hash: Identifier


class MediaVariant(Contract):
    export_id: Identifier
    revision_id: Identifier
    kind: Literal['original', 'captioned']
    duration_s: NonNegative
    created_at: AwareDatetime
    selected: bool = False
    available: bool = True


class ClipMediaVariants(Contract):
    analysis_id: Identifier
    candidate_id: Identifier
    selected_export_id: Identifier | None = None
    variants: list[MediaVariant] = Field(default_factory=list)

class CandidateFeedback(Contract):
    schema_version: Literal['2.1.0'] = '2.1.0'
    feedback_id: Identifier
    analysis_id: Identifier
    candidate_id: Identifier
    rating: Literal['useful', 'not_useful']
    note: str = Field(default='', max_length=1000)
    created_at: AwareDatetime
