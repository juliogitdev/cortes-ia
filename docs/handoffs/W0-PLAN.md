# Entrega W0-PLAN

Data: 02/10/2026. Cwd confirmado: C:/Users/Julio/Documents/cortes-ia. Checkout compartilhado, sem isolamento automático. Lidos AGENTS.md, tarefa W0-delegacao e os três documentos originais v1.1. STATUS ainda ausente na leitura inicial; consolidação pertence ao coordenador.

Arquivos criados: docs/tasks/BACKLOG.md; evals/README.md; evals/annotation.example.json; evals/run.example.json. Nenhum módulo funcional, dependência, contrato shared, mídia ou configuração raiz foi alterado. Entrega por diff local, sem commit.

O backlog detalha áreas, dependências, entradas/saídas e critérios da onda 1, incluindo ordem de integração e distinção entre mocks e fluxo real. Ondas 2–6 permanecem planejamento. O requisito v1.1 está na onda 4 com coleta só por ação, idempotência, histórico/idade real, manual, grupos sem vazamento e nenhuma atualização automática de pesos.

Verificação: parse dos dois JSON sintéticos e revisão textual das dependências/áreas. Comando reproduzível: `python -c "import json,pathlib; [json.loads(p.read_text(encoding='utf-8')) for p in pathlib.Path('evals').glob('*.json')]; print('2 templates JSON validos')"`. Não executado benchmark, GPU, teste de qualidade editorial ou software de produto; esses resultados não são inferidos do parse.

Limitações: nicho, fonte inicial dos links, mídia autorizada, tolerância de processamento e capacidades dos conectores ainda exigem definição. NVIDIA não acessível segundo inventário do coordenador; W0-GPU pendente. Fundação entregue com ressalva não satisfaz o gate original de smoke real.

Próximo passo: coordenador revisar, integrar e atualizar STATUS; reservar W0-GPU no host RTX quando acessível. Antes de onda 1 fechar contrato Job/Export/OpenAPI e preparar fixture audiovisual autorizada.
