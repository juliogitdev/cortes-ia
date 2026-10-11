# Entrega W2-AUTO-CUTS — arquivos prontos por sugestão

Data: 2026-10-02. Coordenador executou a integração no checkout compartilhado.
Arquivos: `services/store.py`, `api/app.py`, `media/export.py`, `ui/app.py`,
testes Store, mídia e integração, OpenAPI W2, RUN, README, STATUS e evidência JSON.

Ao concluir uma análise, a mesma transação registra uma revisão inicial e um job
de exportação para cada candidato. IDs e payloads estáveis tornam a preparação
idempotente. `POST /analyses/{id}/exports` prepara também análises antigas sem
duplicar arquivos. Os jobs seguem a fila persistida e o worker serial.

O painel mostra o MP4 exportado no player e link de download por corte, com
duração e horário original. Não usa a gravação longa como cinco players.
Ajuste manual continua disponível em expander e gera nova revisão/exportação.
O MP4 usa H.264 CRF 18, preset medium, AAC 256k e resolução da fonte. FFmpeg
faz busca rápida com pré-roll de 3 s e recodifica o intervalo solicitado;
valida duração com tolerância de 0,2 s e preserva hash/manifesto/idempotência.

Verificação: suíte integrada 95 testes após novo teste de busca tardia; teste
de mídia usa evento visual conhecido. A análise existente do vídeo de referência
com 5 candidatos exatos de 30 s foi preparada sem reanálise: os 5 jobs foram
concluídos, MP4s duram 30,03 s e ocupam 10,3–13,6 MiB cada. Quadros em +1 s
foram comparados com os mesmos instantes do original; erro médio máximo 2,99/255
em miniatura 160×90. Dados em `docs/evidence/W2-auto-cuts.json`.

Limites: a exportação recodifica na CPU e alta qualidade não significa arquivo
sem perdas. O ranking segue apenas fala; utilidade editorial dos cinco cortes
continua dependente de revisão humana. Fonte original, banco e arquivos permanecem
locais; nenhuma mídia foi excluída automaticamente.
