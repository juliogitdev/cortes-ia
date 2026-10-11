# Estado persistente — frontend React validado

## W29: checkpoint no GitHub antes dos escritorios

O estado atual da aplicacao foi preparado para versionamento antes da proxima etapa de escritorios multicanal. A suite Python passou com 157 testes e o frontend React compilou. Arquivos de midia, banco local, pesos e credenciais permanecem fora do commit. Relato: `docs/handoffs/W29-GITHUB-CHECKPOINT.md`.

## W28: arquitetura de escritórios e agentes

Foi desenhado o fluxo de escritórios com personagens em pixel art ligados a tarefas reais, handoffs versionados, revisão humana, quadro de métricas e conectores por plataforma. A proposta aproveita perfis, lives, jobs, TikTok e publicações já existentes, mas não ativa agentes autônomos nesta etapa. O usuário confirmou um escritório por marca, com até uma conta TikTok, uma Instagram e um canal YouTube inicialmente; Shorts é um formato do canal. Cada plataforma terá preset e variante próprios, com Shorts mais curtos como preferência configurável, sem cortar fala à força. Decisão em `docs/decisions/0004-office-multichannel.md`; arquitetura e ondas E0–E5 em `docs/architecture/office-agents.md`. Relato: `docs/handoffs/W28-OFFICE-AGENTS-ARCHITECTURE.md`.

## W27: identidade visual dos cortes por perfil

Perfil agora guarda link TikTok, nome e foto local; ao salvar o link, o nome pode vir do oEmbed público, e o @ é fallback. Foto oficial é copiada quando há conta autorizada; upload manual disponível. Nova análise 9:16 traz cabeçalho branco ativado, prévia, nome e marca d'água derivados do perfil, com opções para desligar/sobrescrever. Cada corte recebe chamada curta baseada na fala observada e editável antes de nova exportação. Composição 1080×1920 foi validada com MP4 real; contratos/OpenAPI versionados. 157 testes Python, build e lint frontend passaram. O desempenho dos posts e a coerência semântica das chamadas ainda exigem revisão e dados de retenção. Relato: `docs/handoffs/W27-PROFILE-VIDEO-BRANDING.md`.

## W26: revisão dos posts da live Yuri

A captura enviada pelo usuário mostra dez vídeos curtos com 32–87 visualizações cada e zero comentários no momento da captura; sem retenção e dados de distribuição, isso não permite atribuir causa ao desempenho. A análise local revelou defeito editorial verificável: o ranking ainda incluía instruções de votação, links, site e transições da live. O seletor agora omite janelas com esses sinais em vez de preencher artificialmente a quantidade pedida. Os posts existentes permanecem intactos; a triagem literal ainda precisa de avaliação humana e dados comparáveis para medir melhora. 154 testes Python aprovados. Relato: `docs/handoffs/W26-YURI-POSTED-CLIPS.md`.

## W25: pesquisa de cortes curtos e revisão do ranking

Fontes primárias do TikTok, documentação da OpusClip e estudos de métricas foram sintetizados em `docs/research/W25-short-video-quality.md`, distinguindo observações de hipóteses. Auditoria local encontrou seis gravações, nove análises concluídas, quatro feedbacks negativos com repetição e só um snapshot de views; ainda não há base para treinar ou afirmar ganho de alcance. O seletor agora limita o bônus de fala excessivamente densa, reconhece perguntas iniciais e reduz aberturas administrativas; regras `windows-5-editorial-review`. Um avaliador offline somente leitura compara a seleção antiga à atual. Em três lives, preservou 11/15, 9/10 e 4/5 regiões por sobreposição ≥0,5, respectivamente; isso mede continuidade, não viralização. Suíte Python: 153 aprovados. Relato: `docs/handoffs/W25-SHORT-VIDEO-RESEARCH.md`.

## W24: feedback da live do Yuri e texto de postagem

Quatro feedbacks da análise `d74a3d7c-68ad-4ef4-a9a9-2944e1ebd6d8` foram revisados. O ranking agora reduz recados operacionais como pedidos de likes; na reavaliação da mesma evidência, o trecho rejeitado por falta de assunto saiu do top 15. O detector reconhece o player vertical central em gravações de tela compatíveis e evita dividir rostos dentro de vídeos assistidos em painéis errados. Os dois cortes criticados foram reexportados e seus quadros conferidos. A marca d'água perdeu o fundo e ficou mais translúcida; os dez cortes recentes da live “dona master chef” também foram reexportados. Todos os 12 jobs terminaram sem erro e os arquivos novos estão selecionados. A sugestão de post perdeu a pergunta repetitiva, inclui criador e assunto quando sustentados pela origem/fala, oferece hashtags separadas e permite copiar/editar. Suíte completa: 146 testes aprovados; 25 testes focados aprovados após as últimas alterações; build frontend aprovado. API e painel locais respondem 200. Aplicação local continua ligada. Relato: `docs/handoffs/W24-FEEDBACK-POST-COPY.md`.

