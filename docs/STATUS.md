# Estado persistente — onda 1

Data: 2026-10-02. Usuário confirmou notebook sem RTX, autorizou avanço e informou repositório juliogitdev/cortes-ia.
Estado atual: fatia local CPU integrada e verificada; destino remoto https://github.com/juliogitdev/cortes-ia.
NVIDIA/visão/CUDA permanecem pendentes para o PC. Desenvolvimento não está bloqueado por esse gate.

Entregas W1: contratos Project/Job/Export e OpenAPI congelado; ingestão/FFmpeg reais;
fila SQLite WAL, leases/fencing/idempotência/cancelamento; worker em subprocesso com reserva de processo;
transcrição faster-whisper local CPU int8/CUDA explícito, motor baseline só fala; API e painel local.
Helpers de start/stop, download explícito de tiny e FFmpeg portable, demo artificial e prova CPU.
Três agentes trabalharam em mídia, Store e fala/seleção, com áreas exclusivas; coordenador integrou API/worker/UI.

Prova real CPU: 30 s de vídeo artificial com voz Windows Maria pt-BR; tiny revisão d90ca5fe260221311c53c58e660288d3deb8d356,
faster-whisper 1.2.1, CTranslate2 4.8.2. Dois segmentos, um candidato e corte 20 s baixado;
fala 1,55 s (carga+inferência), fluxo 5,93 s; pico RAM do processo de fala 250023936 bytes (~238,4 MiB),
inclui bibliotecas/vida do processo, não é delta da etapa nem VRAM. Evidência resumida em docs/evidence/W1-cpu-smoke.json.
Relatório completo local runtime/diagnostics/local-smoke-clean.json. Nenhuma afirmação de qualidade editorial em lives.

Verificação integrada final: 74 testes passaram em 20,05 s; pip check limpo; compilação src/scripts;
start/stop reais com API e painel saudáveis em localhost. Há um aviso de depreciação Starlette/TestClient sobre httpx,
sem falha; não é erro da inferência. Código/modelos/dados mantêm fronteiras: só fontes/docs/locks/testes no Git.
Originais mantidos byte a byte, inclusive no clone via regras .gitattributes específicas.
Checkpoint atual na branch main; use git status e git log para conferir revisão/sincronização.

Próximo: clone/instalação no PC conforme INSTALL e prova real W0-GPU; anotar uma gravação representativa PT-BR para qualidade do baseline.
Fonte inicial dos links/nicho/tolerância continuam a confirmar antes da onda 2. Multimodal/coleta/treino não implementados.
Comandos atuais e jornada: docs/INSTALL.md e docs/RUN.md. Consulte também handoffs W1 e backlog.

## Histórico do checkpoint onda 0 (estado abaixo é anterior)

Data: 2026-10-02. Coordenador: sessão principal.
Estado: fundação integrada e verificada; gate RTX pendente por ausência de NVIDIA acessível.

Base: pasta originalmente com três documentos, sem Git. Repositório main iniciado, sem commits ou remoto.
Documentos originais preservados; hashes em docs/decisions/0001-fundacao.md.
Subagentes reais: contratos, planejamento e ambiente, áreas exclusivas em docs/tasks/W0-delegacao.md.
Nenhum agente implementa funcionalidades das próximas ondas.

## Entregas integradas

- Estrutura src/clip_platform com onze fronteiras modulares, tests/unit, contract e integration; storage/models ignorados.
- AGENTS.md, pyproject, .gitignore, README, .venv isolado e requirements-foundation.lock.txt.
- W0-CONTRACT: contratos Pydantic 1.0.0, três exemplos JSON e três JSON Schemas sincronizados, 35 testes.
- W0-PLAN: backlog pequeno por onda, dependências e aceite; plano de avaliação e dois templates sintéticos.
- W0-ENV: instalação PowerShell, diagnóstico e script para prova real sequencial de fala/visão.
- ADR 0001 e relatos individuais em docs/handoffs; consolidação em W0-INTEGRATE.md.

## Verificações finais

Python 3.11.0; Pydantic 2.13.5; pytest 9.1.1; setuptools 84.0.0. Todas as dependências da fundação congeladas no lock.
`python -m pytest -q` com Python do .venv: **35 passed in 0.24s**.
`pip check`: sem dependências quebradas. `compileall` em src/scripts: sucesso.
Oito JSON parseados; os três JSON Schemas iguais aos gerados pelos modelos Pydantic.
Diagnóstico PowerShell: sucesso; detectou somente AMD Radeon. Smoke: código 2, pending,
nenhuma inferência, torch ausente; modelos, tempos de inferência e VRAM usada **não medidos**.
Hashes dos três documentos originais conferidos e intactos. Ignorados: venvs, runtime, storage e models.

Git: main, sem commit base, sem remoto. Todos os arquivos de entrega são novos e não commitados;
os três documentos existentes continuam preservados. Não há branches de subagentes ou merges:
integração revisada no checkout compartilhado, com áreas exclusivas. Nenhuma API/painel funcional.

## Próximo passo

1. Executar diagnóstico no computador que contém a RTX e concluir W0-GPU conforme docs/INSTALL.md.
   Preservar hashes das amostras/pesos, versões, driver, tempo e memória reais. Não considerar esta fundação
   aceite completo do critério original da onda 0 até esse gate; nenhum teste CPU/mock o substitui.
2. Confirmar nicho, duração típica das lives, tolerância de processamento e fonte inicial dos links/métricas.
   Ponto de partida técnico já decidido: arquivo local em PT-BR.
3. Na próxima rodada autorizada, W1-00 fecha Job, Export e OpenAPI antes das tarefas independentes da onda 1.
   Nenhuma tarefa da onda 1 foi iniciada.

## Comandos de retomada

```powershell
Set-Location 'C:\Users\Julio\Documents\cortes-ia'
.\.venv\Scripts\python.exe -m pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/diagnose.ps1
.\.venv\Scripts\python.exe scripts/gpu_smoke.py
Get-Content runtime/diagnostics/gpu-smoke.json -Encoding UTF8
git status --short --branch
```

Instalação do zero e comando com pesos/amostras locais: docs/INSTALL.md. O smoke sem backend retorna
pendência esperada; não é teste de processamento aprovado.
