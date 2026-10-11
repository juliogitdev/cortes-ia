# W13 — espaço de trabalho por perfil

## Entrega

- Seleção de perfil virou entrada obrigatória. O perfil ativo aparece no topo e na lateral; **Trocar perfil** retorna à tela de escolha sem encerrar o administrador local. A escolha persiste na sessão do navegador.
- A visão geral, lives recentes, atividade, tarefas, estúdio e resultados usam apenas as lives do perfil ativo. Abrir uma live já não troca o perfil implicitamente.
- A opção **Lives sem perfil** é um espaço separado para conteúdo antigo. A tela de escolha permite mover essas lives para um perfil antes de entrar. O seletor de perfil saiu de cada cartão de live.
- Configuração global do aplicativo/contas TikTok ficou na tela de escolha; o painel de publicação mostra a conta e os cortes da live ativa, sem seletor de contas de outros perfis.
- A criação de live com `profile_id` é atômica no servidor e herda a conta TikTok do perfil. Ao alterar a conta do perfil, o servidor atualiza suas lives na mesma transação e respeita conflitos com publicações existentes.
- A coleta manual e por início de sessão recebe `profile_id` e consulta somente publicações desse espaço. Continua ocorrendo apenas por POST/autorização de sessão ou ação explícita; GET não coleta.
- API/OpenAPI 1.6.0.

## Verificação

- 124 testes Python aprovados; build e lint do frontend aprovados (avisos React já existentes).
- Smoke real com Edge headless via `node frontend/scripts/smoke-profile-scope.mjs`: perfil selecionado, visão geral isolada, troca explícita, lives sem perfil e tela móvel sem rolagem horizontal; nenhum erro JavaScript.
- Aplicação local manteve painel, worker e agendador ligados durante o desenvolvimento; somente a API foi reiniciada ao final para carregar os endpoints. API 1.6.0 e painel HTTP 200 verificados. A análise em execução concluiu sem cancelamento.

## Limite

Este isolamento organiza o workspace de um administrador local. Não é um sistema de permissões entre usuários nem autenticação de contas sociais. O aplicativo TikTok continua sendo uma configuração global do computador, administrada na tela de escolha de perfis.
