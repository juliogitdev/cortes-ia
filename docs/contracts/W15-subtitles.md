# W15 — contrato de legendas

`AnalysisRequest` 1.1.0 adiciona `subtitle_settings` com `enabled`, `style`, `position`, `max_words_per_line` e `font_scale`. Requisições 1.0.0 sem esse campo continuam válidas e desativam legendas. O exemplo em `v1/analysis_input.json` demonstra o estilo inicial `yellow_pop`. `ClipRevision` 1.1.0 adiciona `analysis_id` opcional para ligar ajustes manuais à transcrição e às opções da análise. Revisões antigas continuam válidas.

O GET `/analyses/{analysis_id}/candidates/{candidate_id}/subtitles` entrega palavras e horários em segundos do vídeo original, início inclusivo e fim exclusivo. O PUT no mesmo caminho aceita `{ "words": [{"start_s": 1.0, "end_s": 1.4, "text": "Olá"}] }`, valida ordem e limites e cria um Job de exportação. O novo MP4 não substitui o anterior. Palavras de análise e de correção são tratadas como dados não confiáveis ao gerar ASS.

Para análises antigas sem legenda, o PUT também aceita `settings` com `enabled: true` e as mesmas opções do `AnalysisRequest`. A configuração fica no payload do novo Job, preservando a análise original. Correções posteriores reutilizam essa configuração se `settings` não for repetido.

Consumidores revisados: API, Store, worker, módulo `subtitles`, painel React e documentação OpenAPI. Sem alterações em dependências ou migrações.
