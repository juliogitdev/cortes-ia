# W16 — personalização visual de legendas no painel

## Entrega

- `frontend/src/components.tsx`: controles reutilizáveis para cor do texto, destaque, contorno, espessura, escala, posição e palavras por linha. Prévia atualiza conforme cada ajuste na Nova análise e no detalhe do corte.
- `frontend/src/types.ts` e `frontend/src/api.ts`: `SubtitleSettings` tipado; nova análise envia os valores em `subtitle_settings` e revisão envia `settings` no PUT. O editor carrega as configurações efetivas do GET, com padrão para revisões antigas.
- `frontend/src/App.css`: apresentação dos seletores e da prévia responsiva.

## Verificação

- `npm run build`: aprovado.
- `npm run lint`: aprovado, com sete avisos React preexistentes em outros componentes.

## Limites e integração

A prévia é uma representação visual da aparência; a sincronização por palavra é verificada no MP4 produzido pelo backend. O GET `/analyses/{analysis_id}/candidates/{candidate_id}/subtitles` precisa fornecer `settings` efetivas e o backend aceitar as quatro propriedades de cor/contorno no contrato W16. Revisões sem ajustes salvos recebem branco, amarelo, preto e contorno 5 como padrão. Depois da integração, verificar no navegador que um corte revisado conserva as escolhas ao reabrir.
