# W24 — feedback, enquadramento e texto para postagem

## Entradas observadas

- Análise `d74a3d7c-68ad-4ef4-a9a9-2944e1ebd6d8`, live do Yuri: quatro eventos de feedback, três candidatos rejeitados. O candidato `81dd47...` contém pedido de likes e texto sem assunto independente; `e2b700...` e `17ce4...` receberam críticas ao enquadramento.
- As prévias dos dois últimos mostram uma gravação de tela com rostos dentro de vídeos exibidos na live. O detector escolhia o modo de duas pessoas e cortava a cena em painéis errados. Os rostos do lado direito mediam em alguns quadros apenas 15–64 px numa fonte 1920×1080.
- `select()` com a mesma evidência, após penalização de recados operacionais, já não inclui `81dd47...` entre as 15 sugestões. Isso é reavaliação local, não treino nem prova de melhora de viralização.

## Alterações

- `selection/baseline.py`: reduz o score de janelas com pedidos de likes, links de inscrição e recados operacionais. Scores continuam servindo só para ordenar.
- `media/presentation.py`: descarta detecções de rostos muito pequenos; reconhece o player vertical central em gravações de tela com uma faixa preta larga antes das recomendações e recorta os limites do player, mantendo a marca d'água sobre a imagem. Fora desse padrão, gravações com vários rostos preservam o quadro inteiro em vez de compor painéis errados. Também removeu o fundo da marca d'água e baixou a opacidade do texto. Quando o enquadramento continua ambíguo, o rosto principal pode ficar pequeno.
- `selection/social_caption.py`, `services/store.py`: sugestão de texto e hashtags extraída apenas de fala do trecho, nome da live e origem verificada. Retirou o fechamento repetido “O que você achou desse momento?”. A live `XBKuTcBuFKg` foi verificada com título e uploader `YURI22`; por isso seus cortes podem usar `#Yuri22`. Assunto incerto vira texto neutro, nunca uma citação inventada. Sugestões não sobrescrevem texto salvo pelo editor.
- `ClipEditorial` 1.1.0: campo `hashtags` separado; frontend permite editar, salvar, copiar legenda ou copiar legenda com hashtags em cada corte.

## Pesquisa externa

- [TikTok, Como recomenda conteúdo](https://support.tiktok.com/pt_BR/using-tiktok/exploring-videos/how-tiktok-recommends-content): hashtags são um sinal de conteúdo, junto com interações, som e outros sinais. Não há promessa de alcance por uma hashtag.
- [TikTok Creative Center, tendências de hashtags](https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/pt/): permite pesquisar tendências por hashtag e região. A busca pública de posts comparáveis em `tiktok.com/@` foi bloqueada por robots, então não foi usada como amostra quantitativa nem como prova de legenda ideal.
- [TikTok Newsroom, dicas para criadores](https://newsroom.tiktok.com/5-tips-for-tiktok-creators?lang=en): recomenda usar a descrição para contextualizar o vídeo e hashtags relevantes; hashtags genéricas como #FYP não garantem distribuição. Por isso a sugestão prioriza assunto e criador identificáveis no clipe.

## Verificação e limites

- Suíte completa: 146 aprovados; após as últimas mudanças, 25 testes focados aprovados. Build TypeScript/Vite aprovado. API `/health`, painel e leitura de legenda/hashtags via API local responderam 200.
- Os dez cortes recentes da live “dona master chef” foram reexportados; a prévia do primeiro confirmou a marca d'água menor e sem caixa. Os dois cortes do Yuri foram reexportados com o player vertical central ampliado; quadros dos MP4 finais confirmaram imagem e marca d'água dentro do player. Todos os 12 jobs terminaram sem erro, e cada novo arquivo é a versão selecionada do respectivo corte.
- A qualidade do texto depende da transcrição. O texto é apresentado como sugestão editável e deve ser revisado antes da postagem. Os feedbacks não dispararam treino. Dados e vídeos permanecem no storage ignorado pelo Git.
