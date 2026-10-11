# Executar e retomar a aplicação local

Instale conforme INSTALL, inclusive FFmpeg/ffprobe e modelo local. Execute na raiz:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_local.ps1
```

Neste PC, o worker de fala pode usar a RTX validada com `scripts/start_local.ps1 -Device cuda`.
O arquivo local `runtime/local-settings.json` também pode definir `{"device":"cuda"}`;
um parâmetro explícito prevalece. Confirme a linha `Worker local: device=cuda` em
`runtime/worker.log`. A extração, seleção e exportação continuam usando CPU/FFmpeg;
somente a inferência de fala usa CUDA nesta etapa.

Abra http://127.0.0.1:8501. O frontend React/TypeScript usa Vite nessa porta e encaminha as
chamadas para a API na porta 8000. O build também é servido em http://127.0.0.1:8000/.
Crie um projeto e envie a gravação ou cole o link de um vídeo individual de YouTube,
Vimeo, Twitch, Dailymotion ou TikTok. O download usa a qualidade escolhida no painel;
pode demorar e consumir bastante disco. Cada projeto preserva uma gravação; para outra
mídia, crie outro projeto. MP4 H.264/AAC é a referência de reprodução no navegador;
outros contêineres podem ser processados, mas a prévia depende do suporte do navegador.
Escolha duração exata ou faixa, quantidade e nicho, e clique Analisar gravação.
Atualize andamento por botão. O worker informa etapa; não há percentuais inventados.

Ao concluir a análise, o worker gera automaticamente um MP4 para cada sugestão. Atualize os
cortes no painel enquanto a fila trabalha. A galeria mostra um vídeo curto por célula, uma
descrição baseada na transcrição e controles para baixar, abrir detalhes ou excluir o corte.
Em detalhes, consulte motivos, evidências e limitações e registre feedback útil/não útil.
O feedback fica no histórico e não treina modelos automaticamente. Excluir pede confirmação,
remove o MP4 automático e oculta o corte; preserva o original e a análise.
No modo Faixa, o motor procura pausa ou fim de frase dentro dos limites informados. Sem
encerramento claro, usa um limite de segmento e avisa nos detalhes. No modo Exata, a duração
é rígida e pode cortar uma fala. A exportação usa H.264/AAC,
CRF 18 e preserva a resolução de origem; duração é verificada com tolerância de 0,2 s.
Revise motivos/evidências e limitações. Para ajustar início/fim no relógio original, abra
"Ajustar limites deste corte", salve uma revisão e gere seu arquivo; o corte inicial permanece.
Toda revisão é nova; análise inicial permanece. Score é uma ordenação heurística;
orientação editorial livre é registrada, mas este baseline não a interpreta.
O motor registra mudanças entre quadros amostrados e janelas de energia sonora elevada;
esses sinais podem sugerir um corte sem fala, mas não descrevem o acontecimento.
Segmentos de transcrição muito repetitivos são desconsiderados para o ranking.

O painel abre em Contas TikTok. Escolha uma conta para ver suas lives ou abra "Lives sem conta" para organizar gravações anteriores. Ao abrir uma live, o estúdio mostra todos os cortes; "Publicar e resultados" exibe postagem imediata, agendamento e vínculo manual. Associe a conta à pasta da live no cartão ou na tela de publicação. Sem conta ou sem `video.publish`, os controles de envio aparecem bloqueados com a permissão necessária. Para consultar métricas de posts próprios, a conta precisa de `video.list`.

No vínculo manual TikTok, selecione o corte e cole o link completo `https://www.tiktok.com/@perfil/video/ID`. A data da postagem é opcional: se ausente, o sistema consulta `create_time` junto com visualizações, curtidas, comentários e compartilhamentos. Se o TikTok não fornecer a data, informe-a para salvar o vínculo. O cadastro consulta somente aquele post; abrir a página não dispara nova coleta. A consulta ao entrar no painel e o botão "Atualizar agora" continuam disponíveis.

Na galeria, **Excluir corte** remove os MP4s locais daquele corte, incluindo revisões manuais, mantendo a gravação e o histórico. Em Lives ou no estúdio, **Excluir projeto** retira a live do catálogo e apaga os arquivos locais de sua pasta, inclusive a gravação e os cortes. As duas ações mantêm os posts já publicados no TikTok; a exclusão de projeto guarda vínculos e métricas no banco para auditoria. Cancele ou conclua jobs e postagens agendadas antes de excluir. Nenhuma dessas ações chama a API do TikTok para apagar posts.

O painel também possui Visão geral, Estúdio, Lives e Configurações. Em Lives, é possível
renomear o projeto selecionado; Configurações define a qualidade de novos downloads
na sessão atual. O modelo de fala pode ser configurado em `runtime/local-settings.json`
com a chave `model` e exige reinício do worker. Um exemplo local é
`{"device":"cuda","model":"models/whisper-small"}` após preparar o modelo.

Histórico de análises permanece no SQLite e pode ser aberto após reiniciar o painel.
Histórico de revisões/exportações está persistido. Os cortes automáticos reaparecem após reiniciar;
a interface acompanha revisões manuais criadas nesta sessão.
API em http://127.0.0.1:8000/docs permite consultar uma tarefa conhecida e baixar novamente um export por ID.
Uma falha preserva o erro/histórico: clique Analisar novamente para novo pedido.
Worker morto é recuperado após lease (60 s), com novo owner e exclusão de processo.
Etapas podem ser refeitas; exportação pronta usa manifesto/hash. Não há cache fino de transcrição nesta onda.
Crash entre publicação do MP4 e seu manifesto deixa par incompleto preservado; requer inspeção local, sem substituição automática.

Para parar os quatro processos locais e seus filhos, preservando banco/mídia:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop_local.ps1
```

Os helpers abrem processos sem janelas e bind em 127.0.0.1. Logs: runtime/api.log, scheduler.log, worker.log, panel.log e respectivos .err.log.
Portas ocupadas ou manifesto existente impedem novo start; use stop antes de iniciar outra vez.
Não há servidor público/autenticação multiusuário nesta rodada.

Alternativa em três terminais PowerShell, todos na raiz:

```powershell
# Terminal 1
.\.venv\Scripts\python.exe -m uvicorn clip_platform.api.app:create_app --factory --host 127.0.0.1 --port 8000
# Terminal 2
.\.venv\Scripts\python.exe -m clip_platform.worker.runner --model models/whisper-tiny --device cpu
# Terminal 3
Set-Location frontend
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 8501 --strictPort
# Terminal 4, na raiz do projeto
.\.venv\Scripts\python.exe -m clip_platform.learning.tiktok_scheduler --storage storage
```

No PC, valide driver/backend conforme INSTALL e execute a prova CUDA antes de escolher `--device cuda`.
Se usar ambiente GPU separado, instale também a aplicação nele e use seu python para o worker.
Os auxiliares start_local usam `.venv` para API, Node para frontend e `.venv-gpu` para o worker CUDA.
Não copie dependências binárias ou modelos pelo Git.

Referências de implementação: [upload FastAPI](https://fastapi.tiangolo.com/tutorial/request-files/),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper), [React](https://react.dev/learn/build-a-react-app-from-scratch) e [Vite](https://vite.dev/guide/).
