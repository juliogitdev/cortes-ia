# Plano de desenvolvimento da plataforma de cortes

Arquitetura modular e execução com multiagentes no Codex

Responsável pelo produto: Júlio César
Versão 1.1 | 2 de outubro de 2026

## 1 Direção técnica

Implementar uma aplicação local com painel visual e um motor de seleção utilizável isoladamente. O desenvolvimento começa por contratos de dados, validação do hardware e uma fatia completa pequena. Os agentes trabalham em módulos delimitados; a integração acontece a cada entrega, não somente no final.

O Codex coordena o desenvolvimento e usa modelos disponíveis na conta. A aplicação executa os modelos de análise localmente na RTX 5060. O consumo de Codex e o processamento local são recursos diferentes. A arquitetura inicial não depende de uma API paga de inferência para analisar as lives.

## 2 Componentes e stack proposta

| Componente | Escolha inicial | Fronteira |
| --- | --- | --- |
| Painel | Streamlit | Consome API sem carregar modelos |
| API e serviços | FastAPI e Pydantic | Projetos tarefas resultados e download |
| Persistência | SQLite e arquivos locais | Metadados no banco mídia fora do banco |
| Execução | Worker em processo separado | Fila persistida checkpoints e reserva de GPU |
| Ingestão | yt-dlp e upload | Adaptadores por fonte |
| Mídia | FFmpeg e ffprobe | Extração proxies validação e cortes |
| Fala | faster-whisper | Modelo multilíngue escolhido por benchmark |
| Imagem e texto | Qwen3-VL compacto | Adaptador substituível com saída validada |
| Aprendizado | Ranking pequeno e coleção de exemplos | Treinamento separado da inferência |

A API evita acoplar os modelos ao painel e permite trocar a interface posteriormente. Redis, microsserviços distribuídos e orquestração em nuvem não são requisitos da primeira versão. O worker usa a mesma camada de serviços da API; workers não dependem de funções internas do painel.

faster-whisper oferece execução CUDA e timestamps por palavra [1]. Qwen3-VL é um candidato para entendimento visual e textual [2], não um modelo pronto de previsão de viralização. A escolha final depende do teste na RTX; drivers, backend e bibliotecas devem suportar efetivamente a arquitetura da placa. Não basta a instalação reconhecer o nome da GPU.

---

## 3 Contratos de dados

Um pacote shared define schemas Pydantic e exemplos JSON versionados. Todos os tempos são segundos decimais no vídeo original; início é inclusivo e fim exclusivo. Exibição HH MM SS é responsabilidade da interface. Tokens de modelos nunca são usados como relógio da gravação.

| Contrato | Campos mínimos |
| --- | --- |
| MediaAsset | asset_id source_uri content_hash duration_s tracks local_path |
| EvidenceBundle | schema_version asset_id transcript visual_events audio_events quality provenance |
| AnalysisRequest | asset_id duration_mode target_s min_s max_s top_k niche instructions |
| ClipCandidate | candidate_id start_s end_s features evidence_ids reasons limitations rank_score versions |
| ClipRevision | revision_id candidate_id boundaries editor_changes parent_revision_id |
| Publication | publication_id revision_id platform account posted_at final_asset_id |
| MetricSnapshot | publication_id observed_at age_hours metric_name value denominator source |
| Feedback | target_id label reason comparison_target reviewer created_at |
| ModelRun | run_id model_version rules_version feature_schema dataset_version settings |

Exemplo de saída simplificada do motor, com valores apenas ilustrativos:

```json
{
  "schema_version": "1.0",
  "asset_id": "asset_exemplo",
  "candidates": [{
    "candidate_id": "corte_exemplo",
    "start_s": 4348.0,
    "end_s": 4378.0,
    "rank_score": 0.82,
    "evidence_ids": ["fala_18", "evento_9"],
    "reasons": ["A pergunta recebe uma resposta inesperada"],
    "limitations": ["Nome mencionado depende de contexto"],
    "model_version": "baseline_1",
    "rules_version": "regras_1"
  }]
}
```

rank_score é apenas ordenação interna sem interpretação probabilística. Evidências referenciadas devem existir e cobrir o acontecimento descrito. Erros de schema, campos faltantes e intervalos fora da mídia impedem a promoção do resultado para concluído.