## W23: zoom vertical e marca d’água refeitos

Após a referência visual do usuário, o modo vertical passou a usar YuNet para enquadrar um rosto de perto, acompanhar seu movimento entre amostras e mostrar dois participantes ampliados em painéis quando aparecem juntos. Na falta de detecção confiável, mantém a cena inteira. A marca textual agora é uma sobreposição PNG com fonte sem serifa e fundo discreto, posicionada dentro da imagem do vídeo com margem de segurança. O modelo oficial foi instalado localmente em `models/` e seu instalador confere SHA-256; pesos não são versionados. Testes reais em cenas da live Lula e da live “dona master chef” tiveram enquadramento visualmente conferido; composição CUDA/NVENC e legenda concluídas. Os dez cortes da última análise foram recompostos: dez jobs concluídos, dez MP4s 1080×1920 presentes e selecionados, versões antigas preservadas. Suíte Python: 143 aprovados. API e painel responderam HTTP 200. Relato: `docs/handoffs/W23-VERTICAL-REFRAME-WATERMARK.md`.

## W22: apresentação dos cortes configurável

Nova análise oferece vídeo em pé (9:16), deitado (16:9) ou proporção original, remoção de silêncios e marca d’água textual em quatro posições. A composição mantém participantes em quadro por detecção conservadora de rostos; quando o corte não é seguro, conserva a cena completa com fundo desfocado. FFmpeg remove pausas de volume baixo e um mapa de tempo ajusta as legendas. Contrato `AnalysisRequest` 1.3.0, exemplos, esquema e OpenAPI atualizados. Smokes CPU e CUDA/NVENC geraram MP4s reais; 143 testes Python e build React aprovados. API, scheduler, worker CUDA e painel foram reiniciados sem jobs ativos; API expõe `video_settings` e painel respondeu HTTP 200. Relato: `docs/handoffs/W22-VIDEO-PRESENTATION.md`.

## W21: qualidade da transcrição e legendas da live do Lula

Diagnóstico real do áudio encontrou alucinações repetitivas dentro de segmentos Whisper, inclusive “pão de queijo”, propagadas aos cortes e legendas. O adaptador agora desativa condicionamento pelo texto anterior, rejeita loops locais e sequências de interjeições suspeitas, preserva horários do áudio original e registra intervalos suprimidos na proveniência. Ranking, editor e renderização protegem também análises antigas. Risadas ambíguas são omitidas; “(risos)” pode ser inserido manualmente após revisão. A reanálise integral `7ec04a28-744f-4972-bf36-b95fa306267f` concluiu com 1.606 segmentos, nenhum loop aceito, 18 intervalos suspeitos suprimidos e cinco MP4s legendados exportados e presentes no disco. 142 testes Python e build frontend aprovados. Erros pontuais de palavras ainda exigem revisão humana antes da publicação. Relato: `docs/handoffs/W21-ASR-QUALITY-LULA.md`.

## W20: aceleração GPU da exportação de vídeo

Modo CUDA agora usa NVDEC e NVENC H.264 nos cortes e nas versões legendadas; validação real na RTX local produziu MP4 H.264/AAC de 32 s e smoke das funções Python. Libass, AAC e tarefas leves continuam na CPU. Relato: `docs/handoffs/W20-GPU-VIDEO-PIPELINE.md`.

## Correção W19: análise parada em 88% na live Julio cocielo

A etapa visual do job original varria todos os quadros de uma gravação de 11.875 s e 3,06 GB, por isso permaneceu em 88% com FFmpeg ativo. O job foi cancelado; o worker agora usa CUDA para amostrar quadros chave quando configurado com CUDA, preservando horários originais e registrando a política na proveniência. Nova análise `7145fb49-5743-431c-9006-ed1c1e35e3f5` concluiu com cinco candidatos, 5.209 segmentos de fala distintos em 4.585 textos e 1.016 eventos visuais. Cinco MP4s legendados foram gerados e conferidos no disco. Suíte Python: 137 aprovados. Painel, API, worker e agendador mantidos ligados; API anterior à W17 ainda carregada. Relato: `docs/handoffs/W19-VISUAL-SAMPLING-STALL.md`.

