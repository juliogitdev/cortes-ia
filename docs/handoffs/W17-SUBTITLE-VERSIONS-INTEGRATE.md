# W17 — integração das versões de legenda

## Arquivos

`src/clip_platform/shared/jobs.py`, `services/store.py`, `worker/runner.py`, `api/app.py`, `tests/integration/test_local_flow.py`, `docs/contracts/W17-media-versions.md`, `docs/contracts/w2/openapi.json`, frontend e relato de interface em `W17-SUBTITLE-VERSIONS-UI.md`.

## Resultado

Original e renderizações legendadas são versões locais independentes. O usuário pode gerar legendas em corte antigo, editar palavras/estilo e renderizar outra versão, escolher qual pré-visualizar/baixar, voltar ao original e remover uma versão legendada. Publicação individual e em lote pede uma versão explícita para cada corte. A exclusão local não apaga post do TikTok e é bloqueada durante envio pendente.

O catálogo lê os manifestos de exportação para recuperar originais gerados antes desta atualização. Novos originais são registrados no SQLite assim que exportados.

## Verificação e limites

Teste de integração cobre original, legendado, seleção, download e remoção preservando original. Suíte Python e build/lint frontend executados na integração. Não houve postagem real no TikTok; exige aplicativo autorizado. Prévia de estilo é estática, e a sincronização é aplicada no MP4 renderizado. Gate RTX permanece pendente neste ambiente.
