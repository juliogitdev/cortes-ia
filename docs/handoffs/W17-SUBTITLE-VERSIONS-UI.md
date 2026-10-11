# W17 — Interface de versões de legenda

## Entrega

- O detalhe do corte lista o MP4 original e cada versão legendada. O usuário escolhe a versão para prévia, download e uso padrão, pode voltar ao original com um clique e pode excluir uma versão legendada local.
- A galeria usa o `selected_export_id` informado pela API, mantendo o mesmo MP4 para player e download.
- A publicação TikTok individual exige escolha explícita do corte e da versão. A publicação em lote lista cada corte uma vez e exige escolher uma versão por corte, impedindo envio acidental do original e da versão legendada juntos.
- O editor de palavras e aparência continua disponível para gerar outra versão, preservando as anteriores.

## Contrato consumido

`GET /projects/{project_id}/media-versions` retorna grupos por `analysis_id` e `candidate_id`, com `selected_export_id` e variantes `{export_id, revision_id, kind, created_at, selected, available, duration_s}`. `PUT /analyses/{analysis_id}/candidates/{candidate_id}/media-selection` recebe `{export_id}` e retorna o grupo atualizado. `DELETE /analyses/{analysis_id}/candidates/{candidate_id}/media-versions/{export_id}` remove somente uma variante legendada local e retorna o grupo atualizado. Contrato confirmado com o coordenador.

## Arquivos

`frontend/src/types.ts`, `api.ts`, `App.tsx`, `components.tsx`, `TikTokPublishing.tsx`, `PublicationsPage.tsx`, `App.css`.

## Verificação

`npm run build` passou. `npm run lint` passou com avisos anteriores de `react(set-state-in-effect)`; o aviso novo introduzido nesta rodada foi removido. Fluxo real depende da API W17 em integração.

## Limites e próximo passo

As versões refletem os arquivos locais gerados; a exclusão não remove publicações no TikTok. Integrar com a API W17 e verificar no navegador seleção, reversão, exclusão local e publicação individual/em lote com a versão escolhida. O coordenador atualiza `docs/STATUS.md` após a verificação conjunta.
