# W19 — análise em 88% na live Julio cocielo

## Diagnóstico

Projeto `0b3a0138-e672-4d4b-b394-3d91775c39e4`, gravação de 11.875,041 s (quase 3h18min), 3,06 GB. Job original `efb59c9a-a5cb-4ffa-8ad6-130e082855a4` ficou na etapa `observando imagem`, progresso 88%. Não havia exceção: FFmpeg estava ativo, usando CPU e lendo o arquivo sequencialmente para produzir um quadro a cada cinco segundos. Após vários minutos de etapa visual, leu cerca de 610 MB de 3,06 GB. A interface não recebia progresso dentro dessa etapa.

## Correção

`media/signals.py`: quando o worker usa CUDA, a amostragem visual emprega decodificação acelerada e somente quadros chave, mantendo amostras regulares com `fps=1/5`. A proveniência registra `frame_policy=keyframes_held` e `decoder=cuda`; horários permanecem em segundos do vídeo original. `worker/runner.py` transmite o dispositivo à etapa visual. O caminho CPU mantém a decodificação anterior.

No próprio vídeo, teste de 120 s com CUDA e quadros chave gerou 24 amostras de 32×18 em cerca de 0,8 s; amostragem por quadros chave sem CUDA levou cerca de 56 s sob carga concorrente, e CUDA sem a redução de quadros levou cerca de 24 s. Esses tempos são observações locais, não previsão linear para o arquivo completo.

O job original foi cancelado por `POST /jobs/{id}/cancel`, preservando a mídia. Uma nova análise com o mesmo pedido foi iniciada como `7145fb49-5743-431c-9006-ed1c1e35e3f5`. Ela passou de 88% para 97% e concluiu sem erro. Resultado: 5.209 segmentos de fala com 4.585 textos distintos, 1.016 eventos visuais e cinco candidatos. Os cinco exports com legenda foram concluídos, e os cinco MP4s existem no disco. Suíte completa: 137 testes aprovados. O código novo foi carregado pelo processo filho do worker sem parar painel ou agendador.

O painel ainda usa API 1.9.0 em processo iniciado antes de W17; rotas novas de versões de mídia da W17 dependem de reinício isolado posterior da API. Isso não impede os cinco vídeos de aparecerem via resultados de exportação atuais. A revisão editorial do conteúdo dos cortes permanece humana; o score não é probabilidade de viralização.
