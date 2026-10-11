# W2 — seleção por faixa e galeria editorial

Data: 2026-10-02. Responsável: sessão principal. Sem delegação nesta rodada.

## Entregue

- `selection/baseline.py`: escolha de fim em pausa ou pontuação dentro da faixa, com fallback e limitação explícita; modo exato preservado.
- `ui/app.py`: grade de vídeos, descrição extraída da transcrição, detalhes com evidências, feedback, download e exclusão confirmada.
- `services/store.py`, `api/app.py`, `shared/jobs.py`: eventos de feedback, exclusão lógica do candidato e remoção da exportação automática; original e análise preservados.
- `docs/contracts/w2`: schema/exemplo de feedback e OpenAPI 0.4.0; documentação operacional atualizada.
- `tests/unit/test_engine.py`, `tests/integration/test_local_flow.py`, `tests/contract/test_jobs.py`: limites, interface e persistência.

## Limites e próximo passo

Verificação: 98 testes passaram no `.venv`; `pip check` e `git diff --check` sem falhas.
API e painel responderam HTTP 200 após reinício; worker anunciou `device=cuda`.
Esta rodada não realizou uma nova inferência CUDA nem análise integral da live.

O algoritmo observa apenas transcrição e pausas entre segmentos. Não compreende a conclusão do assunto nem garante que uma frase não seja interrompida quando a transcrição falha. A live de referência tem regiões de transcrição repetitiva com o modelo tiny; avaliar trechos manualmente e medir qualidade antes de automatizar parte 2 ou publicação. Os cinco MP4s antigos não são alterados; executar nova análise no modo Faixa para obter cortes com novos limites. Exclusão remove o arquivo automático, enquanto revisões manuais já criadas mantêm seus registros e arquivos para preservar o histórico.
