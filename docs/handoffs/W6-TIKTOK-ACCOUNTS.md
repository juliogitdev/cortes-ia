# W6 — Login Kit TikTok e múltiplas contas

Data: 2026-10-02. Coordenador e implementador: sessão principal. Checkout compartilhado confirmado. Aplicação e túnel foram desligados antes da edição.

## Entrega

- Em Resultados, o operador configura `client_key`, `client_secret` e URL HTTPS de retorno no próprio painel. A API nunca devolve o segredo. Dados ficam em `storage/integrations/tiktok-app.json`, fora do Git.
- O botão Vincular conta inicia Login Kit com estado aleatório em cookie HttpOnly/Secure/SameSite=Lax. O retorno verifica o estado, troca o código por tokens no servidor e consulta `open_id` e nome do perfil. Cada conta é persistida separadamente por hash de `open_id`; somente nome, ID e permissões são mostrados ao painel.
- As publicações TikTok novas e anteriores podem ser associadas a uma conta vinculada. Consultas de métricas usam o token da conta selecionada e verificam `video.list`. Tokens são renovados por conta, com rotação persistida sob bloqueio de arquivo entre as APIs local e remota.
- `Publication.account_open_id` é opcional para preservar registros antigos. API 0.9.0, OpenAPI atualizado, exemplo de contrato em `docs/contracts/w3/tiktok_connected_publication.json`, consumidores React e testes atualizados.
- Uvicorn foi configurado sem access log para evitar registro do código OAuth presente na URL de retorno. O proxy Vite agora encaminha `/integrations` e `/publications` para a API local.

## Configuração necessária pelo proprietário

1. Criar aplicativo em TikTok for Developers; habilitar Login Kit, Display API e solicitar `video.list`. `user.info.basic` identifica o perfil. Para futura publicação direta, solicitar também `video.publish` e completar auditoria da Content Posting API.
2. Cadastrar no Login Kit uma URL HTTPS que termine exatamente em `/integrations/tiktok/callback`. Preferir domínio fixo: o Quick Tunnel muda de hostname ao reiniciar.
3. Abrir Resultados > Integração TikTok, preencher chave, segredo e a mesma URL de retorno; salvar. Clicar Vincular conta e consentir no TikTok para cada perfil. Associar as publicações já registradas ao perfil correspondente.

O botão de publicação ainda não foi implementado. Solicitar `video.publish` na vinculação apenas prepara a permissão, depois que ela for aprovada. Nenhuma chave ou token foi configurado nesta entrega; o fluxo real não pôde ser testado sem aplicativo e contas autorizados. Segredo e tokens residem no computador e dependem da proteção do usuário Windows e da senha de acesso remoto atual; para SaaS multiusuário serão necessários autenticação individual, isolamento por tenant e proteção adicional dos segredos.

Fontes oficiais: https://developers.tiktok.com/docs/en/login-kit-web ; https://developers.tiktok.com/docs/en/oauth-user-access-token-management ; https://developers.tiktok.com/docs/en/tiktok-api-v2-video-query ; https://developers.tiktok.com/docs/en/content-posting-api-get-started .

## Verificação

Suite Python: 109 testes aprovados. Build e lint do frontend aprovados, com avisos React preexistentes e um no componente novo. Navegador Edge carregou Resultados localmente e pelo túnel: rotas de integração/publicações responderam 200 e não houve erro JavaScript. Testes OAuth usam transporte HTTP simulado e verificam segredo ausente nas respostas, cookie e estado, troca de código, duas contas separadas e escolha do token correto. A validação externa real permanece pendente de aplicativo TikTok aprovado.
