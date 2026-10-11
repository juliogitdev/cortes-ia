# W21 — revisão da transcrição e das legendas da live do Lula

## Observações

Projeto `Minha gravação` (`e85e92c9-3183-4c41-a904-afbe6e09ea1c`), fonte de 6.994,381 s. A análise de 2026-10-03 `34af5e3f-7897-4c8c-8f34-c2bdc0d0f4ef` gerou cinco cortes, mas pelo menos dois continham segmentos com “Pão de queijo?” repetido dezenas de vezes dentro de uma única janela; havia 25 segmentos com repetição interna. A guarda W18 só detectava segmentos *inteiros* idênticos no conjunto total e não impedia esses loops locais.

Um teste real no áudio 0–300 s, usando a RTX local e o mesmo modelo `whisper-small`, reproduziu o erro com `condition_on_previous_text=True`: 19 segmentos, três com “pão de queijo” e um segmento de 564 caracteres com repetição. O mesmo trecho com `condition_on_previous_text=False` produziu 67 segmentos, 67 textos distintos e duas menções contextuais à expressão. Amostra de 60–155 s isolada também mostrou fala variada sobre debates, não a repetição salva na análise anterior. Estes são experimentos observados; não provam acurácia palavra a palavra.

## Alterações

- `speech/transcribe.py`: cada janela Whisper deixa de usar o texto anterior como condicionamento. Detecta loops internos por n-gramas e compressibilidade do texto, sequências de segmentos curtos idênticos e interjeições repetitivas como “ai ai ai ai”; suprime esses intervalos da transcrição e das legendas sem inventar texto ou emoção. Preserva offsets em segundos do original e registra intervalos suprimidos e sinais de confiança do modelo na proveniência.
- `selection/baseline.py`: não pontua segmentos com esses loops e evita janelas com múltiplos indícios explícitos de chamada promocional; esta regra editorial é limitada e auditável.
- `subtitles/render.py`: não grava automaticamente palavras de segmentos antigos que contenham loop; correção manual continua permitida.
- `api/app.py` e frontend: editor de legenda recebe intervalos suprimidos e informa que versões antigas já renderizadas permanecem como estavam. Cartões de clipes antigos com repetição mostram um aviso em vez do texto em loop.

Risada, choro e outras vocalizações sem fala reconhecível são omitidos quando o padrão textual é suspeito. O sistema **não** afirma detectar emoção real ou inserir “(risos)” automaticamente: isso exigiria classificador acústico validado. O editor permite inserir texto manual com horário confirmado, inclusive “(risos)”.

## Verificações e pendências

O adaptador atualizado processou os primeiros cinco minutos em CUDA: 67 segmentos distintos, duas menções a “pão de queijo”, nenhum loop suprimido nesse trecho. A reanálise integral intermediária `c649015c-bce8-44e7-b5aa-d046df356260` reduziu a repetição mas revelou uma variação quase idêntica em um segmento; a guarda por compressibilidade e a seleção promocional foram acrescentadas depois. A análise final `7ec04a28-744f-4972-bf36-b95fa306267f` concluiu com 1.606 segmentos, 1.585 textos distintos, duas menções contextuais a “pão de queijo”, nenhum segmento aceito pelo detector de loops e 18 segmentos suprimidos com intervalos na proveniência. Seus cinco cortes de 25,0–32,9 s foram exportados em MP4 legendado; todos os cinco jobs concluíram e os arquivos foram conferidos no disco (18,7–29,2 MB). O conteúdo ainda é transcrição automática e há erros de palavras isoladas que requerem revisão humana antes de publicar. Os cortes originais do usuário foram preservados.

Validação de código: suíte Python, 142 testes aprovados; `npm run build` do frontend aprovado após a dica de revisão manual.

Referência técnica primária: implementação e opções de `WhisperModel.transcribe` do faster-whisper (https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py), incluindo `condition_on_previous_text`, VAD e limites de compressão. A opção usada foi verificada no ambiente local, não apenas assumida pela documentação.