## Diagnóstico W18: transcrição da live Ronaldinho e max

A análise anterior concluiu 10 MP4s, todos presentes, mas seus 2.614 segmentos de transcrição repetem a mesma frase; o ranking e os resumos desses cortes não são confiáveis. Amostras de 45 s e cinco minutos do áudio produziram falas variadas com o modelo local. O adaptador foi alterado para processar gravações acima de 600 s em blocos de 300 s, preservar offsets originais e rejeitar repetição extrema. Suíte: 137 testes aprovados. Os cortes existentes não foram apagados nem refeitos. O worker em execução ainda precisa carregar o código novo antes de reanalisar a live. Relato: `docs/handoffs/W18-RONALDINHO-TRANSCRIPTION.md`.

## Atualização W17: versões independentes de legenda

O original e cada renderização legendada agora aparecem como versões do corte. É possível gerar legendas em clipe antigo, editar e gerar outra versão, voltar ao original, baixar a versão escolhida e remover apenas um MP4 legendado local. A publicação individual ou em lote exige escolher uma versão explícita para cada corte; exclusão de versão em envio pendente é bloqueada. API/OpenAPI 2.0.0. Suíte Python: 135 aprovados; build frontend aprovado. Integração real TikTok não realizada por depender de conta/aplicativo autorizado. A tentativa de reiniciar somente API e worker foi rejeitada pela revisão automática do ambiente; painel e processos anteriores permanecem ligados, ainda sem carregar W17. Relatos: `docs/handoffs/W17-SUBTITLE-VERSIONS-INTEGRATE.md` e `W17-SUBTITLE-VERSIONS-UI.md`.

## Atualização W16: personalização e prévia das legendas

A nova análise e o detalhe do corte permitem configurar cor do texto, cor da palavra ativa, cor e espessura do contorno, tamanho, posição e palavras por linha. A prévia atualiza imediatamente sobre uma miniatura da gravação ou corte; o MP4 recebe as mesmas configurações visuais. `SubtitleSettings` 1.1.0, `AnalysisRequest` 1.2.0, API/OpenAPI 1.9.0. Suíte Python: 135 aprovados; build/lint e smoke Edge desktop/móvel aprovados. A prévia é estática e a sincronia permanece verificável no MP4 final. Relato: `docs/handoffs/W16-SUBTITLE-STYLE-INTEGRATE.md`.

## Atualização W15: legendas sincronizadas e revisão

A nova análise oferece uma aba Legendas com ativação, estilo amarelo animado (`yellow_pop`), posição, escala e quantidade de palavras por linha. O worker usa horários por palavra da transcrição no vídeo original para gerar MP4 legendado separado; o detalhe do corte permite corrigir/adicionar/remover palavras e horários e gerar outra versão sem sobrescrever a anterior. Cortes antigos podem receber legendas sem reanalisar a live. Falta de horários por palavra gera erro explícito, sem inventar alinhamento. API/OpenAPI 1.8.0; `AnalysisRequest` e `ClipRevision` 1.1.0. Suíte integrada: 134 testes aprovados; frontend build/lint e smoke Edge desktop/móvel aprovados. Aplicação local ligada; vídeo TikTok de referência não acessível pela ferramenta, estilo baseado na descrição. Relato: `docs/handoffs/W15-SUBTITLES-INTEGRATE.md`.

## Atualização W13: isolamento do painel por perfil

Selecionar um perfil agora define o contexto de todo o painel; visão geral, lives, tarefas, estúdio e resultados ficam restritos a ele. Troca explícita no topo/lateral volta à seleção sem logout. Lives antigas ficam em espaço sem perfil e podem ser organizadas na tela inicial. Criação de live herda o perfil/conta em uma transação; coleta de métricas por sessão ou ação explícita aceita escopo de perfil. API/OpenAPI 1.6.0. 124 testes Python, build/lint e smoke desktop/móvel aprovados. Painel, API, worker e agendador ligados; análise da live concluiu durante a mudança. Relato: `docs/handoffs/W13-PROFILE-WORKSPACES.md`.

## Atualização W12: cancelamento e exclusão visíveis

O estúdio agora oferece cancelamento para cada download em fila ou execução; a visão geral permite cancelar qualquer tarefa ativa. Na confirmação de excluir live, é possível cancelar as tarefas locais antes de remover os arquivos. Perfis editoriais agora podem ser excluídos sem apagar lives, mídia ou publicações. API/OpenAPI 1.5.0; 122 testes Python, build e lint frontend aprovados. Painel, API, worker e agendador continuam ligados; análise em execução preservada. Relato: `docs/handoffs/W12-DELETE-CANCEL-CONTROLS.md`.

