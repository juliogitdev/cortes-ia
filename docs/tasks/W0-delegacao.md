# Tarefas autorizadas — onda 0

Base: três documentos v1.1, preservados; checkout compartilhado em C:/Users/Julio/Documents/cortes-ia.
Não criar commits nem alterar dependências ou configuração raiz. CPU apenas.

## W0-CONTRACT — contratos (dono: agente contratos)
Objetivo: Pydantic v2 para os contratos do plano, incluindo coleta sob demanda.
Escrita exclusiva: src/clip_platform/shared/**, docs/contracts/**, tests/contract/**, docs/handoffs/W0-CONTRACT.md.
Entradas: docs originais; saída: schemas e fixtures versionados, testes positivos e negativos.
Dependência: Pydantic v2 será instalado pelo coordenador.
Aceite: validação temporal, modos de duração exclusivos, referências e proveniência, exemplos de entrada/saída; campos ausentes de métricas não viram zero.
Limite: contratos apenas, nenhum serviço funcional. Relatar o comando de teste.

## W0-PLAN — backlog e avaliação (dono: agente planejamento)
Escrita exclusiva: docs/tasks/BACKLOG.md, evals/**, docs/handoffs/W0-PLAN.md.
Entradas: docs originais e esta tarefa. Saída: pequenas tarefas por onda, áreas, dependências, testes e aceite; plano de amostras sem dados privados.
Aceite: onda 1 executável por dependências e requisito v1.1 na onda 4; não implementar funcionalidades.

## W0-ENV — diagnóstico e instalação (dono: agente ambiente)
Escrita exclusiva: scripts/**, docs/INSTALL.md, docs/handoffs/W0-ENV.md.
Entradas: docs originais, Windows 11 Pro 64 bits, Ryzen 5700U, 14875422720 bytes RAM, ~27,7 GB livres; só AMD Radeon detectada, sem nvidia-smi, FFmpeg ou uv no PATH; Python 3.11.0 e Git 2.49.0.
Saída: diagnóstico reproduzível e instruções PowerShell; prova GPU de fala e visão preparada, não executada sem NVIDIA.
Aceite: resultado persistível explícito pendente sem GPU, versões/tempo/memória registrados quando houver inferência real; sem baixar modelos ou instalar globalmente.
Não fixar versões CUDA/torch não verificadas. Coordenador instala somente base Pydantic + pytest em .venv.

Coordenador possui todos os demais arquivos, estrutura dos módulos, configuração raiz, registro de decisões e integração.
