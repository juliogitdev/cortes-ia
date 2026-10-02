# Executar e retomar a aplicação local

Instale conforme INSTALL, inclusive FFmpeg/ffprobe e modelo local. Execute na raiz:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_local.ps1
```

Abra http://127.0.0.1:8501. Crie um projeto e envie a gravação. Cada projeto preserva uma gravação;
para outra mídia crie outro projeto. MP4 H.264/AAC é a referência de reprodução no navegador;
outros contêineres podem ser processados, mas a prévia depende do suporte do navegador.
Escolha duração exata ou faixa, quantidade e nicho, e clique Analisar gravação.
Atualize andamento por botão. O worker informa etapa; não há percentuais inventados.

Revise motivos/evidências e limitações. Ajuste início/fim no relógio original, salve uma revisão,
gere o arquivo e atualize exportação; quando concluída, clique Baixar corte.
Toda revisão é nova; análise inicial permanece. Score é densidade textual para ordenação;
orientação editorial livre é registrada, mas este baseline não a interpreta.
Eventos sem fala e qualidade multimodal serão tratados na onda 3.

Histórico de análises permanece no SQLite e pode ser aberto após reiniciar o painel.
Histórico de revisões/exportações está persistido; a interface atual acompanha a exportação criada nesta sessão.
API em http://127.0.0.1:8000/docs permite consultar uma tarefa conhecida e baixar novamente um export por ID.
Uma falha preserva o erro/histórico: clique Analisar novamente para novo pedido.
Worker morto é recuperado após lease (60 s), com novo owner e exclusão de processo.
Etapas podem ser refeitas; exportação pronta usa manifesto/hash. Não há cache fino de transcrição nesta onda.
Crash entre publicação do MP4 e seu manifesto deixa par incompleto preservado; requer inspeção local, sem substituição automática.

Para parar os três processos e seus filhos, preservando banco/mídia:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop_local.ps1
```

Os helpers abrem processos sem janelas e bind em 127.0.0.1. Logs: runtime/api.log, worker.log, panel.log e respectivos .err.log.
Portas ocupadas ou manifesto existente impedem novo start; use stop antes de iniciar outra vez.
Não há servidor público/autenticação multiusuário nesta rodada.

Alternativa em três terminais PowerShell, todos na raiz:

```powershell
# Terminal 1
.\.venv\Scripts\python.exe -m uvicorn clip_platform.api.app:create_app --factory --host 127.0.0.1 --port 8000
# Terminal 2
.\.venv\Scripts\python.exe -m clip_platform.worker.runner --model models/whisper-tiny --device cpu
# Terminal 3
.\.venv\Scripts\python.exe -m streamlit run src/clip_platform/ui/app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

No PC, valide driver/backend conforme INSTALL e execute a prova CUDA antes de escolher `--device cuda`.
Se usar ambiente GPU separado, instale também a aplicação nele e use seu python para o worker.
Os auxiliares start_local usam .venv; o modo de três terminais permite misturar API/UI .venv e worker .venv-gpu.
Não copie dependências binárias ou modelos pelo Git.

Referências de implementação: [upload FastAPI](https://fastapi.tiangolo.com/tutorial/request-files/),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) e [testes de app Streamlit](https://docs.streamlit.io/develop/api-reference/app-testing).