Artefatos imutáveis são identificados por hash e versão. O cache combina conteúdo, etapa, modelo, configuração e schema. Alterar regras de ranking não invalida o download; alterar o modelo de transcrição invalida os consumidores afetados. Revisões não sobrescrevem a análise que motivou a publicação.

---

## 4 Motor independente e execução

O motor recebe EvidenceBundle e AnalysisRequest e retorna candidatos validados. Sua extração multimodal pode ser executada separadamente: uma entrada alternativa por mídia chama os adaptadores e produz o mesmo bundle. O pacote do motor não importa o painel, o downloader ou o gerador de cortes.

Ele contém entendimento, geração de candidatos, ranking e validação. Mantém evidências observadas separadas das interpretações e hipóteses. Saídas de modelos são tratadas como propostas e passam por validação determinística. Textos presentes no vídeo são conteúdo a analisar, não instruções para executar ferramentas.

A primeira passagem cobre toda a mídia com blocos sobrepostos e amostragem visual. A segunda revisita regiões promissoras e duvidosas com maior densidade. Parâmetros iniciais são configuráveis; sua escolha deve considerar recall dos acontecimentos, custo e resolução. Um sistema baseado só na fala é baseline de comparação, não aceite final multimodal.

## 5 Tarefas e recursos

Estados operacionais: recebido, validando, baixando, preparando, transcrevendo, analisando, selecionando, concluído, falhou e cancelado. Geração de corte é outra tarefa com estados próprios. Progresso porcentual aparece somente quando há denominador confiável; caso contrário, mostrar etapa e duração transcorrida.

O worker reserva a GPU para uma tarefa pesada por vez, incluindo treinamento. A reserva tem lease e heartbeat para recuperação após falha. Cada etapa grava checkpoint e resultado atomicamente. Repetir uma tarefa usa chave de idempotência e não cria candidatos duplicados. API e worker usam transações curtas; SQLite pode operar em WAL, com contenção medida.

As mídias são escritas em diretórios por projeto e análise. Trechos locais mantêm offset para conversão ao relógio original. O corte preciso usa recodificação e verifica duração e sincronização; cópia direta só é oferecida quando a imprecisão de quadros chave for aceitável e informada.

## 6 API e armazenamento

Endpoints propostos: POST /projects; POST /projects/{id}/analyses; GET /jobs/{id}; GET /analyses/{id}/candidates; POST /candidates/{id}/revisions; POST /revisions/{id}/exports; GET /exports/{id}/download; POST /publications; POST /publications/{id}/metrics; POST /feedback. O coordenador consolida o OpenAPI antes da implementação paralela.

O banco guarda projetos, artefatos, execuções, candidatos, revisões, publicações, métricas, feedback e versões. A API serve apenas caminhos autorizados do projeto. Links de entrada não podem acessar endereços internos ou locais por redirecionamento; processos externos recebem argumentos separados, nunca comandos interpolados. Credenciais de fontes, se necessárias, ficam fora do Git e dos logs. Arquivos grandes e pesos também ficam fora do repositório.

---

## 7 Papéis dos agentes

São nove papéis lógicos, ativados por necessidade. Começar com até três agentes executores simultâneos, além do coordenador se a sessão permitir. Nove papéis não implicam nove sessões ativas.

| Papel | Responsabilidade | Área principal |
| --- | --- | --- |
| Coordenador | Contratos backlog dependências integração | shared docs arquitetura configuração raiz |
| Ingestão e mídia | Fontes preparação proxies cortes | ingestion media |
| Fala e áudio | Transcrição alinhamento sinais sonoros | speech |
| Visão e contexto | Eventos visuais e entendimento temporal | vision |
| Motor de seleção | Candidatos ranking regras validação | selection |
| Feedback e aprendizado | Métricas referências experimentos treino | learning |
| API e worker | Persistência fila checkpoints GPU | services api worker |
| Painel | Jornada players formulários downloads | ui |
| Qualidade | Contratos regressão avaliação integração | tests evals |

Cada responsável escreve testes do próprio módulo. Qualidade revisa de forma independente e mede a cadeia inteira. Arquivos compartilhados, migrações, dependências e lockfile têm um responsável único por rodada. Alterações de contrato passam pelo coordenador e incluem exemplo, compatibilidade e consumidores afetados.

