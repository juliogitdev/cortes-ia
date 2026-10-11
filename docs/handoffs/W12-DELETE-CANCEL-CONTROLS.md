# W12 — cancelar tarefas e excluir perfis

## Mudanças

- Cada download em fila ou execução tem um botão **Cancelar download** no estúdio. A visão geral também oferece **Cancelar** para tarefas ativas de qualquer live.
- A confirmação de exclusão da live mostra **Cancelar tarefas desta live** quando há jobs locais ativos; a exclusão fica disponível depois. Publicações TikTok agendadas continuam exigindo cancelamento no painel de publicação.
- Os cartões de perfis editoriais têm botão de exclusão e confirmação. `DELETE /profiles/{profile_id}` remove somente o perfil e desassocia suas lives, preservando lives, mídia, contas TikTok e publicações.
- API/OpenAPI 1.5.0, frontend atualizado ao vivo por Vite. A API foi reiniciada isoladamente; worker, agendador e painel permaneceram ligados. A análise em execução continuou em `transcrevendo` após o reinício da API.

## Verificação

- 122 testes Python aprovados, inclusive exclusão de perfil com live preservada.
- Build e lint frontend aprovados; lint registra apenas avisos React já existentes.
- API 1.5.0 e painel HTTP 200 verificados; todos os quatro processos locais ativos.

## Limites

- Cancelar uma tarefa mantém o registro histórico com estado `cancelled`; o botão de excluir perfil não remove uma conta social externa.
- A exclusão de uma live continua recusada se existir postagem TikTok pendente. A UI orienta a cancelar essa postagem na área de publicação.