## Correção W11: downloads duplicados

Na live `Ronaldinho e max`, o primeiro download do vídeo de 7.621 s terminou e gerou arquivo local de 3,15 GB. O segundo job era cópia do mesmo link e foi cancelado sem remover o asset. A fila agora reutiliza download ativo idêntico e o painel mostra estados de importação com mais clareza. 122 testes Python e build frontend aprovados. Aplicação local reiniciada e verificada; túnel desligado. Relato: `docs/handoffs/W11-DOWNLOAD-STATUS.md`.

## Correção W11: criação de perfil pelo painel

O proxy do Vite agora encaminha `/profiles` para a API. O 404 de criação foi reproduzido e corrigido; GET pela porta do painel retorna JSON e POST inválido chega à validação da API. Aplicação local ligada, túnel desligado. Relato: `docs/handoffs/W11-PROFILES-PROXY-FIX.md`.

## Atualização W11: perfis → lives → clipes

Perfis editoriais TikTok, Instagram ou ambos organizam lives com capa da gravação. Ao abrir a live, os clipes existentes continuam disponíveis; no detalhe do clipe agora há legenda de publicação e estado de revisão persistentes. Contas TikTok e lives antigas permanecem acessíveis. Instagram ainda é organização editorial, sem OAuth/publicação/métricas. `Project` 1.2.0 e OpenAPI 1.4.0. Testes Python 121 aprovados; build e lint do frontend aprovados. Aplicação e túnel desligados. Pesquisa, arquivos, limitações e próximo passo em `docs/handoffs/W11-PROFILES-LIVES-CLIPS.md`.

## Atualização W10: exclusão local de cortes e projetos

Exclusão de corte remove MP4 automático e de revisão manual, mostra explicitamente que o post TikTok permanece e impede remover MP4 com envio pendente. O painel de lives e o estúdio agora oferecem Excluir projeto: a live sai do catálogo e os vídeos/arquivos locais em sua pasta são removidos; publicações, vínculos, métricas e proveniência ficam no SQLite. Job local ou postagem TikTok pendente bloqueiam a operação. `DELETE /projects/{project_id}`, OpenAPI 1.3.0. Suite Python: 118 aprovados; build/lint do frontend aprovados. Aplicação e túnel seguem desligados. Relato: `docs/handoffs/W10-LOCAL-DELETION.md`.

## Atualização W9: contas → lives → cortes e métricas no vínculo manual

O painel inicia pela escolha da conta TikTok; cada conta abre as lives associadas e uma pasta separada guarda lives sem conta. Ao abrir uma live, o estúdio mostra os cortes e o acesso a publicar/resultados. A associação da conta à pasta é persistida; publicação aparece bloqueada com instrução quando falta conta ou permissão. O cadastro manual de um link TikTok consulta automaticamente as métricas do post, sem pedir números manuais; se a data não for informada, busca `create_time` na mesma consulta. GET não coleta. API/OpenAPI 1.2.0, Project 1.1.0. Testes Python: 116 aprovados; build/lint frontend aprovados. Aplicação e túnel mantidos desligados a pedido do usuário. Sem prova real do TikTok por falta de aplicativo/conta aprovados. Relato: `docs/handoffs/W9-ACCOUNTS-LIVES-METRICS.md`.

## Atualização W8: agendamento TikTok individual e em lote

Resultados agora permite configurar publicação imediata individual ou agendamento de um ou vários cortes. Para lotes, é possível escolher data/hora por vídeo ou intervalo em horas a partir de uma data/hora inicial. Cada vídeo tem legenda e visibilidade; comentários, duetos e costuras são definidos para o lote. Agendamentos persistem em SQLite, podem ser cancelados antes do envio, e um processo local iniciado por `start_local.ps1` os executa quando vencem. API/OpenAPI 1.1.0. Suite Python: 114 aprovados; build e lint do frontend aprovados. Postagem real depende de conta e aplicativo autorizados. Relato: `docs/handoffs/W8-TIKTOK-SCHEDULING.md`.

## Atualização W7: vínculos TikTok manual e automático

Resultados agora lista vídeos públicos da conta TikTok por ação explícita, permite escolher o post e registra vínculo manual. O envio pelo painel requer confirmação e escopo video.publish; a API guarda publish_id, envia o MP4 exportado e cria vínculo automático quando o TikTok confirma a postagem. O ID público pode chegar depois da moderação. API/OpenAPI 1.0.0 e exemplos atualizados. Testes Python: 113 aprovados; frontend build/lint aprovados. Nenhuma publicação real foi feita, pois ainda faltam aplicativo aprovado e conta autorizada. Relato em docs/handoffs/W7-TIKTOK-LINKAGE-POSTING.md.

