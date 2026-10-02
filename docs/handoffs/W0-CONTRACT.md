# Entrega W0-CONTRACT

Data: 2026-10-02. Checkout confirmado: C:/Users/Julio/Documents/cortes-ia.
Originais, AGENTS.md, tarefa e STATUS provisório lidos. Sem commits e sem alterações na raiz.

Entregas: `src/clip_platform/shared/{__init__,contracts}.py`, `docs/contracts/README.md`,
`docs/contracts/v1/*.json` e `tests/contract/test_contracts.py`.
Schemas Pydantic v2 1.0.0 incluem mídia, evidência, pedido, candidato, revisão, publicação,
coleta, snapshot, feedback e execução. Envelopes contextuais validam asset, duração,
proveniência, existência/sobreposição das evidências, idade real e vínculo das métricas.
Revisão do coordenador incorporada: uma coleta ativa, IDs de snapshots únicos, coleta
posterior à postagem, estado requested sem início. Fixtures são sintéticas, sem dados privados.

Teste executado: `.\.venv\Scripts\python.exe -m pytest tests/contract -q`.
Resultado: 35 passed (Python 3.11.0, Pydantic 2.13.5, pytest 9.1.1).
Casos negativos cobrem modos ambíguos, horários inválidos/não finitos, referências inexistentes,
mídia errada, duração alternativa, ausência preservada, idade falsa, timestamp sem timezone,
coleta implícita, concorrência lógica e dados manuais sem responsável.

Limitações: validação não comprova coerência semântica de motivos nem qualidade dos cortes.
Vínculos de revisão/publicação exigem persistência futura; idempotência e proibição de coleta
em GET/treino automático exigem testes da onda 4. JSON Schemas não expressam validadores
contextuais Python. URLs/caminhos não autorizam IO nem validam SSRF. Nenhuma GPU usada.

Integração: coordenador deve executar suíte no estado combinado e revisar fixtures/contratos.
Próximo passo: aprovar baseline e liberar consumidores da onda 1; alterações de contrato
permanecem com único dono e passam pela coordenação.
