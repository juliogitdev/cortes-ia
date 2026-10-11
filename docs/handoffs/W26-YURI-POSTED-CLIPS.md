# W26 — revisão dos cortes publicados da live Yuri

## Observação

Imagem fornecida pelo usuário: dez posts em 3 de outubro, 14–34 s, 32–87 visualizações cada e nenhum comentário no momento da captura. A imagem não mostra retenção, compartilhamentos, alcance por origem nem a versão exata do arquivo enviado. Logo, não identifica sozinha a causa do desempenho.

Na análise local Yuri `d74a3d7c-68ad-4ef4-a9a9-2944e1ebd6d8`, candidatos ainda começavam ou continham operação da live: “vamos começar”, votação, meta de likes, links, site deslogando e troca de vídeos. O ranking de densidade de fala e os sinais de energia/quadro podem promover esses trechos sem entender se formam uma história autossuficiente. Este é um defeito editorial concreto da seleção, independente das métricas dos posts.

## Alterações

- `src/clip_platform/selection/baseline.py`: trechos com sinais observáveis de operação da live deixam de preencher `top_k`; o resultado pode ter menos cortes do que o solicitado. Regra conservadora baseada na transcrição, sem alegação de compreensão semântica.
- `tests/unit/test_engine.py`: verifica que duas instruções operacionais não entram no resultado e que a limitação é explícita.
- 154 testes Python aprovados. Comparação local em memória executada; ela mostrou que uma regra isolada deixa outros trechos fracos ocuparem as vagas, razão para não tratar a mudança como solução completa.

## Limites e próximo passo

Os posts já publicados não são alterados. Para uma seleção realmente melhor, avaliar início/contexto/desfecho com exemplos rotulados por live e revisão cega; depois comparar retenção de publicações do mesmo perfil em idade semelhante. Nenhuma métrica externa foi coletada automaticamente, e feedback não acionou treino.