## Atualização W6: vinculação de várias contas TikTok

O painel Resultados agora permite inserir a chave e o segredo do aplicativo TikTok e iniciar a autorização de cada conta pelo Login Kit. A API armazena tokens separados por open_id, renova cada um e associa publicações à conta usada na coleta. O segredo não é devolvido ao navegador. OAuth usa cookie de estado e retorno HTTPS; OpenAPI 0.9.0 e exemplo de contrato atualizados. Suite Python: 109 aprovados; frontend build e lint aprovados. A autorização real depende de aplicativo no TikTok for Developers, escopos aprovados e URL HTTPS cadastrada. Publicação direta de vídeos ainda não está implementada. Relato e instruções em docs/handoffs/W6-TIKTOK-ACCOUNTS.md.

## Atualização W5: live, TikTok e sinais afetivos

O estúdio agora agrega os cortes de todas as análises concluídas da live selecionada (duas análises, dez cortes no conjunto observado). O ranking de novas análises inclui expressões afetivas literais da transcrição, com proveniência e limitação explícita; não mede emoção real nem probabilidade de viralização. Foi preparado o conector oficial TikTok para consultar visualizações, curtidas, comentários e compartilhamentos uma vez por sessão de navegador, registrando tentativas e snapshots. A conta ainda não está conectada: falta aplicativo TikTok for Developers aprovado para `video.list` e autorização do perfil. Métricas manuais continuam disponíveis. Contrato OpenAPI 0.8.0 e relato em `docs/handoffs/W5-LIVE-TIKTOK-AFFECT.md`. Testes Python: 107 aprovados. Frontend build e lint aprovados. Acesso remoto validado com 10 cartões, MP4 carregado e sem erros JS. Aplicação e túnel ligados ao encerrar.

## Atualização: contagem de cortes no estúdio

O usuário observou 10 cortes no resumo e apenas um na tela. Os dados confirmam dois
conjuntos concluídos de cinco cortes no mesmo projeto; o total do resumo somava os
arquivos do projeto, enquanto a grade exibiu a análise selecionada. O estúdio agora
identifica cada análise e seus cortes no seletor, informa o total do projeto e quantos
cortes da análise estão visíveis. Trocar a análise limpa busca e filtro. No celular,
os cartões ficam empilhados e precisam de rolagem. Build e lint do frontend passaram.

## Atualização: resultados de publicações e acesso remoto

Foi criada a área Resultados para associar um corte exportado à publicação e registrar
métricas manuais com histórico e horário. API e SQLite persistem publicações e snapshots;
cadastro e consultas não coletam dados externos. Contrato OpenAPI 0.7.0.
O acesso remoto usa Quick Tunnel e uma instância separada da API protegida por senha.
Relato em `docs/handoffs/W4-PUBLICATIONS-REMOTE.md`. O hostname temporário depende de
internet e do PC permanecer ligado.

Correção posterior: acesso remoto com e-mail no Quick Tunnel apresentou `Failed to fetch`
e vídeos ausentes para o usuário, mesmo com API local saudável. O túnel passou a usar
HTTP/2 e uma segunda instância da API em 8001 protegida por senha HTTP Basic forte;
credencial fica apenas em `runtime/remote-auth.json`. Testes externos confirmaram 401
sem senha, 200 em projetos/miniatura, 206 em vídeo com Range. Navegador Edge remoto
carregou cinco cartões e metadados do MP4, sem erro JavaScript. O endereço muda ao
reiniciar o túnel; a senha permanece até ser trocada localmente.

## Atualização: painel reconstruído após feedback do usuário

O usuário rejeitou a aparência e a legibilidade do painel Streamlit anterior. O painel
ativo foi reconstruído em React/TypeScript com navegação persistente, visão geral,
biblioteca de projetos, estúdio, configurações, grade de cortes, modais e detalhes
laterais. A API e os vídeos existentes foram mantidos. As capas dos cortes vêm dos
próprios MP4s por um novo endpoint de miniatura; o original não é modificado.
`start_local.ps1` agora inicia o frontend Vite na porta 8501; o build fica disponível
também na raiz da API. O Streamlit continua somente como código legado.
Decisão: `docs/decisions/0003-frontend-react.md`. Relato: `docs/handoffs/W3-FRONTEND.md`.
O usuário pediu a aplicação desligada durante mudanças; os serviços foram parados antes
da edição, ligados apenas para inspeção visual e desligados antes dos ajustes seguintes.
Validação final: `npm run build` e `npm run lint` passaram (lint com quatro avisos de
estado em efeitos React); `npm run smoke` verificou cinco cortes, navegação, detalhes,
miniaturas, desktop e celular sem erro JavaScript; 102 testes Python passaram. O painel
foi iniciado novamente somente após a conclusão das alterações.