Estrutura proposta: src/clip_platform com shared, ingestion, media, speech, vision, selection, learning, services, api, worker e ui; tests separados em unit, contract e integration; evals para avaliação humana e modelos; docs para decisões, tarefas e relatos. storage e models são diretórios locais ignorados pelo Git.

## 8 Ondas de desenvolvimento

| Onda | Trabalho | Critério de saída |
| --- | --- | --- |
| 0 Fundação | Schemas ambiente GPU amostras e backlog | Smoke test real e exemplos de contratos aprovados |
| 1 Fatia completa | Arquivo local baseline de fala API corte painel | Trecho reproduzível baixado pelo painel |
| 2 Entrada por link | Adaptador da plataforma inicial metadados recuperação | Link real mais upload alternativo funcionando |
| 3 Multimodal | Cobertura visual áudio contexto e candidatos | Avaliação por live e falhas documentadas |
| 4 Feedback | Publicações revisões métricas correções | Resultado rastreável ao vídeo final e à hipótese |
| 5 Aprendizado | Ranking treino avaliação promoção rollback | Versão candidata avaliada sem vazamento |
| 6 Tendências | Fonte disponível datas relevância por nicho | Dados atuais rastreáveis e ausência bem tratada |

As ondas têm checkpoints; não há prazo fechado antes do benchmark. O primeiro fluxo usável pode preceder aprendizado e tendências. Entre as ondas, o coordenador integra e valida antes de liberar consumidores dependentes.

---

## 9 Colaboração e integração

O coordenador atribui tarefa com objetivo, arquivos permitidos, contratos, dependências, critérios de aceite e orçamento de recursos. Os agentes comunicam bloqueios e pedidos de alteração por mensagens na sessão, quando suportadas, e registram decisões em documentos versionados.

Em checkout compartilhado, nenhum agente reverte mudanças de outro nem altera a mesma área simultaneamente. Em worktrees, cada tarefa mutável usa branch própria e base comum; dados e pesos permanecem fora das cópias. Worktrees não sincronizam automaticamente alterações de contratos ou mensagens entre chats independentes. O coordenador encaminha relatos e integra commits.

O relato de entrega inclui tarefa, commit ou diff, contratos usados, testes executados, resultados, limitações e instruções de integração. O coordenador verifica o diff, incorpora em ordem de dependência e roda testes de contrato e uma fatia completa. Qualidade revisa o estado integrado, não apenas branches isoladas. Conflitos voltam ao responsável do módulo com o contexto dos dois lados.

## 10 Avaliação e aprendizado

O conjunto inicial inclui conversa, gameplay com pouca fala, ruído, silêncio e acontecimentos em fronteiras de blocos. Um subconjunto tem transcrição revisada e momentos marcados pelo usuário. Medir erro de palavras em amostras, erro temporal, cobertura visual, recall de candidatos, aproveitamento dos primeiros cinco e ajustes de limites.

Meta inicial proposta: em média três cortes aproveitáveis entre os cinco primeiros. Para exportações recodificadas, testar duração com tolerância inicial de 0,2 s e sincronização em amostras; tolerâncias devem ser confirmadas no benchmark. Registrar tempo por etapa, pico de VRAM, RAM e disco. Comparar com seleção por transcrição e candidatos humanos.

O ranking começa com preferências humanas e métricas normalizadas por perfil, plataforma e janela. Separar conjuntos por live, publicação duplicada e período. Dados futuros da mesma publicação não podem entrar em uma avaliação passada. Exemplos fracos devem permanecer; ausência de publicação não equivale a desempenho ruim.

Treinamento usa dataset e configuração versionados e não acontece a cada métrica recebida. Nova versão é avaliada em material posterior ou reservado e só substitui a estável quando há benefício sem regressões relevantes. Recuperar a versão anterior deve ser uma operação simples. LoRA e estratégias de exploração são evoluções condicionadas à quantidade e qualidade dos dados.

## 11 Definição de entrega concluída

