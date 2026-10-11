# W10 — Exclusão local de cortes e projetos

## Entrega

O botão de excluir corte já removia o MP4 automático e preservava análise e feedback. Agora remove também as exportações de revisões manuais do mesmo corte. A confirmação informa que o post no TikTok e as métricas permanecem. A operação é bloqueada quando o corte possui envio TikTok agendado ou em andamento.

O painel de lives e o estúdio oferecem **Excluir projeto**. `DELETE /projects/{project_id}` (OpenAPI 1.3.0) oculta a live no catálogo, remove a pasta local `storage/projects/{project_id}` com gravação, cortes e arquivos de processamento, e preserva no SQLite o histórico de publicações, métricas e proveniência. A rota não chama a API do TikTok. O servidor recusa a exclusão enquanto houver job local ou publicação TikTok pendente. A remoção da pasta é restrita ao diretório de projetos; links simbólicos impedem a operação. Uma limpeza local interrompida pode ser repetida pelo mesmo endpoint.

## Verificação

Testes de integração verificam exclusão da pasta local, preservação de arquivo fora dela, ocultação da live, retenção da publicação, idempotência e bloqueio por job e postagem agendada. O teste de exclusão individual mantém um vínculo de publicação e remove MP4s automático e de revisão manual. Suite completa: 118 testes aprovados; build e lint do frontend aprovados. Lint mantém avisos React já existentes.

## Limites

O histórico preservado fica no SQLite, mas a live excluída deixa de aparecer no catálogo e seus MP4s locais não podem ser reproduzidos. Posts no TikTok permanecem na conta e precisam ser apagados no próprio TikTok se o usuário desejar isso futuramente. A aplicação e o túnel continuam desligados a pedido do usuário.
