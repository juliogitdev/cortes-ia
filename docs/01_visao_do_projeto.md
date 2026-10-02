# Visão do projeto de seleção de cortes de lives

Estratégia de produto e evolução da inteligência

Responsável pelo produto: Júlio César
Versão 1.1 | 2 de outubro de 2026

## 1 Propósito e resultado esperado

Construir uma aplicação local que receba o link de uma live gravada, identifique momentos interessantes e entregue cortes em vídeo para edição manual e publicação. O usuário acompanha o processamento em um painel visual, assiste às sugestões, entende os motivos da seleção, ajusta os limites e baixa os arquivos escolhidos.

O núcleo da aplicação será um motor independente de entendimento e seleção. Ele poderá ser utilizado sem o painel, receber dados de outras fontes e evoluir com referências, regras, correções e resultados de postagens. A estratégia prioriza a qualidade de toda a cadeia: dados incorretos na preparação podem comprometer até um bom modelo de seleção.

O produto estima potencial de atenção e adequação ao público. A pontuação ordena candidatos; não representa uma probabilidade comprovada de viralização. O sucesso será medido primeiro pela utilidade dos cortes e, depois, pelo desempenho observado das publicações.

## 2 Problema e proposta de valor

Assistir a várias horas de live para localizar poucos momentos publicáveis consome tempo. Cortes escolhidos somente pela transcrição podem perder ações visuais, reações e acontecimentos sem diálogo. Ferramentas genéricas também podem selecionar falas interessantes que não formam um vídeo compreensível.

A aplicação deve reduzir a procura manual, preservar contexto e aprender preferências específicas do usuário. A seleção deve considerar fala, imagem, sinais sonoros e a estrutura do acontecimento, mantendo uma justificativa verificável no material original.

O OpusClip serve como referência funcional, não como uma implementação a ser copiada. Sua descrição pública apresenta curadoria do vídeo e análise multimodal; os detalhes internos do treinamento não são publicados nas páginas consultadas. O projeto terá sua própria seleção, avaliação e evolução [1].

## 3 Público e premissas

O primeiro usuário é o próprio Júlio, como criador e operador. O sistema deve aceitar diferentes nichos e permitir perfis de preferência; gameplay, humor e conversas exigem critérios diferentes. A primeira validação deve se concentrar em um nicho e português brasileiro para reduzir variáveis.

O ambiente alvo é um computador com RTX 5060 de 8 GB de VRAM [2]. Sistema operacional, RAM, espaço em disco e plataforma inicial dos links serão confirmados na preparação técnica. O funcionamento inicial será local e para um usuário, sem exposição pública. Modelos, drivers e dependências precisam passar por um teste real de compatibilidade e consumo.

---

## 4 Escopo e prioridades

| Entrega inicial | Evolução planejada | Fora da primeira versão |
| --- | --- | --- |
| Link de gravação e upload alternativo | Novos conectores e fontes | Captura contínua de live ativa |
| Transcrição e análise visual | Análise sonora mais especializada | Edição automática completa |
| Sugestões com motivos e prévias | Ranking treinado com feedback | Alternância automática de câmeras |
| Ajuste de limites e download | Tendências por nicho e região | Legendas estilizadas automáticas |
| Registro e coleta sob demanda | Novos conectores de métricas | Publicação automática |
| Motor independente e versionado | Ajuste fino quando justificado | Treinar um modelo grande do zero |

O escopo inicial inclui gerar o arquivo cortado, mantendo imagem e áudio originais. O usuário faz reenquadramento, legendas, música e demais ajustes em um editor externo. Identificar pessoas não é requisito para cortar um intervalo; pode se tornar necessário na edição automática futura.

## 5 Jornada no painel

O usuário cria um projeto com link ou arquivo, duração exata ou faixa permitida, número de sugestões, nicho e orientação opcional. O sistema resolve os metadados disponíveis, apresenta título, miniatura, duração e origem e permite iniciar a análise. Campos indisponíveis devem ser identificados sem inventar informações.

Durante o trabalho, o painel mostra a etapa atual, progresso quando mensurável, avisos e falhas recuperáveis. Os resultados são apresentados em cards com player, título sugerido, início e fim, duração, prioridade, motivos, evidências e limitações. O usuário pode corrigir limites, gerar o arquivo, baixá-lo ou descartar o candidato.

Depois da edição, o usuário associa a publicação ao corte e registra o vídeo final ou uma descrição das alterações, plataforma, perfil, data e métricas. A área de resultados compara publicações em janelas equivalentes e exibe o histórico de hipóteses e versões.

## 6 Regras de negócio

RB01. Cada análise e cada corte pertencem a uma gravação identificada. Uma publicação aponta para a revisão do corte efetivamente utilizada.

RB02. Duração exata e faixa de duração são modos distintos. Se nenhum candidato atende ao pedido com qualidade suficiente, o sistema apresenta a limitação e oferece alternativas identificadas, sem alterar silenciosamente a duração.