## Atualização: pedido de quatro etapas e painel estilo SaaS

Usuário autorizou avaliação da live, melhoria da fala, limites editoriais, sinais de
imagem/áudio e revisão visual do painel. A aplicação foi desligada a pedido do usuário
durante as alterações. Uma análise da live com Whisper small CUDA e faixa 25–65 s foi
retomada após as alterações e concluída. A primeira tentativa falhou por timestamp de
palavra fora do segmento; agora a palavra inválida é omitida com aviso de qualidade,
preservando o segmento. Na análise concluída, 41 palavras foram omitidas por esse motivo.

A avaliação automática da análise antiga achou 257 de 291 segmentos repetitivos com tiny;
a nova análise small registrou 1 em 3169 segmentos. Relatório em
`docs/evidence/W3-live-comparison.json`. Este número mede repetição, não qualidade
editorial validada por pessoa. O modelo small está preparado localmente e configurado
em `runtime/local-settings.json`.

Na live de 6994,38 s, a nova análise produziu cinco cortes com durações solicitadas
28,31 s, 38,53 s, 26,21 s, 28,09 s e 46,59 s. Os cinco MP4s foram exportados, com
desvio máximo de 0,02 s em relação ao pedido. A primeira passagem registrou 210
mudanças visuais e duas janelas de energia sonora elevada. Todos os cinco cortes têm
sinais de abertura e fim na transcrição; isso não garante conclusão do assunto.
A etapa de fala small levou 486,2 s incluindo carregamento e inferência no processo;
não é tempo total do job nem benchmark comparativo padronizado com tiny.

Código novo: seleção filtra transcrição repetitiva, considera abertura e continuação;
observadores de mudança visual e energia sonora alimentam evidências com proveniência;
painel tem visão geral, estúdio, projetos e configurações, com renomeação de projeto e
preferência de qualidade de download por sessão. Observadores não entendem semanticamente
o vídeo. Contrato OpenAPI 0.5.0 em `docs/contracts/w2`.
Verificação: 102 testes passaram no `.venv`; 101 passaram no `.venv-gpu` antes da última
adição de teste de observação visual. `pip check`, compilação e `git diff --check` sem
falhas. API e painel responderam HTTP 200 durante a validação. Revisão humana dos cinco
cortes segue necessária.

## Atualização: faixa de duração, galeria e feedback

O modo Faixa agora escolhe preferencialmente pausas ou finais de frase detectados na
transcrição, dentro dos limites configurados; quando não há sinal confiável, registra a
limitação. O modo Exata mantém a duração fixa. O painel apresenta uma grade de MP4s curtos
com descrição breve, detalhes da escolha, download, feedback e exclusão confirmada.
Excluir remove o MP4 automático e seu manifesto, oculta o corte e preserva original,
análise e avaliações. O score continua apenas uma ordenação, sem previsão de viralização.
Contratos em `docs/contracts/w2`, versão OpenAPI 0.4.0. Relato em
`docs/handoffs/W2-EDITORIAL.md`. Os cinco cortes antigos de 30 s permanecem inalterados;
é necessária uma nova análise no modo Faixa para usar a nova seleção. A transcrição tiny
da live de referência contém trechos repetitivos, então a descrição pode indicar que não
há resumo confiável e o limite escolhido não garante conclusão semântica do assunto.
Verificação: 98 testes passaram no `.venv`, `pip check` e `git diff --check` sem falhas.
Serviços locais reiniciados; API 200 com versão 0.4.0 e painel 200. Worker iniciou com
`device=cuda` conforme configuração local, sem nova inferência CUDA nesta rodada.

## Atualização: cinco arquivos de corte automáticos

Análises concluídas agora enfileiram uma exportação por candidato na mesma transação.
O painel reproduz os MP4s curtos, mostra duração/horário e link de download por corte.
O vídeo original não é usado como player de cada sugestão. Exportação H.264 CRF 18,
AAC 256k, resolução de origem e busca rápida com pré-roll; revisão manual preservada.
A análise existente de 5 candidatos de 30 s foi migrada sem reprocessar a fala:
5 MP4s concluídos, todos 30,03 s e 10,3–13,6 MiB. Quadros de cada corte foram
comparados aos instantes originais; erro médio máximo 2,99/255 em 160×90.
Evidência: `docs/evidence/W2-auto-cuts.json`. Relato: `docs/handoffs/W2-AUTO-CUTS.md`.
Nenhum vídeo antigo foi excluído; ranking ainda é baseline de fala.