Uma tarefa está concluída quando o código está integrado, os contratos permanecem válidos, os testes relevantes passaram, a documentação operacional foi atualizada e o fluxo real foi verificado. Um mock comprova integração de interfaces, mas não comprova desempenho na RTX, qualidade de transcrição ou qualidade dos cortes. Esses limites são relatados explicitamente.

## 12 Referências técnicas

[1] SYSTRAN. faster-whisper. https://github.com/SYSTRAN/faster-whisper
[2] Qwen. Qwen3-VL-4B-Instruct. https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct
[3] yt-dlp. Documentação e fontes suportadas. https://github.com/yt-dlp/yt-dlp
[4] OpenAI. Subagents e Git worktrees. https://learn.chatgpt.com/docs/agent-configuration/subagents e https://learn.chatgpt.com/docs/environments/git-worktrees

Fontes consultadas em 02/10/2026. Stack, endpoints e distribuição de tarefas são propostas deste projeto; versões concretas serão fixadas depois do teste técnico.

---

## 13 Implementação da análise de publicação

A onda 4 inclui cadastro de link, botão Analisar publicação, tarefa de coleta externa e histórico de snapshots. O conector inicial atende à plataforma definida na fundação; conectores adicionais entram depois. Se a fonte não oferecer dados acessíveis, o fluxo manual deve funcionar sem bloquear o cadastro nem simular métricas.

Publication passa a incluir publication_url, external_video_id quando resolvido, editorial_status, account, platform, posted_at e revisão publicada. PublicationCollectionRun inclui collection_id, publication_id, requested_at, started_at, finished_at, status, connector_version, request_id e error_code. MetricSnapshot mantém a ligação com collection_id, instante real de observação, idade da publicação, fonte, definição da métrica e indicador de qualidade. Campos não disponíveis são ausentes ou nulos, nunca zero por conveniência.

Endpoints adicionais propostos: PATCH /publications/{id} para cadastrar ou corrigir o link; POST /publications/{id}/analyze para iniciar a coleta; GET /publications/{id}/collections para tentativas; GET /publications/{id}/metrics para histórico. O POST retorna o identificador da tarefa; o acompanhamento usa GET /jobs/{id} sem chamar o conector externo novamente. Nenhum GET de tela inicia coleta.

O conector em learning/collectors recebe identidade da publicação e acesso autorizado quando necessário, consulta a fonte, normaliza os dados e informa limitações. A API valida os dados de entrada; o worker executa com timeout, limites de tentativas e tratamento de rate limit. Retentativas limitadas pertencem à mesma solicitação explícita; não viram monitoramento de fundo. Sem acesso autorizado, encaminhar o usuário ao registro manual.

| Agente | Entrega específica |
| --- | --- |
| Feedback e aprendizado | Conector normalização snapshots e preparação dos dados |
| API e worker | Endpoint tarefa idempotência estados e persistência |
| Painel | Link botão última coleta histórico erros e entrada manual |
| Coordenador | Schemas migração contrato da tarefa e integração |
| Qualidade | Verificar acionamento exclusivo por clique e fluxo completo |

Uma restrição de tarefa ativa por publicação evita consultas simultâneas. Idempotência da solicitação impede repetição do mesmo snapshot por falha de resposta ou duplo clique. Uma ação posterior deliberada pode gerar outro snapshot. O armazenamento preserva o resultado anterior e registra falhas separadamente; coleta parcial não apaga métricas antigas nem as apresenta como atuais.

Após persistir um snapshot validado, um evento interno ou outbox idempotente informa ao módulo de aprendizado que há feedback disponível. O consumidor atualiza a coleção e o estado de elegibilidade, sem carregar modelos na GPU nem iniciar treino. Métricas parciais podem ser elegíveis para análises específicas; o motivo de exclusão ou uso é registrado. Não presumir evidência suficiente para inferir a causa do desempenho.

Testes obrigatórios: cadastro e abertura da tela fazem zero consultas externas; um clique cria uma tarefa; duplo clique em andamento é consolidado; sucesso acrescenta histórico; falha conserva dados anteriores; campos ausentes não são zero; dado manual identifica sua origem; evento repetido não duplica exemplo; snapshots da mesma publicação ficam no mesmo grupo de treino e avaliação; a coleta não dispara treinamento. Testes de contrato usam conector simulado, e um teste autorizado real confirma as capacidades da fonte escolhida.
