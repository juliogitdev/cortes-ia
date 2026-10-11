# W16 — contrato de aparência das legendas

`SubtitleSettings` 1.1.0 adiciona `text_color`, `highlight_color`, `outline_color` (`#RRGGBB`) e `outline_width` (inteiro de 0 a 8). `font_scale`, posição e palavras por linha permanecem. Registros 1.0.0 sem os campos novos usam branco, amarelo, preto e contorno 5. `AnalysisRequest` 1.2.0 aceita a configuração; requisições antigas 1.0.0 e 1.1.0 continuam válidas.

O GET de revisão de legendas devolve `settings` efetivas. O PUT aceita `settings` para criar nova exportação e preserva a configuração anterior quando ela não é enviada. Cores são validadas antes de chegar ao FFmpeg; o módulo converte RGB para a ordem BGR exigida por ASS/libass. O hash de cache inclui o documento ASS, portanto alterações visuais criam outro arquivo sem sobrescrever versões anteriores.

Exemplo completo: `docs/contracts/v1/analysis_input.json`. Schemas e OpenAPI atualizados. Consumidores revisados: API, worker, renderizador de legendas, painel React e testes.