RB03. Os horários sempre se referem ao vídeo original. O ajuste manual cria uma revisão e pode exigir nova avaliação da justificativa.

RB04. Selecionado, gerado, baixado, descartado e publicado são estados diferentes. Descartar um candidato não significa que ele teve baixo desempenho nas redes.

RB05. Repetições do mesmo acontecimento devem ser agrupadas ou removidas. Cortes publicados não podem ser excluídos do histórico por serem resultados negativos.

RB06. Falhas permitem retomar a etapa afetada. Excluir mídia não exclui automaticamente métricas, avaliações e proveniência; o painel explica o efeito da operação.

---

## 7 Estratégia da inteligência

A primeira passagem cobre toda a gravação, incluindo trechos sem fala, com transcrição, amostragem visual e descrições temporais. A segunda examina regiões promissoras ou incertas com mais contexto e mais imagens. Blocos sobrepostos reduzem perdas de acontecimentos que atravessam fronteiras.

Cada evidência deve preservar horário, origem, referência à mídia e configuração usada. Observação, interpretação e hipótese são campos separados. Indicadores de qualidade sinalizam dúvidas; uma nota produzida pelo próprio modelo não deve ser apresentada como confiança estatisticamente calibrada.

O motor procura abertura clara, desenvolvimento, conclusão, emoção ou surpresa, entendimento sem a live completa e adequação ao nicho. Características visuais e sinais de áudio complementam a fala. Relação com tendências é opcional e depende de dados recentes acessíveis, com origem e data registradas.

## 8 Aprendizado com resultados

O processo terá três camadas. Memória guarda exemplos e correções. Treinamento modifica um modelo de ranking ou, mais tarde, outros modelos. Avaliação verifica se a alteração melhora sugestões em material não utilizado no treinamento. Adicionar um arquivo à coleção não significa atualizar os pesos automaticamente.

Antes da publicação, o sistema registra a hipótese e a previsão. Depois, associa os resultados à versão editada. Visualizações isoladas não explicam por que um vídeo funcionou. A comparação considera perfil, plataforma, idade da postagem, nicho, edição, divulgação e métricas de retenção quando disponíveis.

| Dados de retorno | Uso esperado |
| --- | --- |
| Visualizações em 24 h 72 h e 7 dias | Comparação com publicações da mesma idade |
| Tempo médio e percentual assistido | Avaliação do consumo em relação à duração |
| Conclusão e curva de retenção | Localização de abandono quando disponíveis |
| Compartilhamentos e comentários | Taxas de interação com denominador registrado |
| Música edição hashtags e impulsionamento | Contexto do vídeo realmente publicado |
| Aprovação rejeição e comparação de cortes | Preferência editorial com motivo explícito |

Dados ausentes permanecem ausentes. Métricas de plataformas diferentes não são somadas sem normalização. Referências de terceiros sem contexto suficiente podem ajudar a reconhecer estruturas, mas não recebem o mesmo peso de resultados próprios bem registrados.

O sistema deve experimentar alternativas e manter resultados fracos, reduzindo o viés de aprender somente com os cortes escolhidos. Conteúdos não publicados não recebem recompensa zero. Hipóteses são reforçadas ou enfraquecidas por testes repetidos; postagens orgânicas fornecem associações, não uma prova automática de causalidade.

O treinamento inicial será do ranking, com modelos de entendimento já treinados. Ajuste fino será considerado somente quando erros recorrentes, dados adequados e medições de hardware justificarem seu custo.

---

## 9 Qualidade e critérios de sucesso

As metas abaixo são propostas iniciais de aceite. Júlio e o coordenador as revisam após o primeiro benchmark; não são resultados já obtidos.

| Dimensão | Critério inicial |
| --- | --- |
| Utilidade | Pelo menos 3 das 5 primeiras sugestões aproveitáveis em média no conjunto de validação |
| Cobertura | Medir quantos acontecimentos relevantes marcados pelo usuário aparecem entre os candidatos |
| Temporalidade | Horários válidos e sem deslocamento acumulado em toda a gravação |
| Arquivo entregue | Corte reproduzível com áudio sincronizado e duração verificada |
| Explicação | Motivos ligados a evidências reais sem acontecimentos inventados |
| Operação | Reinício recuperável e reprocessamento sem duplicação de resultados |
| Eficiência | Registrar tempo por etapa pico de VRAM RAM e uso de disco no hardware alvo |

Transcrição será avaliada em amostras revisadas, incluindo nomes, ruído, sotaque e falas simultâneas. A seleção será comparada com referências humanas e uma seleção simples por transcrição. A avaliação final usará lives separadas das referências e dos dados de treino, com divisão por gravação e por período.

## 10 Estratégia de entrega

