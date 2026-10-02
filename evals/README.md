# Plano de avaliação inicial

Estado: plano e templates apenas. Nenhum benchmark de modelo, RTX ou seleção foi executado por esta tarefa. Mídias, anotações privadas e pesos ficam em storage/models ignorados ou em diretório externo. Os JSON deste diretório são sintéticos e não identificam pessoas reais.

## Amostras e preparação

Criar localmente seis tipos de fixture: conversa PT-BR; gameplay com pouca fala; fala com ruído; silêncio com ação visual; evento cruzando fronteira de bloco; marcadores audiovisuais para exportação. Para testes técnicos usar mídia produzida pelo operador ou com uso autorizado. Registrar hash, duração obtida por ffprobe, origem/autorização, FPS, tracks e offset original. Não baixar mídia nesta onda.

Separar validação de ferramentas e qualidade: marcadores sintéticos validam limites e sincronização; lives representativas autorizadas validam transcrição/cortes. Não atribuir qualidade editorial a uma fixture artificial. O nicho inicial será confirmado por Júlio antes da anotação representativa.

Júlio marca acontecimentos relevantes, limites, motivo e contexto necessário antes de ver ranking ou desempenho de publicação. Uma segunda revisão resolve divergências e preserva ambas as avaliações. Transcrição de subconjunto é revisada manualmente, incluindo nomes, sotaque, fala simultânea e ruído. Tempos são segundos no vídeo original, início inclusivo/fim exclusivo.

## Métricas e comparação

| Dimensão | Procedimento | Gate inicial |
| --- | --- | --- |
| Contratos | Exemplos positivos/negativos, referências cruzadas e limites | Sem referências inexistentes ou intervalos inválidos |
| Fala | WER contra transcrição revisada; erro absoluto de timestamps contra marcadores | Registrar erros por categoria; alvo numérico após benchmark |
| Cobertura | Acontecimento humano encontrado entre candidatos / acontecimentos marcados | Declarar regra de correspondência antes do teste; relatar omissões |
| Seleção | Cortes aproveitáveis nos primeiros cinco, ajustes necessários e motivos | Meta proposta: média de pelo menos 3/5; não é resultado obtido |
| Explicação | Revisor confere cada motivo contra evidência real | Eventos inventados impedem aceite do candidato |
| Exportação | ffprobe para duração; marcadores de som/imagem antes/depois | Tolerância proposta 0,2 s, sincronização inspecionada; confirmar no benchmark |
| Operação | Falha, cancelamento, repetição request_id, reinício e lease | Retomada sem duplicação e sem duas tarefas pesadas GPU |
| Eficiência | Tempo por etapa; RAM, VRAM e disco com método de medição | Valores reais por hardware/configuração; não extrapolar CPU para RTX |

Comparar mesmos pedidos de duração/top_k em baseline só fala, motor multimodal e candidatos humanos. Relatar qualidade da geração separada do ranking: um evento ausente não pode ser corrigido apenas reordenando. Fixar critério temporal de correspondência (por exemplo IoU e inspeção de contexto) antes de olhar resultados; não escolher limiar depois para melhorar a nota.

## Partições e proveniência

Dividir por gravação, publicação e período, nunca aleatoriamente por trecho. Conteúdo duplicado, revisões da mesma live e todos os snapshots de uma publicação ficam no mesmo grupo. Referências/treino não entram na avaliação final; dados posteriores não entram em previsões históricas. Versionar manifesto, configuração, modelo, regras, features e dataset; guardar hash de entradas e IDs de evidência. Métricas ausentes são nulas/ausentes; não publicado não equivale a desempenho zero.

O template annotation.example.json demonstra marcação humana; run.example.json demonstra um relatório sem resultados. Preencher null somente após uma medição real. GPU pending continua pendente até executar fala e visão em CUDA na placa alvo; mocks servem apenas às interfaces.

## Gate específico v1.1 na onda 4

Contador do coletor simulado deve permanecer zero no cadastro, GET, abertura da tela e consulta de progresso. Uma ação cria uma tarefa; clique repetido em andamento não chama novamente. Nova ação após conclusão cria novo snapshot. Falha conserva último resultado válido e estado Publicado; parcial não torna valores antigos atuais. Entrada manual registra revisor, instante e fonte. Evento duplicado não duplica coleção; feedback não treina. O conector real precisa de teste explicitamente autorizado, registrando capacidades efetivamente disponíveis e limites de acesso.
