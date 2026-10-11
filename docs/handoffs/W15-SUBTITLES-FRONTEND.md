# W15 — Configuração de legendas no painel

## Entrega

- O modal de nova análise agora separa "Vídeo e seleção" e "Legendas" em duas abas do mesmo fluxo, sem criar uma página isolada.
- A aba de legendas oferece ativação opcional, estilo `yellow_pop`, posição inferior/central, 2 a 6 palavras por linha e escala de fonte de 70% a 150%.
- A prévia visual é explicitamente ilustrativa; o texto mostrado nela não representa uma transcrição real.
- O envio de uma análise inclui `subtitle_settings` com `enabled`, `style`, `position`, `max_words_per_line` e `font_scale`. O botão impede valores inválidos.
- O detalhe do corte consulta palavras sincronizadas no endpoint de legendas e permite corrigir texto e tempos em segundos do vídeo original. Valida ordem, limites do corte, duração positiva e palavras não vazias. Enviar correções chama PUT e solicita uma nova exportação; a legenda de publicação segue independente.
- O editor também permite adicionar palavras ausentes e remover palavras indevidas. Um horário inicial é sugerido dentro do corte, sem preencher o texto da fala. Quando a transcrição vem vazia, há o botão "Adicionar primeira palavra".
- Para análise antiga sem legenda, o editor continua disponível. O usuário pode revisar as palavras e ativar legendas apenas naquele corte; o PUT envia `settings` com `yellow_pop`, posição inferior, quatro palavras por linha e escala 1.0. Uma nova exportação é solicitada sem reanalisar a live.

## Arquivos

- `frontend/src/components.tsx`
- `frontend/src/App.css`
- `frontend/src/api.ts`
- `frontend/src/types.ts`

## Testes

- `npm run build`: aprovado.
- `npm run lint`: aprovado, com sete avisos preexistentes de estado em efeitos React fora deste módulo.

## Limites e próximo passo

- A prévia representa apenas a aparência aproximada; sincronização, animação real e MP4 final dependem do módulo backend de legendas.
- Ainda não há inspeção visual automatizada em navegador nesta entrega. Após integração do backend, validar um corte com fala real, silêncio e interrupções, além da resposta de erro se a transcrição por palavras falhar. O editor de palavras pressupõe o contrato GET/PUT informado pelo coordenador.
