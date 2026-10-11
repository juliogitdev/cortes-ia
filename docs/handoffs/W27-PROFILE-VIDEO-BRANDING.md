# W27 — cabeçalho de perfil e identificação do corte

## Entrega

- Perfil: link TikTok, nome exibido e foto enviada e validada; nome pode ser sugerido pelo oEmbed público no ato de salvar. Com conta autorizada, a API oficial fornece avatar, baixado apenas de domínios CDN do TikTok e armazenado localmente; foto manual tem prioridade.
- Nova análise: cabeçalho branco ativo por padrão em 9:16, nome e marca d'água pré-preenchidos do perfil, opção para desligar o cabeçalho e campos para sobrescrever identidade/chamada. Prévia estática do cabeçalho.
- Clipe: chamada curta individual derivada apenas de fala observada, editável no detalhe antes de nova exportação. `ClipEditorial` preserva legenda de post e hashtags separadas.
- Compositor: PNG 1080×360 com foto circular/nome/chamada, vídeo preservado abaixo, marca d'água posicionada dentro da imagem, hash incorpora a identidade. MP4s antigos não são sobrescritos.
- Contratos e OpenAPI atualizados: `EditorialProfile` 1.1.0, `VideoSettings` 1.1.0, `ClipEditorial` 1.2.0. Ver `docs/contracts/W27-profile-branding.md`.

## Verificação

- Suíte Python: 157 testes aprovados após integração; build e lint frontend concluídos (avisos preexistentes de effects).
- API de identidade e foto: teste com URL válida/inválida, foto PNG, GET local e avatar autorizado copiado da CDN do TikTok.
- Smoke FFmpeg real em CPU: MP4 2 s, 1080×1920, cabeçalho e marca d'água, 696 KB; quadro do cabeçalho gerado e inspecionado visualmente.
- Sem jobs ativos, serviços locais reiniciados; API e painel responderam HTTP 200.

## Limitações

- O link público permite sugerir o nome pelo oEmbed, mas não entrega uma foto oficial confiável; sem conta TikTok autorizada, a foto deve ser enviada pelo usuário. Isso é indicado no painel e documentado.
- A chamada automática usa ASR e pode herdar erro de transcrição. A prévia do formulário é estática e genérica; o título real aparece no detalhe de cada corte. Revisão humana continua necessária antes de publicar.
- A captura dos dez posts não informa retenção nem identifica versões exatas; nenhuma regra foi treinada com esses números. Seleção semântica de contexto e experimento cego com retenção comparável continuam como trabalho de avaliação, não como qualidade comprovada nesta entrega.
