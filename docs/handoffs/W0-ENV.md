# Entrega W0-ENV

Responsável: agente ambiente. Checkout compartilhado confirmado: `C:/Users/Julio/Documents/cortes-ia`. Lidos AGENTS.md, os três originais v1.1 e tarefa delegada; STATUS ainda ausente na leitura inicial, depois criado pelo coordenador. Área exclusiva respeitada; sem instalar dependências, baixar pesos ou editar configuração raiz.

Arquivos: `scripts/diagnose.ps1`, `scripts/gpu_smoke.py`, `docs/INSTALL.md`, este relato. Diagnóstico reproduzível Windows via CIM, ferramentas no PATH, disco/RAM/adaptadores; JSON local em runtime. Smoke opt-in real sequencial CTranslate2/faster-whisper e PyTorch/Transformers visual, CUDA obrigatória, modelos locais e hashes, lock exclusivo por checkout, versões, driver, tempo e memória. Não contém implementação do produto.

Verificação executada: PowerShell diagnose terminou com sucesso; Python 3.11 compilou o script; execução smoke no host retornou código 2 e `status: pending`, `runs: []`, `ModuleNotFoundError: No module named 'torch'`. Não houve processamento GPU nem tempo/VRAM inventados. Diagnóstico confirmou Windows 11 Pro 10.0.26200, Ryzen 7 5700U, 14.875.422.720 bytes RAM, AMD Radeon, Python 3.11.0, Git 2.49.0; nvidia-smi/uv/FFmpeg/ffprobe ausentes. Espaço livre é variável e está no JSON.

Fontes primárias consultadas: PyTorch instalação local, README faster-whisper, ficha Qwen3-VL-2B-Instruct; links em INSTALL. Stack GPU não fixada porque host alvo não está disponível. Script real não foi validado com bibliotecas/modelos/GPU nesta rodada; erro de backend/DLL/VRAM pode exigir ajuste. Memória CTranslate2 depende de amostragem nvidia-smi (total de dispositivo, pode perder picos), sem falsa equivalência com torch. Reserva só coordena este checkout; outros processos precisam ser conferidos.

Próximo passo: executar diagnóstico no computador da RTX, revisar driver/backends, preparar venv GPU separado e pesos/amostras locais autorizados, executar prova real e registrar resultado antes de promover compatibilidade. Nenhuma funcionalidade de API, UI, processamento ou treinamento entregue.
