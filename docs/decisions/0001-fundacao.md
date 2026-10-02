# ADR 0001 — Fundação, ambiente e limites

Data: 2026-10-02 (America/Sao_Paulo). Estado: adotada para onda 0.

Problema: preparar projeto sem presumir acesso à RTX ou implementar todas as ondas.

Decisão: manter stack proposta nos documentos; instalar apenas Pydantic e pytest em ambiente virtual Python 3.11.
As demais dependências, CUDA e modelos são candidatos até benchmark real. Nenhuma API paga de inferência.
Arquivo local em português brasileiro será a primeira entrada; plataforma de links, nicho, duração usual,
tolerância de processamento e fonte de métricas permanecem por confirmar na próxima rodada.

Git inexistente na chegada: iniciado repositório local main, sem remoto, sem commit automático.
Três documentos originais preservados. Não havia AGENTS.md na raiz nem nos ancestrais consultados.
Subagentes disponíveis via ferramentas da sessão, quatro slots incluindo coordenador.
Três executores usam o mesmo checkout com fronteiras exclusivas em docs/tasks/W0-delegacao.md.
Não criar .codex/config.toml: não é necessário para delegação desta sessão e suporte local não foi comprovado.

Hardware observado: Windows 11 Pro 10.0.26200 x64; PowerShell 5.1; Ryzen 7 5700U;
RAM 14875422720 bytes (~13,85 GiB); C: ~25,84 GiB livres no levantamento.
Win32_VideoController e PnP Display mostram AMD Radeon(TM) Graphics, driver 31.0.21923.11000.
nvidia-smi ausente no PATH e nos dois caminhos padrão consultados. RTX 5060 não acessível nesta sessão.
Python 3.11.0, Git 2.49.0; Docker e Node no PATH, sem validar daemon/runtime;
FFmpeg, ffprobe e uv ausentes do PATH. yt-dlp 2026.3.17 instalado globalmente, não usado como dependência do projeto.

Consequência: entregar fundação verificada em CPU, com gate GPU aberto. Não afirmar onda 0 aprovada
no hardware alvo até inferência real de fala e visão com modelo, versão, tempo e VRAM registrados.
Não instalar pesos nem bibliotecas CUDA neste host sem NVIDIA detectada.

Proveniência dos documentos originais (SHA-256):
- 01_visao_do_projeto.md: 47DED57F663A01BD92DDF80654FB736B70FD7DEB4A4B4112DC664D86F964F6AA
- 02_plano_de_desenvolvimento.md: 3387557255E32B835BD3761985F9839AA5CA7A72018D9E3D3571C2E0ECFF3EAB
- 03_manual_de_multiagentes_codex.md: 9BBCE754C879CA16A3F16AC8E52149AF99B9548E32480C19904850214432935F
