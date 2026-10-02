# Backlog e gates de integração

Base: documentos originais v1.1, 02/10/2026. Onda 1 autorizada após usuário confirmar notebook e adiar RTX para o PC (ADR 0002).
Ondas 2–6 seguem como planejamento. Áreas/delegação W1 em W1-delegacao.md, interfaces em docs/contracts/W1-interfaces.md.
Coordenador possui shared, migrações, dependências e lockfile; nenhum agente paralelo escreve na mesma área.

Checkpoint W1: W1-00 a W1-07 integrados; W1-08 tem fluxo técnico real CPU em mídia artificial, mais testes de API/painel/fila e mídia.
Aceite editorial em uma live representativa e benchmark RTX continuam pendentes. Transcrição simulada em testes automatizados
é distinguida da prova real Whisper tiny registrada em docs/evidence. Coleta de links só na onda 2.

## Onda 0 — preparação

| ID | Entrega e dono | Dependência | Aceite e verificação | Estado |
| --- | --- | --- | --- | --- |
| W0-BASE | Coordenador: inventário, Git, estrutura e AGENTS.md | Nenhuma | Originais preservados; SO e ferramentas confirmados; delegação e áreas documentadas | Integrado |
| W0-CONTRACT | Contratos: shared, exemplos, testes e schemas | W0-BASE, Pydantic v2 | Exemplos válidos; negativos rejeitados; tempos, proveniência e coleta v1.1 cobertos | Integrado; 35 testes passaram |
| W0-PLAN | Planejamento: este backlog e evals | Originais v1.1 | Onda 1 ordenada; avaliação sem dados privados; requisito v1.1 na onda 4 | Integrado |
| W0-ENV | Ambiente: diagnóstico e instalação PowerShell | Inventário do host | Comandos reproduzíveis; nenhuma versão CUDA presumida; scripts de prova preparados | Integrado; pré-condições verificadas |
| W0-GPU | Executor reservado: fala e visão reais na RTX | NVIDIA acessível, drivers/backends verificados, amostra autorizada | Inferência CUDA de ambos os modelos; versões, tempo e pico de memória persistidos | Pendente: NVIDIA não acessível neste host |
| W0-INTEGRATE | Coordenador: verificação, decisões e STATUS | W0-CONTRACT, W0-PLAN, W0-ENV | Testes relevantes passam; instalações e próxima ação documentadas; limite GPU explícito | Integrado; gate GPU aberto |

O critério original de saída inclui smoke real. A fundação documental pode ser entregue com ressalva, mas a compatibilidade RTX continua sem validação até W0-GPU. CPU e mocks não satisfazem esse gate.

## Onda 1 — fatia local executável

Ordem: W1-00 fecha interfaces; W1-01, W1-02 e W1-03 podem preparar módulos independentes; W1-04 depende de W1-01 e prova de fala real; W1-05 depende de evidências; W1-06 liga os serviços; W1-07 só é concluída com API real; W1-08 verifica o conjunto. O painel pode ser desenhado antes com fixtures, mas esse trabalho não comprova o fluxo final.

| ID | Área exclusiva e dono | Entrada → saída | Dependência | Teste e critério de aceite |
| --- | --- | --- | --- | --- |
| W1-00 | shared/docs/contracts/migrações, coordenador | Contratos W0 → OpenAPI e contrato de Job/Export aprovados | W0-INTEGRATE | Revisão de consumidores; fixtures versionadas; progresso sem denominador fica indeterminado |
| W1-01 | ingestion e seus testes, mídia | Arquivo local autorizado → MediaAsset por hash | W1-00, ffprobe instalado | Arquivo com áudio/vídeo, inválido e ausente; metadados reais, mídia fora do Git |
| W1-02 | media e seus testes, mídia | MediaAsset + revisão → corte recodificado e metadados | W1-00, FFmpeg instalado | Fixture de marcadores; duração com tolerância proposta de 0,2 s; áudio sincronizado; limites negativos rejeitados |
| W1-03 | services/worker e seus testes, API/worker | Job → fila SQLite, checkpoints e processador simulado | W1-00 | Matar/reiniciar worker; repetir request_id; lease expirado recuperado; sem resultados duplicados |
| W1-04 | speech e seus testes, fala | MediaAsset → transcrição com offsets originais | W1-01, benchmark real de fala | Amostra PT-BR revisada; timestamps monotônicos dentro da mídia; versões/custo medidos; GPU reservada |
| W1-05 | selection e seus testes, seleção | Bundle de fala + pedido → candidatos baseline | W1-04 | Intervalos válidos, evidências existentes, exato/faixa sem ajuste silencioso, top_k sem duplicatas; baseline identificado |
| W1-06 | api e seus testes, API | Serviços integrados → endpoints locais e download | W1-02, W1-03, W1-05 | Arquivo local percorre análise/revisão/export; caminhos fora da área autorizada recusados; cancelamento e falha explícitos |
| W1-07 | ui e seus testes, painel | API → upload, etapa, cards, revisão e download | W1-06 | Painel sem import de modelos; falha recuperável visível; reprodução e download reais |
| W1-08 | tests/integration/evals, qualidade | Fluxo conjunto → relato revisado | W1-07 | Criar projeto, transcrever, escolher, ajustar, exportar e baixar; reinício sem duplicação; listar desempenho real e simulado separadamente |