## Atualização: fala CUDA no PC

RTX 5060 real detectada neste host. A primeira prova falhou por `cublas64_12.dll` ausente;
foi criado `.venv-gpu` com bibliotecas oficiais NVIDIA e inferência faster-whisper CUDA/float16
real concluiu em amostras de 3 s e 10 s. Worker integrado concluiu job audiovisual de 10 s
com um candidato. Configuração local ignorada pelo Git escolhe `device=cuda` em `start_local.ps1`;
API e painel seguem em `.venv`. Evidência: `docs/evidence/W2-speech-cuda-smoke.json`.
93 testes no venv GPU e `pip check` passaram. Visão/Qwen e inferência PyTorch não foram
testadas; W0-GPU completo permanece pendente. Recorte integral não foi benchmarkado na RTX.

Data: 2026-10-02. Módulo extensível de download implementado para YouTube, Vimeo, Twitch,
Dailymotion e TikTok, com melhor qualidade padrão e contrato para limite de altura futuro.
API, worker, fila persistida e painel integrados. `yt-dlp[default]` fixado no lock; YouTube
requer Node.js no PATH para extrair todos os formatos. W1 foi preservada e contratos W2
ficam em `docs/contracts/w2`. Relato: `docs/handoffs/W2-DOWNLOAD.md`.

Verificação atual: 93 testes passaram, `pip check` limpo. Colisão de chave do formulário
de download no Streamlit corrigida e coberta por AppTest. O link de referência do usuário
foi identificado como `LULA - Flow News #077`, duração 6994 s. Depois, o usuário concluiu
pelo painel o download integral (1.693.684.427 bytes) e uma análise CPU, conforme Store local.
Uma tentativa separada de 3 s via FFmpeg recebeu HTTP 403 da URL de mídia; `yt-dlp --test`
obteve fragmentos truncados. Outros provedores seguem sem prova real. Qualidade editorial
da live e visão GPU continuam pendentes.

## Histórico — onda 1

Data: 2026-10-02. Usuário confirmou notebook sem RTX, autorizou avanço e informou repositório juliogitdev/cortes-ia.
Estado atual: fatia local CPU integrada e verificada; destino remoto https://github.com/juliogitdev/cortes-ia.
NVIDIA/visão/CUDA permanecem pendentes para o PC. Desenvolvimento não está bloqueado por esse gate.

Entregas W1: contratos Project/Job/Export e OpenAPI congelado; ingestão/FFmpeg reais;
fila SQLite WAL, leases/fencing/idempotência/cancelamento; worker em subprocesso com reserva de processo;
transcrição faster-whisper local CPU int8/CUDA explícito, motor baseline só fala; API e painel local.
Helpers de start/stop, download explícito de tiny e FFmpeg portable, demo artificial e prova CPU.
Três agentes trabalharam em mídia, Store e fala/seleção, com áreas exclusivas; coordenador integrou API/worker/UI.

Prova real CPU: 30 s de vídeo artificial com voz Windows Maria pt-BR; tiny revisão d90ca5fe260221311c53c58e660288d3deb8d356,
faster-whisper 1.2.1, CTranslate2 4.8.2. Dois segmentos, um candidato e corte 20 s baixado;
fala 1,55 s (carga+inferência), fluxo 5,93 s; pico RAM do processo de fala 250023936 bytes (~238,4 MiB),
inclui bibliotecas/vida do processo, não é delta da etapa nem VRAM. Evidência resumida em docs/evidence/W1-cpu-smoke.json.
Relatório completo local runtime/diagnostics/local-smoke-clean.json. Nenhuma afirmação de qualidade editorial em lives.

Verificação integrada final: 74 testes passaram em 20,05 s; pip check limpo; compilação src/scripts;
start/stop reais com API e painel saudáveis em localhost. Há um aviso de depreciação Starlette/TestClient sobre httpx,
sem falha; não é erro da inferência. Código/modelos/dados mantêm fronteiras: só fontes/docs/locks/testes no Git.
Originais mantidos byte a byte, inclusive no clone via regras .gitattributes específicas.
Checkpoint atual na branch main; use git status e git log para conferir revisão/sincronização.

