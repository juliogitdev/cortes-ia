# W7 — Vínculo manual e automático de vídeos TikTok

Data: 2026-10-02. Implementador: sessão principal. Checkout compartilhado confirmado. Aplicação e túnel desligados durante a edição.

## Entrega

- **Manual:** em Resultados, o usuário escolhe um corte exportado e uma conta TikTok autorizada, clica para listar vídeos públicos (`video.list`) e seleciona o post correspondente. A seleção preenche link e data quando disponíveis; o usuário confirma o registro. Publicações criadas assim recebem `link_type=manual`. Cadastro e GET continuam sem consultas externas.
- **Automático:** uma conta com `video.publish` pode consultar opções atuais de publicação, escolher privacidade/interações, preencher legenda e confirmar explicitamente o envio de um corte exportado. O servidor usa Direct Post com `FILE_UPLOAD` em blocos, guarda `publish_id`, acompanha o status e cria a publicação com `link_type=automatic` quando o TikTok confirma `PUBLISH_COMPLETE`. O ID público pode chegar depois da moderação; o vínculo pelo `publish_id` já fica persistido. Há consulta de status por ação explícita para casos demorados.
- O painel exibe vínculo manual ou automático por publicação, estado de cada envio, conta e erros. Publicações automáticas não permitem trocar a conta de origem. Métricas podem usar o ID público mesmo quando o TikTok ainda não forneceu URL compartilhável.
- Contratos: API 1.0.0, `Publication.link_type`/`publish_id` e URL opcional para vínculo automático; `TikTokPublishAttempt` para histórico. OpenAPI, exemplos e consumidores React atualizados.
- O proxy Vite encaminha as rotas de publicação também no painel local.

## Limites e cuidado operacional

Nenhum vídeo real foi publicado nesta entrega: ainda não há aplicativo TikTok configurado nem conta autorizada. O envio só ocorre após confirmação do operador, sem publicação automática de cortes. A API oficial exige `video.publish` aprovado e consentido pela conta; aplicativos não auditados podem ter visibilidade restrita. A listagem manual retorna apenas vídeos públicos da conta. O TikTok pode atrasar o ID público durante a moderação; nesse período a publicação automática fica vinculada ao corte, porém a consulta de métricas aguarda esse ID. O acompanhamento em segundo plano tenta por cerca de dois minutos; se o processamento durar mais ou a API reiniciar, o botão Verificar status retoma a consulta. Para uma versão SaaS, o acompanhamento persistente deve migrar para um worker próprio.

O upload usa somente URLs HTTPS de hosts de upload do TikTok, sem redirecionamentos. Os blocos são enviados em sequência, com tamanho e intervalo validados. O arquivo é lido de uma exportação autorizada dentro do armazenamento da aplicação. Uma falha após o TikTok aceitar o envio pode deixar a publicação em andamento; antes de tentar publicar de novo, consulte o estado no TikTok para evitar duplicação.

## Verificação

113 testes Python passaram; build TypeScript e lint passaram, com avisos React de efeitos. Navegador Edge validou Resultados localmente e pelo túnel: integração e publicações responderam 200, `/tiktok-posts` retornou JSON e não houve erro JavaScript. Testes simulados cobrem listagem manual, opções da conta, inicialização de publicação, envio do arquivo, status, URL de upload maliciosa, consentimento obrigatório, idempotência e criação de vínculo automático. A validação com a API real continua pendente das permissões do TikTok.

Fontes oficiais: https://developers.tiktok.com/docs/en/tiktok-api-v2-video-list ; https://developers.tiktok.com/docs/en/content-posting-api-reference-query-creator-info ; https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post ; https://developers.tiktok.com/docs/en/content-posting-api-media-transfer-guide ; https://developers.tiktok.com/docs/en/content-posting-api-reference-get-video-status .
