# W9 — Contas, lives e métricas após vínculo manual

## Entrega

A entrada do painel agora é **Contas TikTok**. Cada conta abre suas lives; uma pasta separada reúne lives ainda sem conta. Abrir uma live leva ao estúdio com todos os seus cortes. A associação da conta pode ser feita no cartão da live ou em **Publicar e acompanhar**. A API persiste `Project.account_open_id` e impede trocar uma live para outra conta quando ela já contém publicação vinculada ou envio pendente nessa conta. Dados antigos continuam legíveis; o contrato Project passa a aceitar 1.0.0 e a produzir 1.1.0. OpenAPI 1.2.0.

O estúdio aponta para **Publicar e resultados**. Publicação imediata e agendada aparecem sempre; sem conta vinculada à pasta, os controles ficam bloqueados com a razão. `video.publish` libera envio; `video.list` libera busca de posts próprios e métricas. O histórico de envios e publicações é exibido no contexto da live.

Ao vincular manualmente um corte a um post TikTok, o POST de criação inicia a coleta apenas daquele post. Se o usuário omitir a data de postagem, a aplicação consulta `create_time` junto com visualizações, curtidas, comentários e compartilhamentos; registra data e métricas com proveniência numa única consulta. Se a data vier do formulário ou do seletor de vídeos, a coleta roda após o cadastro. Falhas de consulta ficam no histórico, sem pedir números manuais no painel. GET de publicações e abertura da página não acionam coleta. A consulta já existente ao iniciar sessão continua separada. A associação de uma publicação legada à conta da live também inicia consulta explícita.

## Verificação

Testes de integração cobrem ausência de coleta em GET, coleta automática após vínculo, preenchimento da data pelo TikTok, bloqueio sem `video.list`, URL inválida, associação de pasta e impedimento de troca de conta com publicação. Suite Python: 116 testes aprovados. Frontend build e lint aprovados; lint conserva avisos React sem falhas. Nenhuma consulta ou publicação real ocorreu, pois a conta TikTok e o aplicativo ainda não estão autorizados neste ambiente. Teste visual servido não foi feito porque o usuário pediu que aplicação e túnel permaneçam desligados.

## Limites e próximo passo

O link aceito para coleta deve ser o link completo `https://www.tiktok.com/@perfil/video/ID`; links curtos exigem escolher o vídeo no seletor ou obter o endereço completo. TikTok Display API exige `video.list` e consulta somente posts da conta autorizada. Vinculação e postagem reais precisam de aplicativo aprovado e autorização da conta. Após essa configuração, validar a jornada no navegador com uma live e um post reais, incluindo a responsividade da nova hierarquia.
