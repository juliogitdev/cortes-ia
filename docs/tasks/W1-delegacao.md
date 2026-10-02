# Rodada onda 1 — notebook, 2026-10-02

Usuário confirmou que esta máquina é notebook e autorizou próximos passos; publicação GitHub no final para clone no PC.
Gate GPU fica pendente e não bloqueia desenvolvimento CPU. Leia originais, AGENTS e docs/contracts/W1-interfaces.md.
Checkout compartilhado; confirme cwd. Não alterar shared, raiz, dependências, lock, API/UI ou arquivos de outro agente.
Não criar commits. Relatos próprios em docs/handoffs; GPU e modelos de visão não fazem parte da execução desta rodada.

## W1-MEDIA — mídia
Objetivo: ingestão local, áudio e exportação reais FFmpeg/ffprobe conforme interface aprovada.
Escrita exclusiva: src/clip_platform/ingestion/**, src/clip_platform/media/**, tests/unit/test_media.py, scripts/bootstrap_media.ps1, docs/handoffs/W1-MEDIA.md.
Dependência: contratos aprovados. Pode obter FFmpeg portable em storage/tools ignorado usando fonte primária oficial e registrar origem/hash; sem instalação global.
Aceite: fixture sintética audiovisual gerada localmente, ingestão hash, limites rejeitados, corte recodificado duração tolerância 0,2 s e áudio presente; áudio PCM.
Segurança: subprocess args separados, timeout; arquivos temporários atômicos, preservar mídia original.

## W1-STORE — serviços/fila
Escrita exclusiva: src/clip_platform/services/**, tests/unit/test_store.py, docs/handoffs/W1-STORE.md.
Objetivo: implementar interface Store aprovada sem pipeline/API. SQLite WAL, idempotência, lease/fencing, cancelamento e recuperação.
Aceite: tests de dois workers, morte/reclaim, owner antigo bloqueado, idempotência payload divergente, roundtrip assets/revisões/exports e job concluído.
CPU sem modelos. Checkpoints: set_stage + resultado final; retomada pode refazer etapa de modo idempotente, não prometer cache fino.

## W1-ENGINE — fala e motor
Escrita exclusiva: src/clip_platform/speech/**, src/clip_platform/selection/**, tests/unit/test_engine.py, docs/handoffs/W1-ENGINE.md.
Objetivo: transcrição faster-whisper local (CPU notebook/CUDA explícito PC) e seleção baseline independente conforme interface.
Dependências: contratos e mídia; não alterar/download dependências, coordinator instala faster-whisper.
Aceite: timestamps originais, parâmetros backend/modelo registrados, intervalos/duração/evidências/top_k válidos; pedidos impossíveis retornam limitação.
Teste seleção com evidência sintética e falhas adapter por mock; não afirmar transcrição real até amostra/modelo autorizados executados.
Não carregar Qwen, executar GPU ou iniciar treinamento.

Coordenador: dependências, worker runner, API, painel, e2e, OpenAPI, documentação e Git.
