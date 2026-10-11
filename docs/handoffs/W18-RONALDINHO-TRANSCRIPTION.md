# W18 — diagnóstico da live Ronaldinho e max

## Observação

Projeto `ff5b8608-106c-443c-86f2-594681cc44f1`, análise `6460a256-4af4-4e8d-b321-4c58c3d44c55`: vídeo fonte com 7.621,341 s; análise concluída; 10 exports concluídos e os 10 MP4s presentes. A transcrição persistida tem 2.614 segmentos, todos com o mesmo texto curto (“E aí”). Cada um dos dez cortes aponta para esse texto repetitivo. Logo, os arquivos foram gerados, mas o ranking e os resumos desta análise não são confiáveis.

## Experimentos

- Trecho curto do arquivo fonte, com o modelo `whisper-small` local em CUDA: idioma português detectado com confiança aproximada de 0,993; frases variadas reconhecidas.
- Trecho de cinco minutos do WAV da própria análise, mesmo modelo e parâmetros originais: 177 segmentos, 159 textos distintos. Isso mostra que o áudio possui fala inteligível e que o problema se manifesta na inferência da gravação longa em chamada única.
- Transcrição integral com VAD foi iniciada como diagnóstico, mas encerrada após mais de dez minutos sem resultado; não há evidência de que essa configuração isolada resolva o problema.

## Alteração

`speech/transcribe.py`: arquivos com mais de 600 s agora são processados em blocos PCM de 300 s. Horários dos segmentos e palavras são trazidos de volta aos segundos da gravação original. Uma guarda rejeita transcrições com 100 ou mais segmentos quando uma mesma frase ocupa 90% ou mais do resultado. O processamento de áudio curto permanece direto. Testes em `tests/unit/test_engine.py` cobrem offsets, proveniência e rejeição da repetição. Suíte completa: 137 aprovados.

## Limites e próximo passo

Os dez cortes existentes foram preservados e continuam baseados na análise inválida. A live precisa de nova análise com o worker atualizado para produzir sugestões confiáveis; depois, revisar os novos cortes antes de descartar os antigos. A aplicação aberta ainda não carregou o código novo. Não houve validação integral do arquivo de duas horas com o processamento em blocos nesta rodada. Nenhuma publicação TikTok foi alterada.
