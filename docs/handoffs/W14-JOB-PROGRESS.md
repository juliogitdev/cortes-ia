# W14 — progresso e tempo estimado das tarefas

## Entrega

- Jobs expõem `stage_progress`, `eta_s` e `progress_at` (contrato 2.1.0). O progresso total permanece monotônico; conclusão marca 100%.
- Download, cópia/hash de arquivo, extração de áudio, transcrição por segmentos e exportação por FFmpeg informam avanço medido ao worker. A interface mostra barra total, porcentagem da etapa, previsão aproximada em minutos e horário do último sinal do worker.
- A estimativa aparece somente após avanço suficiente na etapa; durante fila ou atividades sem medida confiável, a interface informa que está calculando. A estimativa é recalculada e pode variar.
- Jobs ativos da live aparecem em um painel de acompanhamento com cancelamento; a visão geral também mostra seu progresso.
- OpenAPI e JSON Schema de Job atualizados.

## Verificação

- `python -m pytest -q`: 127 aprovados.
- `npm run build`: aprovado.
- `npm run lint`: aprovado, com avisos React anteriores à mudança.
- API 1.7.0, painel HTTP 200 e worker/scheduler ativos após reinício isolado da API e do worker. Nenhum Job estava em execução no reinício.

## Limites

- ETA é extrapolação do ritmo observado, sujeita à velocidade da rede, duração do vídeo e custo variável da inferência/codificação. Antes do primeiro avanço mensurável, não há previsão.
- Não houve download externo ou benchmark de CUDA nesta rodada; validação RTX permanece separada.
