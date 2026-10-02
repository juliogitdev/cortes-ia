# Entrega integrada — onda 1 no notebook

Usuário autorizou avanço CPU e transferência via GitHub para o PC. Base antes da rodada: fundação W0 sem commit.
Destino informado SSH git@github.com:juliogitdev/cortes-ia.git, equivalente HTTPS usado no notebook,
onde SSH falhou por confiança do host/chaves não configuradas. Não houve alteração do SSH global.

Três executores, checkout compartilhado e áreas exclusivas: W1-MEDIA, W1-STORE, W1-ENGINE.
Coordenador aprovou contratos aditivos, integrou worker separado, API, painel, scripts e OpenAPI.
Revisão incorporou idempotência de upload, revisão/export sem sobrescrita, retenção de reserva terminal até release,
fencing, cancelamento do processo/filhos e lock OS para evitar inferências simultâneas após expiração de lease.
Sem APIs de inferência externas, modelo visual, rede social ou treinamento.

Prova real CPU registrada docs/evidence/W1-cpu-smoke.json: voz sintética Windows Maria pt-BR e vídeo gerado FFmpeg,
Whisper tiny multilíngue com pesos locais/revisão/hash, transcrição real, baseline, revisão, export CPU e download API.
30 s entrada, 20 s saída, 2 segmentos, 1 candidato, 1,55 s fala e 5,93 s total;
pico RAM do processo fala ~238,4 MiB medido pelo Windows, inclui bibliotecas. Nenhuma VRAM/RTX medida.
Qualidade de transcrição/cortes em lives representativas não é inferida dessa amostra artificial.

Verificação técnica final: 74 testes integrados passaram em 20,05 s; pip check sem falhas; compileall sucesso;
schemas/OpenAPI conferidos; start/stop de API, worker e painel reais com health HTTP 200.
AppTest percorre revisão/export/download contra API real, fala simulada apenas nesse teste.
FFmpeg tests conferem marcador visual, frequência/duração/sincronização; testes da fila verificam recuperação/owners.
Playlists renomeadas são rejeitadas por whitelist de demuxers antes de ler as mídias referenciadas.
Warning conhecido de Starlette sobre httpx em TestClient, sem impacto nos resultados.

Limitações: baseline ordena densidade de fala e não usa orientação livre/nicho para personalizar ranking;
não detecta eventos sem fala. Reprodução original de contêineres depende do navegador (MP4 referência).
Retry de job refaz etapas; export já pronto reutiliza manifesto. Par MP4/manifesto incompleto após crash é preservado para inspeção.
Histórico de jobs persistido acessível no painel; revisões/exports anteriores disponíveis por API, sem tela dedicada ainda.
GPU CUDA/Qwen, dataset humano, fonte inicial de links e tolerância de processamento aguardam PC/definição do usuário.

Executar/clonar: README, docs/INSTALL e docs/RUN. Dependências, pesos e mídias são recriados localmente e não entram no clone.
Próximo checkpoint: diagnóstico RTX e prova real; avaliação de live representativa antes de aceite editorial;
depois conector inicial da onda 2, com escopo confirmado. Git não deve ser confundido com transferência das mídias.
