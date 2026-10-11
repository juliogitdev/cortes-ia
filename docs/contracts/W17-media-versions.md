# W17 — versões locais de um corte

O MP4 original exportado permanece disponível. Cada renderização de legenda cria outro MP4 e outro `export_id`; a seleção atual é metadado local, sem alterar os arquivos anteriores. Os horários das palavras continuam em segundos da gravação original, início inclusivo e fim exclusivo.

## API 2.0.0

- `GET /projects/{project_id}/media-versions`: grupos de versões dos cortes da live.
- `GET /analyses/{analysis_id}/candidates/{candidate_id}/media-versions`: um grupo.
- `PUT /analyses/{analysis_id}/candidates/{candidate_id}/media-selection` com `{"export_id":"..."}`: escolhe versão para prévia/download no painel.
- `DELETE /analyses/{analysis_id}/candidates/{candidate_id}/media-versions/{export_id}`: remove somente MP4, manifesto e capa da versão legendada local. Preserva original e publicações externas. Bloqueia versão com envio pendente.
- `GET /exports/{export_id}/download`: baixa a versão escolhida pelo identificador explícito.

Exemplo de grupo:

```json
{
  "schema_version": "1.0.0",
  "analysis_id": "analysis-1",
  "candidate_id": "candidate-1",
  "selected_export_id": "export-subtitle-1",
  "variants": [
    {"schema_version":"1.0.0","export_id":"export-subtitle-1","revision_id":"revision-1","kind":"captioned","duration_s":30,"created_at":"2026-10-03T12:00:00Z","selected":true,"available":true},
    {"schema_version":"1.0.0","export_id":"export-original-1","revision_id":"revision-1","kind":"original","duration_s":30,"created_at":"2026-10-03T11:00:00Z","selected":false,"available":true}
  ]
}
```

Publicação individual ou em lote recebe `revision_id` e `export_id` da versão selecionada explicitamente pelo usuário. Escolher original no painel não muda automaticamente um agendamento já criado.