A entrega começa com contratos e teste da GPU. Em seguida, uma fatia pequena percorre arquivo local, preparação, seleção, corte e painel. Só depois entra o conector de link escolhido. A análise multimodal é fortalecida com avaliações próprias; o feedback é armazenado desde cedo, e seu uso em treinamento vem após a qualidade do registro ser verificada.

O desenvolvimento será feito com multiagentes no Codex. Haverá um coordenador, responsáveis por módulos e revisão de integração. O plano detalhado define fronteiras de arquivos, contratos, dependências e testes. Os agentes de desenvolvimento não são modelos que ficarão executando dentro do produto.

## 11 Riscos e decisões pendentes

Os principais riscos são perda de acontecimentos na amostragem, erros de fala, limites de VRAM, fontes de download instáveis, dados de feedback enviesados e explicações pós resultado sem evidência. As respostas são inspeção adaptativa, correções humanas, processamento sequencial na GPU, upload alternativo, comparações planejadas e versões avaliadas antes de promoção.

Decisões a confirmar na fase inicial: sistema operacional; RAM e disco; origem inicial dos links; nicho de validação; duração típica das lives; tolerância de tempo de processamento; fontes de métricas disponíveis. Na ausência de resposta, o protótipo técnico começa com arquivo local em português e valida a RTX antes de assumir compatibilidade.

## 12 Referências

[1] OpusClip. How OpusClip Works e ClipAnything. Consultados em 02/10/2026. https://www.opus.pro/how-does-opus-clip-work e https://www.opus.pro/clipanything

[2] NVIDIA. Especificações da família GeForce RTX 5060. Consultadas em 02/10/2026. https://www.nvidia.com/pt-br/geforce/graphics-cards/50-series/rtx-5060-family/

Os detalhes de arquitetura, metas e etapas deste documento são decisões propostas para este projeto.

---

## 13 Análise de publicação sob demanda

Ao marcar um corte como Publicado, o usuário informa a plataforma, o perfil, o link da publicação e a revisão utilizada. Se o mesmo corte for publicado em mais de uma rede, cada publicação tem registro e histórico próprios. Registrar o link não dispara consultas à plataforma.

A tela da publicação oferece o botão Analisar publicação. Somente um clique explícito cria a tarefa de coleta. Não haverá agendamento, consultas periódicas nem coleta automática ao abrir a tela. O painel pode consultar o estado da tarefa interna em andamento; isso não deve provocar novas requisições de métricas à rede social.

O botão consulta as métricas que o conector consegue obter, registra o momento da coleta e a idade real da postagem, preserva o histórico e disponibiliza os dados validados ao módulo de aprendizado. A tela mostra os valores retornados, a última coleta bem sucedida, a origem, campos indisponíveis e o estado da tentativa atual. Atualizações posteriores também dependem de clique.

| Situação | Comportamento esperado |
| --- | --- |
| Link registrado | Publicação fica cadastrada sem coleta automática |
| Clique em Analisar publicação | Criar uma tarefa e apresentar andamento |
| Coleta completa ou parcial | Guardar snapshot e indicar os dados disponíveis |
| Link inválido acesso negado ou falha | Mostrar o motivo e preservar o último resultado válido |
| Métrica inacessível pelo conector | Permitir entrada manual com origem identificada |
| Dados validados | Incluir na coleção de aprendizado sem treinar automaticamente |

O link identifica a publicação; ele não garante acesso a todas as métricas. Retenção e outros dados privados podem depender de conexão autorizada à conta e de um conector compatível. A implementação deve confirmar essas capacidades para a plataforma escolhida e apresentar claramente os limites. O preenchimento manual permanece disponível.

RB07. A coleta externa é iniciada exclusivamente pelo botão. Cliques repetidos durante a mesma tarefa não criam consultas simultâneas para a publicação. Uma nova coleta após a conclusão cria outro snapshot, sem substituir os anteriores.

RB08. Publicado é um estado editorial. Nunca analisado, coletando, concluído, parcial e falhou são estados separados da coleta. Uma falha ao consultar não desfaz o estado Publicado.

RB09. Os snapshots preservam o horário de observação e a idade exata da postagem. As referências de 24 h, 72 h e 7 dias são janelas de comparação, não tarefas agendadas. Uma coleta aos dois dias não deve ser rotulada como resultado de 24 h.

RB10. Várias coletas da mesma publicação não são exemplos independentes de vídeos diferentes. A coleção agrupa o histórico por publicação e impede vazamento entre treino e avaliação. Métricas indisponíveis não viram zero; correções manuais mantêm proveniência.

RB11. Disponibilizar feedback à inteligência significa atualizar sua coleção de dados. Treinamento, avaliação e promoção de um modelo são etapas separadas, sem atualização de pesos disparada automaticamente pelo botão.

Aceite funcional: cadastrar uma publicação não gera requisição externa; um clique gera uma coleta; reabrir a tela não coleta novamente; falhas preservam o histórico; o snapshot validado é rastreável ao vídeo publicado e aparece como dado disponível para o aprendizado.
