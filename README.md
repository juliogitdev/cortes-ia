# Cortes IA

Aplicação local para analisar gravações e exportar cortes, com motor independente.
Recebe link ou upload, transcreve, observa mudanças visuais e energia sonora, sugere cortes,
permite revisão e exporta MP4. API FastAPI, worker separado, SQLite e frontend React/TypeScript.
A fala usa CUDA na RTX 5060 validada neste PC; os observadores de imagem e áudio usam CPU.

Leia [instalação e clone no PC](docs/INSTALL.md), [execução](docs/RUN.md),
[estado](docs/STATUS.md) e [backlog](docs/tasks/BACKLOG.md).

```powershell
git clone https://github.com/juliogitdev/cortes-ia.git
Set-Location cortes-ia
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-runtime.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_media.ps1
.\.venv\Scripts\python.exe scripts/prepare_speech_model.py --revision d90ca5fe260221311c53c58e660288d3deb8d356
Set-Location frontend
npm ci
npm run build
Set-Location ..
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_local.ps1
```

Abra http://127.0.0.1:8501. O painel novo também é servido pela API em http://127.0.0.1:8000 após o build. Para encerrar, execute `scripts/stop_local.ps1` conforme RUN.
Ao concluir a análise, o worker gera um MP4 curto por sugestão. O painel reproduz esses cortes e oferece download individual.
Para links do YouTube, confirme também `node --version`; o painel baixa a gravação com a melhor qualidade disponível antes de analisar.
Para verificar, execute `.\.venv\Scripts\python.exe -m pytest -q`.
No PC, primeiro replique a prova CPU; depois valide CUDA conforme INSTALL.

O ranking usa fala e sinais observáveis de imagem/áudio; não estima probabilidade de viralização.
Nicho/orientação ficam registrados; orientação livre não modifica esse ranking.
Entendimento semântico de vídeo, coleta de redes sociais e treinamento pertencem às próximas ondas.
Vídeos, banco, modelos, ferramentas portable, logs e venvs ficam locais, fora do Git.
