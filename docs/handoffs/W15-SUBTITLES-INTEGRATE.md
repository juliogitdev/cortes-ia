# W15 — integração do módulo de legendas

## Escopo e arquivos

- `shared/contracts.py`: `SubtitleSettings`, `SubtitleWord`, `AnalysisRequest` 1.1.0 e `ClipRevision` 1.1.0 com `analysis_id`. Requisições/revisões antigas continuam aceitas.
- `subtitles/render.py`: palavras no tempo original são deslocadas para o corte, agrupadas em até duas linhas, com destaque amarelo animado por palavra em ASS/libass. Texto não confiável é escapado. Falha explícita se a transcrição falada não tiver horários por palavra; a revisão manual aceita palavras adicionadas/corrigidas.
- `worker/runner.py`: a exportação gera o MP4 base e depois, se ativado, um MP4 com legenda e identidade própria; progresso cobre ambas as codificações. A revisão de palavras produz uma nova versão sem substituir o arquivo anterior.
- `api/app.py`: GET/PUT de revisão de palavras por corte, com validação de tempo original, ordem, duração e vínculo com a análise. Excluir o corte remove também versões intermediárias e bases relacionadas.
- `frontend/src`: aba de legendas no formulário de análise e editor de palavras/horários no detalhe do corte; adição/remoção de palavras. O vídeo concluído anterior continua visível durante uma nova exportação.
- Cortes de análises antigas também podem receber legendas pelo detalhe do corte, sem reanalisar a live. A ativação gera um novo Job de exportação com suas configurações e preserva a análise original.
- Contratos e OpenAPI atualizados em `docs/contracts`; API 1.8.0.

## Verificação

- `python -m pytest -q`: 134 aprovados. Os testes de ponta a ponta usam FFmpeg real com vídeo sintético: análise, exportação, correção, novo MP4, download, exclusão e ativação retroativa em análise antiga.
- `npm run build` e `npm run lint`: aprovados; sete avisos React já existentes fora do módulo.
- `node scripts/smoke-subtitles.mjs`: formulário de legendas e ativação retroativa em corte antigo abertos no Edge headless em 1440 px e 390 px, sem erros JavaScript; capturas ignoradas em `runtime/`.
- Frame do MP4 sintético renderizado inspecionado visualmente; fonte foi ampliada após a primeira inspeção.
- Uma cópia temporária de um corte real já existente (26,2 s) foi legendada em `runtime/`: 105 eventos de palavra, MP4 gerado e frame inspecionado. O arquivo original e as exportações do projeto não foram alterados. Esta verificação mostra renderização com evidência real já transcrita, sem provar que todas as palavras foram reconhecidas corretamente.
- API 1.8.0, painel HTTP 200, worker e agendador ativos após reinício isolado sem Jobs em execução.

## Limitações e próximo passo

- O vídeo TikTok de referência não abriu pela ferramenta disponível. O estilo `yellow_pop` segue a descrição do usuário: palavras destacadas em amarelo, animação curta de escala e contorno para leitura. A comparação exata com o vídeo enviado ainda depende de uma captura ou acesso visual ao vídeo.
- Os testes com fala usam transcrição sintética com horários conhecidos. É preciso avaliar uma live real para medir erros de reconhecimento e alinhamento; o editor permite corrigir palavras e segundos do vídeo original.
- Por ora há um estilo e opções de posição, tamanho e palavras por linha. O contrato e o pacote `subtitles` permitem adicionar estilos sem mudar o fluxo de análise/exportação.
