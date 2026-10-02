# Contratos de fundação

Versão de schema: **1.0.0**. Documentos de produto: v1.1. Estes números têm ciclos distintos.
Fonte executável: `src/clip_platform/shared/contracts.py`. JSON Schemas e exemplos sintéticos em `v1/`.
Não há inferência, coleta externa, fila ou persistência nesta entrega.

`AnalysisRequest` representa entrada do motor; `AnalysisResult` é o envelope contextual de saída.
O envelope deve ser validado antes de promover propostas de modelos: confere mídia, duração,
identificadores, evidências existentes e sobreposição temporal. Tempos são segundos no original,
com início inclusivo e fim exclusivo. `original_offset_s` guarda a origem de trechos processados;
os adaptadores da próxima onda devem converter horários locais antes de construir evidências.
Uma evidência que sobrepõe o corte não prova semanticamente o motivo: revisão humana e avaliação
de qualidade continuam necessárias. `rank_score` é apenas ordenação, sem escala probabilística.
Alternativas à duração solicitada exigem `duration_compliance=alternative` e limitação visível.

`PublicationRecord` valida coleta e snapshots da mesma publicação, idade real e instante de
observação. Há campos de observação, interpretação e hipótese separados nas evidências.
Entrada manual exige responsável e referência de origem. Indisponibilidade conserva `value=null`.
O exemplo parcial representa coleta às 48 h + 2 s; não é resultado de 24 h.
O contrato exige ação explícita no registro de coleta, mas só testes de serviços na onda 4
poderão provar ausência de consultas em GET, idempotência e ausência de treino automático.

IDs e vínculos de revisão/candidato/publicação devem ser resolvidos pelo armazenamento nas ondas
seguintes; schemas individuais não consultam banco. Revisões não sobrescrevem candidatos.
URLs e caminhos são dados; o schema não autoriza acesso a arquivos nem protege contra SSRF.
Essa validação pertence aos adaptadores e serviços. Textos das fixtures e modelos nunca são comandos.

Consumidores previstos: ingestão/mídia produz `MediaAsset`; fala/visão produzem `EvidenceBundle`;
seleção consome pedido e evidências; API/painel consomem saída e revisões; aprendizado consome
publicações, snapshots e feedback. Alterações exigem coordenador, versão, fixtures e revisão dos
consumidores. JSON Schemas devem ser regenerados quando o schema executável mudar.

Verificação: `.\.venv\Scripts\python.exe -m pytest tests/contract -q`.
