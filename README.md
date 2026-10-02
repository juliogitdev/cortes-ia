# Cortes IA

Aplicação local para analisar gravações e exportar cortes, com motor independente.
A onda 1 entrega upload, transcrição, seleção baseline por fala, revisão, exportação e download.
API FastAPI, worker separado, SQLite e painel Streamlit. O notebook usa CPU; RTX será validada no PC.

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
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_local.ps1
```

Abra http://127.0.0.1:8501. Para encerrar, execute `scripts/stop_local.ps1` conforme RUN.
Para verificar, execute `.\.venv\Scripts\python.exe -m pytest -q`.
No PC, primeiro replique a prova CPU; depois valide CUDA conforme INSTALL.

Baseline ordena densidade de fala; não estima probabilidade de viralização nem considera imagem.
Nicho/orientação ficam registrados; orientação livre não modifica esse ranking.
Links, coleta de redes sociais, multimodal e treinamento pertencem às próximas ondas.
Vídeos, banco, modelos, ferramentas portable, logs e venvs ficam locais, fora do Git.
