# W1-00 — interfaces aprovadas

Contratos aditivos em shared/jobs.py; contratos 1.0.0 existentes preservados. SQLite e arquivos sob storage.
Backend padrão CPU para notebook, CUDA explícito no PC; nunca fallback silencioso. Baseline apenas fala.

## Interface de mídia (W1-MEDIA)
`ingestion.local.ingest_file(path: Path, destination_dir: Path) -> MediaAsset`: copiar por hash para área autorizada; ffprobe real, áudio e vídeo.
`media.tools.find_tool(name: str) -> str`: PATH/env CLIP_FFMPEG/CLIP_FFPROBE, depois storage/tools; erro claro se indisponível.
`media.export.export_clip(asset: MediaAsset, revision: ClipRevision, destination_dir: Path) -> Export`: recodificar, validar limites/duração, sem shell.
`media.audio.extract_audio(asset: MediaAsset, output: Path) -> Path`: PCM 16 kHz mono.
Estas funções não consultam banco nem reservam GPU; CPU FFmpeg.

## Interface de persistência (W1-STORE)
`services.store.Store(root: Path)` usa root como armazenamento; `.root` é Path absoluto.
`create_project(name) -> Project`; `list_projects() -> list[Project]`; `get_project(id) -> Project`.
`put_asset(project_id, asset)`, `get_asset(asset_id) -> MediaAsset`.
`enqueue(project_id, kind, request_id, payload) -> Job`: chave única (project_id,kind,request_id), payload diferente mesma chave é ValueError.
`get_job(job_id) -> Job`; `claim(owner, lease_s=60) -> Job | None`; `heartbeat(job_id, owner, lease_s=60)`.
`set_stage(job_id, owner, stage)`; `finish(job_id, owner, result)`; `fail(job_id, owner, error)`; `cancel(job_id)`.
`release(job_id,owner)` após encerramento real do executor. cancel/finish/fail conservam a reserva até release ou expiração;
claim considera reservas vivas mesmo em jobs terminais. Lock de processo no worker impede dois executores pesados,
inclusive se o lease expirar enquanto um filho órfão ainda processa.
`put_revision(revision)`, `get_revision(id) -> ClipRevision`; `put_export(export)`, `get_export(id) -> Export`.
`get_analysis(job_id) -> AnalysisResult`: retorna job analysis concluído validado.
Um job running por vez no checkout (inclui modelos/export); leases e fencing de owner impedem worker antigo concluir após retomada.
JSON no SQLite, transações curtas/WAL; métodos retornam objetos validados. KeyError ausente, ValueError transição inválida.

## Fala/seleção (W1-ENGINE)
`speech.transcribe.transcribe(asset: MediaAsset, audio_path: Path, model_path: str, device='cpu') -> EvidenceBundle`: faster-whisper local_files_only, CPU int8/CUDA float16, palavras/segments com offsets; nada baixa implicitamente.
`selection.baseline.select(asset: MediaAsset, evidence: EvidenceBundle, request: AnalysisRequest) -> AnalysisResult`: independente de downloader/UI; heurística determinística, justificativa verificável, nenhum significado probabilístico.

## API/painel (coordenador)
Factory `api.app.create_app(storage_root=None)`; bind somente 127.0.0.1.
POST/GET /projects; POST /projects/{id}/upload multipart; POST /projects/{id}/analyses (AnalysisRequest e header Idempotency-Key obrigatório); GET /jobs/{id}; POST /jobs/{id}/cancel;
GET /analyses/{id}/candidates (AnalysisResult); POST /candidates/{id}/revisions (analysis_id,start_s,end_s,editor_changes);
POST /revisions/{id}/exports (Idempotency-Key obrigatório); GET /exports/{id}/download.
GET /assets/{id}/media serve só arquivo cadastrado sob root. Sem links externos ou publicação nesta onda.
Painel consome API por HTTP, nunca importa modelos/store. Worker separado recebe model_path/device explícitos.
OpenAPI será gerado e congelado antes da integração do painel.
