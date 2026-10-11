# Entrega W2-DOWNLOAD — entrada por link

Data: 2026-10-02. Checkout compartilhado confirmado em `C:/Users/Cesar/Documents/GitHub/cortes-ia`.
Implementação executada pelo coordenador, sem subagentes. W1 preservada e contratos W2 versionados.

Arquivos: `ingestion/download.py`, `shared/jobs.py`, `services/store.py`, `worker/runner.py`,
`api/app.py`, `ui/app.py`, testes `test_download.py` e `test_jobs.py`, `pyproject.toml`, lock runtime,
schemas/OpenAPI W2 e documentação operacional. Download é job persistido e cancelável;
worker segue reserva serial e publica mídia somente após validar o arquivo audiovisual.
`Downloader` define a interface polimórfica; o registro de provedores pode trocar o adaptador
de uma plataforma sem alterar os consumidores. Atualmente os cinco usam `YtDlpDownloader`.
`yt-dlp[default] 2026.8.19` e dependências fixadas no lock; Node.js exigido para YouTube.

Verificação: 93 testes passaram, 1 aviso Starlette/TestClient já conhecido; `pip check` limpo;
`git diff --check` sem erros. Metadados reais do link fornecido pelo usuário foram extraídos:
`y-KdHRZ9Ggo`, título `LULA - Flow News #077`, duração 6994 s, estado `was_live`.
Teste de transferência de faixa curta via FFmpeg recebeu HTTP 403 na URL de mídia da fonte;
o modo `yt-dlp --test` obteve fragmentos de vídeo e áudio, mas não pode uni-los por serem
deliberadamente truncados. Depois, o usuário concluiu o download integral pelo painel:
o Store registra job concluído, mídia de 6994,381 s e 1.693.684.427 bytes em `storage`.
O job de análise também concluiu. Os demais provedores foram verificados por contrato/URL,
sem transferência real nesta rodada.

Limitações: melhor qualidade pode produzir arquivos grandes e formatos que o navegador não
reproduz na prévia; FFmpeg/ffprobe validam o contêiner antes da análise. Plataformas podem exigir
autenticação ou mudar extratores. Não há login/cookies nesta versão. Falha externa não altera
projetos existentes; arquivos parciais locais ficam na área do job para diagnóstico/retomada.
Próximo passo: avaliar tempo e qualidade em outras fontes e adicionar controles de qualidade
ao painel em rodada posterior.

Correção após uso no painel: a chave do formulário `download-<project_id>` colidia com
`st.session_state` usado para o ID da tarefa. Formulário e estado agora têm chaves distintas;
teste AppTest envia o link e verifica a tarefa persistida sem exceção.
