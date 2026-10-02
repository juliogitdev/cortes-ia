# Instalação no notebook e clone no PC — onda 1

Host observado em 02/10/2026: Windows 11 Pro 64 bits, AMD Ryzen 7 5700U, 14.875.422.720 bytes de RAM (~13,85 GiB), cerca de 27,7 GB livres; Python 3.11.0 e Git 2.49.0. Apenas AMD Radeon foi detectada. `nvidia-smi`, FFmpeg, ffprobe e uv não estavam no PATH. A RTX 5060 informada como alvo não está acessível nesta sessão. Não houve inferência CUDA, nem medição de tempo/VRAM de modelo real.

## Instalar o fluxo local no PowerShell

No PC, clone o código (Python 3.11 64 bits e Git são necessários). HTTPS e a URL SSH informada apontam ao mesmo repositório;
SSH exige chaves e confiança do host configuradas no computador. Este notebook conseguiu acessar HTTPS.

```powershell
git clone https://github.com/juliogitdev/cortes-ia.git
Set-Location cortes-ia
```

Execute na raiz do projeto. Não é necessário ativar o venv nem alterar a política de execução global. Se `.venv` existir, preserve-o e use o Python já presente; crie somente se ausente.

```powershell
if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements-runtime.lock.txt
& .\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_media.ps1
& .\.venv\Scripts\python.exe scripts/prepare_speech_model.py --revision d90ca5fe260221311c53c58e660288d3deb8d356
& .\.venv\Scripts\python.exe -m pytest
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/diagnose.ps1
```

O lock runtime fixa as dependências testadas no notebook, incluindo API/painel/fala CPU e testes. O lock foundation guarda o checkpoint mínimo da onda 0;
ele sozinho não instala a aplicação atual. Modelos e ferramentas não vêm no clone: os dois comandos explícitos acima baixam Whisper tiny (~75 MB de pesos)
e FFmpeg/ffprobe portable 9.0.2, com versão/revisão/hash registrados, sem instalação global.
Não inclua o .venv do notebook no Git; recrie no PC. RAM/tempo CPU não comprovam compatibilidade CUDA.
Arquivos em storage/models/runtime são ignorados e não são transferidos pelo clone.

Para um teste CPU pequeno, independente de uma live privada:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/create_demo.ps1
.\.venv\Scripts\python.exe scripts/smoke_local.py
Get-Content runtime/diagnostics/local-smoke.json -Encoding UTF8
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_local.ps1
```

A amostra usa voz sintética pt-BR do Windows, se instalada; na ausência dela, forneça seu arquivo com `smoke_local.py --video caminho.mp4`.
A prova espera mídia de pelo menos 20 s, ou ajuste `--duration`. É teste técnico, não avaliação editorial.
O painel abre em http://127.0.0.1:8501; jornada e logs em [RUN.md](RUN.md).
O script de demo preserva destinos existentes: para repetir, use outro `-OutputPath`.

O smoke GPU sem backend (`.\.venv\Scripts\python.exe scripts/gpu_smoke.py`) retorna código 2 com pendência esperada.
Resultados locais ficam em runtime/diagnostics, fora do Git. CPU usa int8; CUDA, quando explicitamente selecionado, usa float16 sem fallback.

## Preparar a máquina com a RTX (pendente)

1. Execute `scripts/diagnose.ps1` no host que contém fisicamente a RTX. Confirme `nvidia-smi`, driver, memória e capacidade de computação; reconhecimento do nome não é aceite CUDA.
2. Instale FFmpeg/ffprobe por distribuição indicada no [site oficial](https://ffmpeg.org/download.html), adicione a pasta `bin` ao PATH da sessão e confirme `ffmpeg -version` e `ffprobe -version`. Preserve o PATH existente.
3. Use ambiente GPU separado, `.venv-gpu`, mantendo a fundação. No [seletor oficial do PyTorch](https://pytorch.org/get-started/locally/), escolha Windows/Pip/Python e CUDA suportada pelo driver e arquitetura. Substitua o executável `pip` do comando apresentado por `.\.venv-gpu\Scripts\python.exe -m pip`. Não usar uma versão CUDA inferida apenas pelo nome RTX.
4. Consulte os requisitos CUDA/cuDNN e de CTranslate2 no [faster-whisper](https://github.com/SYSTRAN/faster-whisper). A wheel PyTorch não assegura que o backend CTranslate2 encontrará suas DLLs nem que ambos suportam a placa.
5. Confira a implementação e versão Transformers requerida na [ficha Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct). Esse é candidato visual, não escolha validada. Não habilite `trust_remote_code` para contornar erro. Instale versões explicitamente revistas de Transformers, Pillow, faster-whisper e CTranslate2 no venv GPU; registre-as no relatório. Nenhuma versão GPU foi fixada nesta onda.
6. Reutilize o tiny preparado em models/whisper-tiny (manifesto com repo/revisão) e baixe deliberadamente o candidato visual completo em área privada fora do Git. Reserve espaço para pesos/cache: os ~27,7 GB livres medidos no notebook não são orçamento do PC. Use áudio português curto (~5–10 s), imagem pequena e referências conhecidas. Registre repo/revisão; o smoke calcula hashes completos dos pesos/amostras, mas não infere a revisão remota de uma pasta arbitrária.

```powershell
python -m venv .venv-gpu
# Instale aqui os comandos oficiais revisados para a placa e o driver reais.
& .\.venv-gpu\Scripts\python.exe scripts/gpu_smoke.py --speech-model 'D:\modelos\whisper-tiny-ct2' --audio 'D:\amostras\fala-pt.wav' --vision-model 'D:\modelos\Qwen3-VL-2B-Instruct' --image 'D:\amostras\quadro.jpg'
Get-Content runtime/diagnostics/gpu-smoke.json -Encoding UTF8
& .\.venv-gpu\Scripts\python.exe -m pip freeze | Set-Content runtime/diagnostics/gpu-packages.txt
```

O script exige GPU CUDA e todos os arquivos locais; não baixa modelos e não usa CPU como alternativa. Uma reserva exclusiva em `runtime/gpu-reservation.lock` evita duas execuções deste script neste checkout mesmo com saídas diferentes; confirme que nenhum outro executor usa a GPU antes de iniciar. Se o processo morrer sem limpeza, confirme que terminou antes de remover manualmente o lock obsoleto. Só fala ou visão na memória por vez; a imagem é reduzida a no máximo 512 × 512. Código 0 significa ambas inferências terminaram com medição de memória; código 2 mantém pendência/falha/medição incompleta explícita. Se faltar backend, DLL ou memória, preserve o JSON e ajuste a stack ou o candidato, sem declarar compatibilidade.

O relatório registra versões, driver, modelo/caminho, hash SHA-256 do manifesto e conteúdo dos arquivos locais, hashes das amostras, dispositivo, tempo de carga+inferência e amostras de VRAM total via nvidia-smi. O hash de modelo lê todos os arquivos antes da medição; essa preparação pode demorar e não integra o tempo de inferência. Baseline é a primeira amostra disponível de cada etapa; pico amostrado é escalar, considerando todas as GPUs retornadas. Pico PyTorch refere-se à visão; CTranslate2 não usa seu alocador. Amostragem pode perder picos curtos e inclui processos externos. Compare a saída com a fala/imagem conhecidas antes de aceitar qualidade: conclusão técnica do script não mede precisão. Não persiste transcrição nem texto visual para evitar dados privados; preserve apenas evidências autorizadas em área local.

Fontes primárias consultadas em 02/10/2026. Comandos de instalação GPU continuam pendentes até acessar o host correto e conferir sua compatibilidade real.
