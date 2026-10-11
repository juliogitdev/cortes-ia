# W23 — zoom vertical e marca d’água dentro do vídeo

## Pedido e observação

Referência enviada em 03/10/2026: pessoa deve ocupar o quadro vertical, com margens pequenas se necessárias, sem cortar rosto. A composição anterior mantinha a live horizontal inteira sobre fundo desfocado, deixando os participantes pequenos. A marca antiga usava fonte serifada e podia ficar no fundo fora da cena principal. A análise `a6320486-c8df-4920-b733-4aed0af314bb` da live “dona master chef” tem dez cortes verticais e marca `@korteiclips` no canto superior direito.

## Correção

- Modelo oficial YuNet do OpenCV Zoo, local e ignorado pelo Git, substitui o detector Haar; detecta rostos frontais e de perfil. Instalador `scripts/install_face_model.ps1` fixa SHA-256 `8F2383E4DD3CFBB4553EA8718107FC0423210DC964F9F4280604804ED2552FA4`. Sem o arquivo, fallback preserva a cena inteira.
- Um rosto estável gera recorte 9:16 próximo. Movimento horizontal do rosto entre amostras desloca continuamente o recorte por interpolação. Dois participantes presentes juntos em boa parte da cena recebem dois painéis ampliados em vez de cortar um deles. Em caso incerto, conserva o quadro original sobre fundo desfocado.
- Marca textual vira PNG transparente com fonte sem serifa, fundo arredondado translúcido e margem interna. É sobreposta dentro da área do vídeo, inclusive no fallback, com margem vertical de 12% para não ficar apenas nas bordas removíveis. Texto do usuário não é interpolado no filtro FFmpeg.
- Cache de composição versão 6; versões antigas não são sobrescritas.

## Validação real

- Cena da live Lula com duas pessoas: dois painéis ampliados, ambos os rostos inteiros na inspeção visual.
- Cena de uma pessoa: 1080×1920, rosto inteiro, corpo ampliado e marca `@korteciclips` na imagem.
- Corte móvel da live “dona master chef”: quadros aos 2 s, 8 s e 20 s mostram foco acompanhando as pessoas, sem barras grandes; marca `@korteiclips` sobre o vídeo. Composição CUDA/NVENC e legenda do primeiro corte concluídas pelo worker.
- Smoke CUDA de remoção de silêncio e marca permaneceu funcional. Suíte Python: 143 testes aprovados, um aviso de depreciação Starlette. Os dez jobs de recomposição concluíram sem falha; dez MP4s legendados existem no disco, todos com vídeo 1080×1920, e estão selecionados nos dez cortes. MP4s anteriores preservados.

## Limites

YuNet é amostrado a cada 2 s e o foco interpola entre amostras; cenas com movimentos bruscos podem exigir ajuste manual futuro. O foco escolhe o rosto maior quando várias pessoas aparecem esporadicamente; não há diarização nem identificação do falante. O modo de dois painéis requer presença conjunta consistente. Não existe garantia de enquadramento perfeito em todo quadro.

Fonte técnica do modelo e licença MIT: https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet.
