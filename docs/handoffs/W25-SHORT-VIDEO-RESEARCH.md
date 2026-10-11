# W25 — pesquisa sobre cortes curtos e revisão do seletor

## Entrega

- Pesquisa de fontes primárias do TikTok, documentação da OpusClip e estudos sobre métricas de vídeos curtos, com observação, interpretação e hipótese separadas em `docs/research/W25-short-video-quality.md`.
- Auditoria local: seis gravações, nove análises concluídas, quatro eventos de feedback negativo (com repetição de clipe) e uma publicação com apenas um snapshot de views. Essa base não sustenta treinamento ou alegação de melhora de alcance.
- `src/clip_platform/selection/baseline.py`: ganho de densidade de fala limitado, penalidade moderada para densidade extrema e abertura administrativa, sinal de pergunta inicial. Regras versionadas como `windows-5-editorial-review`; score continua heurístico.
- `scripts/evaluate_selector.py`: comparação offline, somente leitura, entre candidatos armazenados e a seleção atual por sobreposição temporal e feedback.
- `tests/unit/test_engine.py` e `tests/unit/test_evaluate_selector.py`: casos dos novos sinais e da comparação.

## Verificação

- Suíte Python: 153 aprovados, um aviso de depreciação do TestClient.
- `git diff --check`: sem erros de whitespace; avisos de conversão LF/CRLF no checkout.
- Comparação offline: Yuri 11/15, dona master chef 9/10 e Lula 4/5 regiões novas com IoU ≥ 0,5 em relação à análise armazenada. Isso mede continuidade temporal, não qualidade editorial nem viralização.
- Nenhum job em fila ou execução ao verificar antes da reinicialização dos serviços.

## Limites e próximo passo

- Não há curva de retenção, amostra de publicações comparáveis nem feedback positivo suficiente para aprender pesos com validade. Não houve coleta externa ou treino acionado por feedback.
- Rever manualmente top 5 de lives distintas, com avaliadores sem ver o score, e registrar versões finais, retenção e métricas em idades equivalentes quando a integração oficial permitir coleta por ação explícita. Usar divisão por live/período antes de promover outra regra.
