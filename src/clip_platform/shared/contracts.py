"""Fundação dos contratos. Tempos em segundos no vídeo original [start, end)."""

from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION


class Interval(Contract):
    start_s: NonNegative
    end_s: Positive

    @model_validator(mode="after")
    def ordered(self):
        if self.end_s <= self.start_s:
            raise ValueError("end_s deve ser maior que start_s")
        return self


class MediaAsset(Contract):
    asset_id: Identifier
    source_uri: Identifier
    content_hash: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    duration_s: Positive
    tracks: list[Literal["audio", "video"]] = Field(min_length=1)
    local_path: Identifier


class ModelRun(Contract):
    run_id: Identifier
    model_version: Identifier
    rules_version: Identifier
    feature_schema: Identifier
    dataset_version: Identifier
    settings: dict[str, Any]


class Provenance(Contract):
    run_id: Identifier
    source_uri: Identifier
    artifact_hash: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    original_offset_s: NonNegative
    settings: dict[str, Any]


class Evidence(Interval):
    evidence_id: Identifier
    asset_id: Identifier
    observation: Identifier
    interpretation: str | None = None
    hypothesis: str | None = None
    provenance: Provenance


class EvidenceBundle(Contract):
    asset_id: Identifier
    transcript: list[Evidence]
    visual_events: list[Evidence]
    audio_events: list[Evidence]
    quality: list[str]
    provenance: list[Provenance] = Field(min_length=1)

    def all_evidence(self) -> list[Evidence]:
        return self.transcript + self.visual_events + self.audio_events

    @model_validator(mode="after")
    def references(self):
        evidence = self.all_evidence()
        if len({item.evidence_id for item in evidence}) != len(evidence):
            raise ValueError("evidence_id duplicado")
        if any(item.asset_id != self.asset_id for item in evidence):
            raise ValueError("evidência pertence a outra mídia")
        return self


class AnalysisRequest(Contract):
    asset_id: Identifier
    duration_mode: Literal["exact", "range"]
    target_s: Positive | None = None
    min_s: Positive | None = None
    max_s: Positive | None = None
    top_k: int = Field(ge=1, le=100)
    niche: Identifier
    instructions: str | None = None

    @model_validator(mode="after")
    def exclusive_duration(self):
        if self.duration_mode == "exact":
            if self.target_s is None or self.min_s is not None or self.max_s is not None:
                raise ValueError("exact exige somente target_s")
        elif self.target_s is not None or self.min_s is None or self.max_s is None or self.min_s > self.max_s:
            raise ValueError("range exige min_s <= max_s e nenhum target_s")
        return self


class ClipCandidate(Interval):
    candidate_id: Identifier
    asset_id: Identifier
    features: dict[str, float]
    evidence_ids: list[Identifier] = Field(min_length=1)
    reasons: list[Identifier] = Field(min_length=1)
    limitations: list[str]
    rank_score: float  # ordenação interna, nunca probabilidade
    versions: ModelRun
    duration_compliance: Literal["requested", "alternative"] = "requested"

    @model_validator(mode="after")
    def identified_alternative(self):
        if self.duration_compliance == "alternative" and not self.limitations:
            raise ValueError("alternativa exige limitação explícita")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("referência de evidência duplicada")
        return self


class AnalysisResult(Contract):
    asset: MediaAsset
    request: AnalysisRequest
    evidence: EvidenceBundle
    candidates: list[ClipCandidate]
    limitations: list[str]

    @model_validator(mode="after")
    def contextual_validation(self):
        if self.request.asset_id != self.asset.asset_id or self.evidence.asset_id != self.asset.asset_id:
            raise ValueError("asset_id inconsistente")
        items = self.evidence.all_evidence()
        by_id = {item.evidence_id: item for item in items}
        if any(item.end_s > self.asset.duration_s for item in items):
            raise ValueError("evidência fora da mídia")
        if len(self.candidates) > self.request.top_k:
            raise ValueError("resultado excede top_k")
        if len({c.candidate_id for c in self.candidates}) != len(self.candidates):
            raise ValueError("candidate_id duplicado")
        for candidate in self.candidates:
            if candidate.asset_id != self.asset.asset_id or candidate.end_s > self.asset.duration_s:
                raise ValueError("candidato fora da mídia ou asset_id incorreto")
            for evidence_id in candidate.evidence_ids:
                item = by_id.get(evidence_id)
                if item is None:
                    raise ValueError("evidência referenciada não existe")
                if item.end_s <= candidate.start_s or item.start_s >= candidate.end_s:
                    raise ValueError("evidência referenciada não sobrepõe o candidato")
            duration = candidate.end_s - candidate.start_s
            if candidate.duration_compliance == "requested":
                if self.request.duration_mode == "exact" and abs(duration - self.request.target_s) > 1e-6:
                    raise ValueError("duração exata não atendida")
                if self.request.duration_mode == "range" and not self.request.min_s <= duration <= self.request.max_s:
                    raise ValueError("duração fora da faixa")
        if not self.candidates and not self.limitations:
            raise ValueError("resultado vazio exige limitação")
        return self


