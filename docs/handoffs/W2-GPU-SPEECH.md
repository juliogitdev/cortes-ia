# Entrega W2-GPU-SPEECH — fala na RTX

Data: 2026-10-02. Coordenador executou a mudança no checkout compartilhado.
Arquivos: `speech/cuda.py`, `speech/transcribe.py`, `scripts/start_local.ps1`,
`requirements-gpu-windows.lock.txt`, `docs/INSTALL.md`, `docs/RUN.md`,
`docs/STATUS.md` e evidência JSON. Ambiente local `.venv-gpu` e configuração
`runtime/local-settings.json` permanecem fora do Git.

Motivo: `start_local.ps1` mantinha CPU como padrão desde a fase notebook.
Neste PC, `nvidia-smi` confirmou RTX 5060, mas a primeira inferência real falhou
por falta de `cublas64_12.dll`. Instalados cuBLAS 12.9, cuDNN 9 e NVRTC oficiais
em venv isolado. O adaptador registra os diretórios das DLLs antes de importar
faster-whisper no subprocesso do worker. Não há fallback silencioso para CPU.

Verificação: inferência CUDA/float16 real em tom de 3 s e fala de 10 s da gravação
de referência; worker completo em amostra audiovisual de 10 s concluiu com um
candidato. Números e limites em `docs/evidence/W2-speech-cuda-smoke.json`.
`pip check` limpo e 93 testes passaram no `.venv-gpu`. API/painel saudáveis HTTP 200;
worker principal iniciou com `.venv-gpu` e registrou `device=cuda`.

Próximo: avaliar velocidade e qualidade na gravação completa, instalar/testar
modelo visual separadamente e concluir W0-GPU completo. Exportação FFmpeg,
download e ranking baseline continuam CPU; CUDA acelera apenas a transcrição.
