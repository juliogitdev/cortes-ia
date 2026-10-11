# W22 — proporção, enquadramento, pausas e marca d’água

## Entrega

- Nova análise permite escolher fonte, vertical 9:16 ou horizontal 16:9; ligar remoção de silêncios; digitar marca d’água e selecionar um dos quatro cantos.
- O worker preserva o corte base e cria composição versionada. No vertical, amostra rostos frontais e usa corte estático apenas quando os rostos observados cabem na janela. Caso contrário, encaixa a imagem completa sobre fundo desfocado da própria cena, mantendo todos os participantes no quadro.
- `silencedetect` do FFmpeg remove trechos abaixo de -35 dB por pelo menos 0,8 s, mantendo 120 ms de margem. O mapa dos intervalos mantidos reajusta as palavras da legenda depois da composição. O áudio e vídeo são concatenados juntos.
- `drawtext` lê a marca d’água de arquivo temporário em vez de interpolar o texto no filtro. Entrada limita 80 caracteres e uma linha. A configuração pertence à análise e é aplicada a cada export automático.
- `AnalysisRequest` 1.3.0, exemplo, JSON Schema e OpenAPI atualizados; `docs/contracts/W22-video-presentation.md` descreve consumidores e tempos.

## Verificações

- Build React aprovado.
- Smoke real FFmpeg CPU: MP4 vertical 1080×1920 e horizontal 1920×1080, ambos com marca d’água; quadro vertical inspecionado visualmente, com duas pessoas visíveis e fundo desfocado.
- Smoke com pausa sintética de ~2 s: composição preservou 0–1,12 s e 2,88–5 s; vídeo final ~3,24 s. Renderização da legenda com mapa produziu duas palavras após remoção. Smoke CUDA/NVENC da composição também produziu ~3,24 s.
- Teste de unidade do remapeamento de palavras e testes de contrato atualizados. Suíte Python completa: 143 aprovados, um aviso de depreciação do Starlette. Build React aprovado.

## Limites e retomada

Detecção de rosto é frontal e amostrada; não segue pessoas quadro a quadro. O fallback conserva o quadro inteiro. O limiar de silêncio mede volume, não intenção editorial; música ou ruído podem impedir remoção. Fontes antigas e MP4s existentes não são modificados. Depois de confirmar que não havia jobs ativos, os quatro processos locais foram reiniciados. API respondeu com `video_settings` no OpenAPI, painel respondeu HTTP 200, e API, scheduler, worker CUDA e painel estão ativos.