class ClipRevision(Contract):
    revision_id: Identifier
    candidate_id: Identifier
    asset_id: Identifier
    boundaries: Interval
    editor_changes: list[str]
    parent_revision_id: Identifier | None = None


class Publication(Contract):
    publication_id: Identifier
    revision_id: Identifier
    platform: Identifier
    account: Identifier
    posted_at: AwareDatetime
    final_asset_id: Identifier | None = None
    publication_url: Annotated[str, Field(pattern=r"^https?://[^\s]+$")]
    external_video_id: Identifier | None = None
    editorial_status: Literal["published"] = "published"


class PublicationCollectionRun(Contract):
    collection_id: Identifier
    publication_id: Identifier
    requested_at: AwareDatetime
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None
    status: Literal["requested", "collecting", "completed", "partial", "failed"]
    connector_version: Identifier
    request_id: Identifier
    trigger: Literal["explicit_user_action"]
    error_code: Identifier | None = None

    @model_validator(mode="after")
    def lifecycle(self):
        if self.started_at and self.started_at < self.requested_at:
            raise ValueError("início anterior à solicitação")
        if self.finished_at and (not self.started_at or self.finished_at < self.started_at):
            raise ValueError("fim inválido")
        terminal = self.status in {"completed", "partial", "failed"}
        if terminal != (self.finished_at is not None):
            raise ValueError("estado terminal exige finished_at; estado ativo não pode ter fim")
        if self.status == "collecting" and self.started_at is None:
            raise ValueError("collecting exige started_at")
        if self.status == "requested" and self.started_at is not None:
            raise ValueError("requested não pode ter started_at")
        if self.status == "failed" and not self.error_code:
            raise ValueError("falha exige error_code")
        return self


class MetricSnapshot(Contract):
    snapshot_id: Identifier
    publication_id: Identifier
    collection_id: Identifier | None = None
    observed_at: AwareDatetime
    age_hours: NonNegative
    metric_name: Identifier
    metric_definition: Identifier
    value: NonNegative | None = None
    denominator: NonNegative | None = None
    source: Literal["connector", "manual"]
    quality: Literal["available", "unavailable", "estimated", "corrected"]
    source_reference: Identifier
    reviewer: Identifier | None = None

    @model_validator(mode="after")
    def availability(self):
        if self.quality == "unavailable" and self.value is not None:
            raise ValueError("métrica indisponível não pode ter valor")
        if self.quality != "unavailable" and self.value is None:
            raise ValueError("métrica disponível exige valor")
        if self.source == "connector" and not self.collection_id:
            raise ValueError("conector exige collection_id")
        if self.source == "manual" and not self.reviewer:
            raise ValueError("entrada manual exige responsável")
        return self


class PublicationRecord(Contract):
    publication: Publication
    collections: list[PublicationCollectionRun]
    snapshots: list[MetricSnapshot]

    @model_validator(mode="after")
    def contextual_validation(self):
        ids = {run.collection_id: run for run in self.collections}
        if len(ids) != len(self.collections):
            raise ValueError("collection_id duplicado")
        if sum(run.status in {"requested", "collecting"} for run in self.collections) > 1:
            raise ValueError("somente uma coleta ativa por publicação")
        if len({item.snapshot_id for item in self.snapshots}) != len(self.snapshots):
            raise ValueError("snapshot_id duplicado")
        for run in self.collections:
            if run.publication_id != self.publication.publication_id:
                raise ValueError("coleta de outra publicação")
            if run.requested_at < self.publication.posted_at:
                raise ValueError("coleta anterior à postagem")
        for snapshot in self.snapshots:
            if snapshot.publication_id != self.publication.publication_id:
                raise ValueError("snapshot de outra publicação")
            actual = (snapshot.observed_at - self.publication.posted_at).total_seconds() / 3600
            if actual < 0 or abs(snapshot.age_hours - actual) > 1e-6:
                raise ValueError("idade da postagem incorreta")
            if snapshot.source == "connector":
                run = ids.get(snapshot.collection_id)
                if run is None or run.status not in {"completed", "partial"}:
                    raise ValueError("snapshot sem coleta válida")
                if not run.started_at <= snapshot.observed_at <= run.finished_at:
                    raise ValueError("observação fora da coleta")
        return self


class Feedback(Contract):
    target_id: Identifier
    label: Literal["approved", "rejected", "preferred", "boundary_correction"]
    reason: Identifier
    comparison_target: Identifier | None = None
    reviewer: Identifier
    created_at: AwareDatetime

    @model_validator(mode="after")
    def comparison(self):
        if self.label == "preferred" and (not self.comparison_target or self.comparison_target == self.target_id):
            raise ValueError("preferência exige outro alvo")
        return self
