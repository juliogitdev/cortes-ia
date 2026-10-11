# W2 — contrato de entrada por link

Versão de interface: 2.0.0. O contrato W1 permanece arquivado em `docs/contracts/w1`.
`Job` v2 aceita `kind=download`, mantendo leitura de registros `schema_version=1.0.0`.
Schemas atuais de `Job`, `DownloadRequest` e OpenAPI ficam em `docs/contracts/w2`.

`POST /projects/{project_id}/downloads` recebe `DownloadRequest` e header `Idempotency-Key`.
Exemplo:

```json
{"url":"https://www.youtube.com/watch?v=y-KdHRZ9Ggo","settings":{"quality":"best"}}
```

Retorna Job 202, sem consultar a plataforma no processo da API. O worker realiza a transferência,
valida áudio/vídeo com ffprobe e só então registra `MediaAsset` no projeto. `GET /jobs/{id}` e
`GET /projects/{id}/jobs` acompanham estado; GET não inicia download. O resultado de um job
concluído é `MediaAsset` e preserva `source_uri` como URL original. Projeto com mídia existente
recusa novo download; reenvio da mesma chave e payload retorna o mesmo job.

`DownloadSettings` admite `best` (padrão) ou `up_to_height` com `max_height` de 144 a 4320.
O painel usa `best` fixo nesta entrega; o contrato deixa a escolha pronta para futura interface.
O formato efetivo depende da plataforma. O arquivo final é audiovisual e passa pelo mesmo
pipeline de ingestão do upload. Nenhuma playlist, URL HTTP, IP, host local ou domínio fora do
registro de provedores é aceito. Provedores habilitados: YouTube, Vimeo, Twitch, Dailymotion e
TikTok; disponibilidade real depende dos extratores, acesso e regras atuais de cada fonte.
`Downloader` é o protocolo do adaptador, e `BACKENDS` associa cada provedor a uma implementação.
Hoje todos usam `YtDlpDownloader`; um provedor pode receber implementação própria sem mudar API,
fila ou painel.

## Extensão 2.1 — cortes prontos após a análise

Ao concluir um `Job` de análise, a mesma transação grava uma `ClipRevision` inicial para cada
candidato e enfileira um `Job` de exportação por candidato. IDs derivados da análise/candidato
e `request_id` estável impedem duplicatas após retomada. O intervalo da revisão é exatamente
`candidate.start_s` a `candidate.end_s` no relógio original; a mídia exportada deve respeitar
a duração pedida dentro da tolerância técnica de 0,2 s.

`POST /analyses/{analysis_id}/exports` devolve os jobs automáticos existentes e prepara
análises antigas que ainda não têm cortes. Repetir o POST não cria jobs novos. Exemplo de
payload de um job: `{"analysis_id":"<id>","candidate_id":"<id>","revision_id":"<id>","auto":true}`.
`GET /exports/{export_id}/media` serve apenas o MP4 curto autorizado para o player; o endpoint
`/download` continua entregando o arquivo. O painel usa o MP4 exportado, não a live original,
como prévia do candidato. Revisões manuais ainda geram uma nova exportação sem substituir a inicial.
OpenAPI da aplicação passa para 0.3.0; schemas de `Job`, `Project` e `Export` não mudaram.

Consumidores revisados: `api/app.py`, `worker/runner.py`, `services/store.py`, `ui/app.py`,
testes de contrato e `docs/RUN.md`. A mudança não altera `AnalysisRequest`, `MediaAsset`,
`Export` nem os horários dos cortes.

## Extensão 2.2 — galeria editorial e feedback

OpenAPI 0.4.0 inclui `CandidateFeedback` 2.1.0, cujo schema e exemplo ficam nesta pasta.
`POST /analyses/{analysis_id}/candidates/{candidate_id}/feedback` aceita `rating`
(`useful` ou `not_useful`) e `note` opcional de até 1000 caracteres. GET no mesmo caminho
lista eventos em ordem cronológica. O registro é uma avaliação humana; não inicia treino.

`GET /analyses/{analysis_id}/discarded` lista IDs ocultos. `DELETE
/analyses/{analysis_id}/candidates/{candidate_id}` marca o candidato como excluído,
impede recriação de sua exportação automática e remove o MP4 automático e seu manifesto.
Gravação original, análise e feedback permanecem. O painel pede confirmação antes do DELETE.

Para `duration_mode=range`, a seleção busca um fim de segmento transcrito entre `min_s`
e `max_s`, priorizando pausa observada ou pontuação terminal. Sem esse sinal, usa um limite
de segmento e registra a incerteza. `duration_mode=exact` preserva o tempo solicitado e
avisa que pode interromper a fala. Todos os horários seguem em segundos do original,
início inclusivo e fim exclusivo. A heurística não garante fim de assunto, sobretudo se
a transcrição tiver baixa qualidade.

## Extensão 3.0 — sinais observáveis e projetos

OpenAPI 0.5.0 expõe `PATCH /projects/{project_id}` para renomear o projeto, mantendo ID,
gravação e histórico. `GET /health` identifica `observable_signals_v1`. O schema base de
`AnalysisResult` já continha `visual_events` e `audio_events`; agora essas listas recebem
observações com horários no vídeo original e proveniência explícita.

O áudio mede energia RMS em janelas de um segundo. A imagem amostra quadros a cada cinco
segundos e registra mudanças de luminância acima do limiar da regra. O ranking considera
esses sinais com peso limitado e pode gerar sugestão a partir de mudança visual sem fala.
Nenhum sinal identifica semanticamente reação, pessoa, emoção ou importância do conteúdo.
O motor filtra segmentos de fala muito repetitivos na seleção, prioriza aberturas após
pausa ou frase encerrada e marca possível continuação após o fim. O modelo de fala é
escolhido no worker; cada análise registra identidade e configurações na proveniência.

## Extensão 3.1 — capas dos cortes

OpenAPI 0.6.0 adiciona `GET /exports/{export_id}/thumbnail`. A API verifica que o MP4
pertence ao armazenamento autorizado, extrai um quadro pequeno com FFmpeg e guarda
`*.preview.jpg` ao lado do corte. Repetir o GET reutiliza a capa. Excluir o corte
automático também remove sua capa. O endpoint não altera mídia, análise ou horários.
O frontend React consome as rotas existentes e esta rota de capa; seus arquivos
compilados são servidos na raiz da API, sem mudar os contratos dos jobs.
