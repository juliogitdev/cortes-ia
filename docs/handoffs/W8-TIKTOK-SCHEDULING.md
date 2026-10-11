# W8 — Agendamento de publicações TikTok

## Entrega

O painel Resultados aceita publicação imediata de um corte e agendamento de um ou vários cortes. Um lote pode receber data/hora por vídeo ou data/hora inicial com intervalo em horas. Cada item tem legenda e visibilidade editáveis; opções de comentários, duetos e costuras são compartilhadas pelo lote. A lista mostra o horário planejado, legenda, estado e cancelamento antes do envio.

A API 1.1.0 adiciona `POST /tiktok-posts/schedule` e `POST /tiktok-posts/{attempt_id}/cancel`. O contrato `TikTokPublishAttempt` inclui `scheduled_at`, `batch_id`, opções de interação e estados `scheduled`/`cancelled`. A Store cria o lote numa transação, impede duplicação de vídeos dentro dele e bloqueia outro envio pendente do mesmo corte para a mesma conta. O agendador local reivindica um item vencido por transação SQLite e executa o envio com autorização vigente, validação do arquivo e consulta de status. `start_local.ps1` o inicia junto com API, worker e painel. Reiniciar após interrupção antes da inicialização da postagem marca a tentativa como falha para conferência manual, sem reenviar às cegas.

Exemplo: `{"batch_id":"lote-1","account_open_id":"conta-1","mode":"interval","start_at":"2026-10-04T14:00:00-03:00","interval_hours":2,"consent":true,"items":[{"revision_id":"revisao-1","export_id":"exportacao-1","caption":"Parte 1","privacy_level":"SELF_ONLY"},{"revision_id":"revisao-2","export_id":"exportacao-2","caption":"Parte 2","privacy_level":"SELF_ONLY"}]}`. O segundo vídeo será agendado para 16h no mesmo fuso, salvo internamente em UTC.

## Verificação e limites

Suite Python: 114 testes aprovados, inclusive lote atômico, consentimento, intervalo, cancelamento, não envio antecipado e execução simulada. Frontend build e lint aprovados; lint mantém avisos React preexistentes. Não houve postagem real porque não há aplicativo TikTok aprovado e conta com `video.publish` autorizada. O PC e o processo agendador precisam permanecer ligados; se estiverem desligados no horário, a fila é executada quando o agendador voltar. O TikTok não oferece horário programado na chamada de publicação direta. Confirme no TikTok eventuais envios interrompidos antes de repetir.

Próximo passo: validar uma conta autorizada em ambiente real e testar os limites de publicação da conta. Revisar experiência de lote com vídeos reais e acrescentar edição de agendamentos já salvos se necessário.