Próximo: clone/instalação no PC conforme INSTALL e prova real W0-GPU; anotar uma gravação representativa PT-BR para qualidade do baseline.
Fonte inicial dos links/nicho/tolerância continuam a confirmar antes da onda 2. Multimodal/coleta/treino não implementados.
Comandos atuais e jornada: docs/INSTALL.md e docs/RUN.md. Consulte também handoffs W1 e backlog.

## Histórico do checkpoint onda 0 (estado abaixo é anterior)

Data: 2026-10-02. Coordenador: sessão principal.

## Atualização 2026-10-03 — W14

Progresso por etapa e estimativa aproximada em minutos integrados para download, ingestão, análise/transcrição e exportação. Jobs 2.1.0; API 1.7.0. Painel mostra porcentagem total, porcentagem da etapa e último sinal do worker. Estimativa só aparece após avanço medido. Ver `docs/handoffs/W14-JOB-PROGRESS.md`.

Verificação atual: 127 testes Python aprovados; build e lint frontend aprovados (avisos React preexistentes). Aplicação local mantida ligada; API e worker reiniciados sem Jobs em execução, scheduler e painel preservados. API 1.7.0 e painel HTTP 200 verificados.
Estado: fundação integrada e verificada; gate RTX pendente por ausência de NVIDIA acessível.

Base: pasta originalmente com três documentos, sem Git. Repositório main iniciado, sem commits ou remoto.
Documentos originais preservados; hashes em docs/decisions/0001-fundacao.md.
Subagentes reais: contratos, planejamento e ambiente, áreas exclusivas em docs/tasks/W0-delegacao.md.
Nenhum agente implementa funcionalidades das próximas ondas.

## Entregas integradas

- Estrutura src/clip_platform com onze fronteiras modulares, tests/unit, contract e integration; storage/models ignorados.
- AGENTS.md, pyproject, .gitignore, README, .venv isolado e requirements-foundation.lock.txt.
- W0-CONTRACT: contratos Pydantic 1.0.0, três exemplos JSON e três JSON Schemas sincronizados, 35 testes.
- W0-PLAN: backlog pequeno por onda, dependências e aceite; plano de avaliação e dois templates sintéticos.
- W0-ENV: instalação PowerShell, diagnóstico e script para prova real sequencial de fala/visão.
- ADR 0001 e relatos individuais em docs/handoffs; consolidação em W0-INTEGRATE.md.

## Verificações finais

Python 3.11.0; Pydantic 2.13.5; pytest 9.1.1; setuptools 84.0.0. Todas as dependências da fundação congeladas no lock.
`python -m pytest -q` com Python do .venv: **35 passed in 0.24s**.
`pip check`: sem dependências quebradas. `compileall` em src/scripts: sucesso.
Oito JSON parseados; os três JSON Schemas iguais aos gerados pelos modelos Pydantic.
Diagnóstico PowerShell: sucesso; detectou somente AMD Radeon. Smoke: código 2, pending,
nenhuma inferência, torch ausente; modelos, tempos de inferência e VRAM usada **não medidos**.
Hashes dos três documentos originais conferidos e intactos. Ignorados: venvs, runtime, storage e models.

Git: main, sem commit base, sem remoto. Todos os arquivos de entrega são novos e não commitados;
os três documentos existentes continuam preservados. Não há branches de subagentes ou merges:
integração revisada no checkout compartilhado, com áreas exclusivas. Nenhuma API/painel funcional.

## Próximo passo

1. Executar diagnóstico no computador que contém a RTX e concluir W0-GPU conforme docs/INSTALL.md.
   Preservar hashes das amostras/pesos, versões, driver, tempo e memória reais. Não considerar esta fundação
   aceite completo do critério original da onda 0 até esse gate; nenhum teste CPU/mock o substitui.
2. Confirmar nicho, duração típica das lives, tolerância de processamento e fonte inicial dos links/métricas.
   Ponto de partida técnico já decidido: arquivo local em PT-BR.
3. Na próxima rodada autorizada, W1-00 fecha Job, Export e OpenAPI antes das tarefas independentes da onda 1.
   Nenhuma tarefa da onda 1 foi iniciada.

## Comandos de retomada

```powershell
Set-Location 'C:\Users\Julio\Documents\cortes-ia'
.\.venv\Scripts\python.exe -m pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/diagnose.ps1
.\.venv\Scripts\python.exe scripts/gpu_smoke.py
Get-Content runtime/diagnostics/gpu-smoke.json -Encoding UTF8
git status --short --branch
```

Instalação do zero e comando com pesos/amostras locais: docs/INSTALL.md. O smoke sem backend retorna
pendência esperada; não é teste de processamento aprovado.
