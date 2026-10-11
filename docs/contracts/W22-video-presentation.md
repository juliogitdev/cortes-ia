# W22 — configuração de apresentação do corte

`AnalysisRequest` 1.3.0 adiciona `video_settings` 1.0.0. Pedidos 1.0–1.2 continuam válidos e usam `aspect=source`, `remove_silence=false` e marca d’água vazia. Novas análises podem escolher `vertical` (1080×1920), `horizontal` (1920×1080) ou `source`, remover silêncios e configurar texto/posição da marca d’água.

O export base preserva o intervalo original. A composição deriva um novo MP4 imutável. `time_map` lista pares `[início, fim)` relativos ao corte base, na ordem conservada; legendas são remapeadas a partir dos horários do vídeo original. A detecção de silêncio usa FFmpeg com limiar de -35 dB e duração mínima de 0,8 s, deixando 120 ms nas bordas. Não é detecção semântica de pausas: áudio ambiente acima do limiar permanece.

No vertical, o modelo YuNet detecta rostos de frente e de perfil em quadros amostrados. Uma pessoa usa recorte próximo; quando o foco se desloca, a janela acompanha o rosto por interpolação entre amostras. Duas pessoas presentes juntas na maior parte do corte usam painéis ampliados. Quando a detecção não é suficiente, a imagem inteira é preservada sobre o próprio vídeo desfocado. O modelo fica fora do Git em `models/` e pode ser instalado com `scripts/install_face_model.ps1`.

Exemplo: `docs/contracts/v1/analysis_input.json`; esquema atualizado: `docs/contracts/v1/analysis_request.schema.json`. Consumidores: painel React, worker de exportação, renderizador de legendas. Mídia de origem, revisões e intervalos de candidatos permanecem no relógio original.