Saída: arquivo reproduzível baixado pelo painel, baseline de fala declarado; não apresentar essa onda como aceite multimodal. Nicho, tolerância de tempo, duração típica e fonte dos links permanecem decisões a confirmar; arquivo local PT-BR é o ponto de partida.

## Ondas futuras — tarefas pequenas

| ID | Onda / dono / área | Dependência | Aceite e teste |
| --- | --- | --- | --- |
| W2-01 | 2, coordenador, docs/decisions | W1-08 | Escolher uma plataforma e confirmar limites de acesso sem prometer suporte universal |
| W2-02 | 2, ingestão, ingestion | W2-01 | Adaptador baixa link permitido e resolve metadados; redirecionamento interno/local recusado; sem interpolação shell |
| W2-03 | 2, API/painel, áreas atribuídas em tarefas separadas | W2-02 | Link real, timeout e retomada; upload alternativo permanece disponível |
| W3-01 | 3, visão, vision | W0-GPU, W1-08 | Primeira passagem cobre inclusive silêncio; frames/blocos e offsets persistidos; memória medida |
| W3-02 | 3, fala, speech | W1-04 | Sinais de áudio com origem e tempo; ausência de fala não elimina trecho |
| W3-03 | 3, seleção, selection | W3-01, W3-02 | Segunda passagem adaptativa, deduplicação e evidências; fronteiras sobrepostas testadas |
| W3-04 | 3, qualidade, evals | W3-03 | Comparar multimodal, baseline de fala e referência humana em lives reservadas; documentar perdas de cobertura |
| W4-00 | 4, coordenador, shared/migrações | W3-04 | Revisar contratos v1.1 e fixtures sucesso/parcial/acesso negado/erro; OpenAPI aprovado |
| W4-01 | 4, API/worker, api/worker/services | W4-00 | Cadastro/PATCH e GET fazem zero chamadas externas; POST analyze retorna job; restrição de tarefa ativa e request_id consolidam duplo clique |
| W4-02 | 4, feedback, learning/collectors | W4-00, capacidades da fonte confirmadas | Coletor com timeout/rate limit e tentativas limitadas na mesma ação; ausência não vira zero; entrada manual rastreável |
| W4-03 | 4, painel, ui | W4-00, integração W4-01/W4-02 | Botão explícito, estados editoriais separados de coleta, histórico e última coleta válida; abrir tela/progresso não coleta |
| W4-04 | 4, aprendizado, learning/collection | W4-01, W4-02 | Outbox/evento repetido não duplica exemplo; snapshot ligado à revisão/final e idade exata; nenhuma carga de modelo ou treino |
| W4-05 | 4, qualidade, tests/integration/evals | W4-03, W4-04 | Clique único; nova ação após conclusão cria snapshot; falha/parcial preserva histórico; snapshots agrupados por publicação; teste real da fonte só com ação autorizada |
| W5-01 | 5, aprendizado, learning | W4-05 | Dataset versionado e divisão por live, publicação e período; fracos preservados, não publicado não recebe zero |
| W5-02 | 5, aprendizado, learning | W5-01 | Ranking candidato comparado com estável em conjunto reservado; promoção e rollback explícitos; treino com reserva GPU |
| W5-03 | 5, qualidade, evals | W5-02 | Auditar vazamento e regressões; feedback automático não promove pesos |
| W6-01 | 6, coordenador/ingestão, áreas separadas | W5-03 | Fonte de tendências acessível, data/região/nicho e proveniência confirmados |
| W6-02 | 6, seleção/qualidade, áreas separadas | W6-01 | Ausência/desatualização explícita; medir benefício em material reservado sem inventar tendências |

O endpoint de métricas manual e o analyze de coleta têm responsabilidades distintas. Janelas 24 h, 72 h e 7 dias servem para comparação; não autorizam agendamento. Publicação em redes distintas gera registros distintos; snapshots da mesma publicação continuam no mesmo grupo de avaliação.
