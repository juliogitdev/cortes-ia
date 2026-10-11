# W15: renderização sincronizada de legendas

## Entrega

- `src/clip_platform/subtitles/render.py`: transforma palavras com horários no vídeo original em eventos ASS no tempo local do corte. Agrupa até duas linhas e realça em amarelo a palavra ativa com animação breve de escala. O texto transcrito é escapado para impedir comandos ASS vindos do vídeo.
- `render_subtitled_clip(export, evidence, clip_start_s, clip_end_s, settings, destination_dir, progress_callback=None)` produz MP4 separado; o export original não é modificado. Preserva áudio por cópia, confere duração/hash e gera um `Export` sidecar `.export.json` para o fluxo atual de exclusão.
- Cache determinístico considera hash do export original, estilo e horários/texto das palavras. Retorna `SubtitleRenderResult(export, local_path, content_hash, duration_s, caption_count, timing_quality)`; `export` é o mesmo contrato persistido no sidecar.
- Ausência de horário válido por palavra em segmento falado faz a operação falhar com indicação para reprocessar ou revisar a transcrição. Não são inventados tempos de fala.

## Testes

`\.venv\Scripts\python.exe -m pytest tests/unit/test_subtitles.py -q`: 4 aprovados. Inclui renderização real de vídeo sintético com FFmpeg, cache, deslocamento original→corte, fim exclusivo, ausência de timestamps e escape de texto não confiável.

## Limitações e próximo passo

O estilo `yellow_pop` foi implementado pela descrição do usuário; o vídeo TikTok de referência não abriu para inspeção visual neste ambiente. O render usa fonte Arial instalada localmente e libass do FFmpeg. A transcrição automática pode errar palavras ou tempos mesmo com timestamps; revisão editorial futura deve permitir corrigir ambos antes da exportação. Integrar o módulo ao worker e apresentar prévia no painel.
