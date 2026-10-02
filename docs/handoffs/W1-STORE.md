# Entrega W1-STORE

Data: 2026-10-02. Cwd confirmado: C:/Users/Julio/Documents/cortes-ia.
Entradas: documentos originais, AGENTS.md, STATUS e interfaces W1 aprovadas.
Área exclusiva: services/store.py, tests/unit/test_store.py e este relato. Sem alterações em shared/raiz.

Store usa SQLite WAL sob root absoluto; JSON validado, objetos imutáveis, transações curtas
BEGIN IMMEDIATE. Enqueue consolida ação por projeto/tipo/request_id, rejeitando payload
divergente. Claim reserva um running global; expirado tem prioridade sobre novos jobs.
Heartbeat estende lease; escritas de worker exigem owner e lease vigentes. Owner é identidade
única por execução/claim; retired_owners impede reutilizar identidade antiga após reclaim.
Runner deve gerar UUID novo ao retomar. Sem token adicional no contrato Job aprovado.

Cancelamento idempotente em queued/running invalida escrita do worker. Estados terminais
conservam owner/lease até subprocesso encerrado. Claim bloqueia reserva viva de qualquer status.
Extensão de interface aprovada pelo coordenador: `release(job_id, owner)` somente em terminal,
após join/kill do processo filho; valida owner e libera reserva, com repetição idempotente.
Sem release após crash, a reserva expira pelo timeout. Conclusão valida
AnalysisResult/Export antes de transacionar; export e estado completed são persistidos juntos.
Revisões verificam asset, limites e vínculo com revisão pai. Checkpoint é etapa persistida;
retomada pode refazer etapa, sem alegação de cache fino.

Verificação: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_store.py tests/contract -q`.
Resultado final: 48 testes passam, incluindo 13 store e 35 contratos. Casos de dois workers,
enqueue concorrente, processo morto/reabertura, reclaim, fencing, heartbeat, cancelamento,
idempotência divergente, resultado inválido e roundtrip assets/revisões/exports.

Limites: Store reserva logicamente e protege escrita, não interrompe subprocessos/modelos.
Runner precisa heartbeat periódico, interrupção ao cancelar/perder lease e release após exit; lease expirado
não prova que o processo antigo deixou de usar CPU/GPU. Caminhos precisam autorização na API;
Store guarda metadados e não serve arquivos. Candidate/revision lookup fica no coordenador/API.
Relógio de lease usa wall clock do host; mudanças manuais no relógio devem ser evitadas.

Integração: importar services.store.Store; finish recebe result direto (AnalysisResult ou Export
model_dump JSON), não envelope extra. Próximo passo: coordenador ligar worker/API e validar
fila, cancelamento e exportação no fluxo real. Nenhuma inferência/GPU executada nesta tarefa.
