# W28 — arquitetura de escritórios e agentes

## Entrega

- `docs/architecture/office-agents.md`: mapeamento do produto atual para escritórios, modelo de dados, papéis, pipeline, handoffs, interface em pixel art, integrações, segurança, recursos, ondas e critérios de aceite.
- Usuário confirmou escritório por marca com até uma conta TikTok, uma Instagram e um canal YouTube inicialmente. `docs/decisions/0004-office-multichannel.md` fixa a cardinalidade e variantes independentes por plataforma.
- Pesquisa de capacidades em fontes oficiais de TikTok, Meta e YouTube. Integrações Instagram/YouTube são propostas, não implementadas.

## Verificação e limites

- Inventário read-only de contratos, serviços, filas, integração TikTok, frontend, backlog e estado do Git. Nenhum vídeo, conta, job ou banco foi modificado.
- Documento inspecionado por coerência com as regras existentes: tempos originais, coleta por ação explícita, uma tarefa pesada de GPU, aprovação humana, proveniência e score sem interpretação probabilística.
- Próxima ação de implementação: contratos/migração com backup e testes de isolamento, seguidos de presets, variantes, QA e UI. O escritório animado ainda não existe na aplicação.
