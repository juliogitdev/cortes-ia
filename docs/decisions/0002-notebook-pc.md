# ADR 0002 — desenvolver no notebook e validar no PC

Usuário confirmou em 2026-10-02 que RTX está no PC e autorizou próximos passos no notebook.
Onda 1 usa CPU explicitamente, com baseline só fala. W0-GPU permanece pendente sem bloquear desenvolvimento.
Não interpretar testes CPU como compatibilidade/eficiência RTX. Modelos ficam locais, fora do Git.
Preparar código, locks e comandos independentes do caminho do notebook; publicar repositório ao final
para clone no PC e novo diagnóstico/benchmark CUDA. Destino GitHub ainda por informar.
