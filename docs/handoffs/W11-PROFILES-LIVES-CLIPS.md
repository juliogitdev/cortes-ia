# W11 — perfis → lives → clipes

## Entrega

- Perfis editoriais persistidos em SQLite com nome e plataformas TikTok, Instagram ou ambas. Um perfil pode guardar uma conta TikTok já autorizada; o Instagram é apenas organização editorial nesta etapa.
- Navegação inicial por perfis. Contas TikTok e lives antigas continuam visíveis; novas lives são atribuídas ao perfil escolhido. Lives existentes podem ser movidas pelo seletor de perfil.
- Cartões de lives mostram capa JPEG do vídeo de origem, gerada sob demanda por FFmpeg e mantida dentro da pasta autorizada de mídia. Renomear, associar conta/perfil, abrir e excluir seguem disponíveis.
- Ao abrir o clipe, a preparação editorial permite salvar legenda de publicação e estado rascunho, em revisão ou aprovado. O ajuste de limites, exportação, feedback e exclusão existentes foram mantidos.
- `Project` 1.2.0 adiciona `profile_id`; API 1.4.0 adiciona `/profiles`, atribuição de perfil, miniatura de origem e preparação editorial. Exemplos de schemas em `docs/contracts/w10/`; OpenAPI atualizado.

## Pesquisa de produto

- OpusClip: biblioteca de clipes, edição na transcrição, templates de marca e legendas visuais. https://help-center-preview.eng.opus.pro/ e https://www.opus.pro/brand-templates
- Vizard: calendário para programar clipes selecionados, editar e reagendar. https://help.vizard.ai/en/articles/10441547-how-to-schedule-using-the-calendar
- Descript: edição da transcrição e camadas/legendas no editor. https://help.descript.com/hc/en-us/articles/10165362727821
- Instagram: a API da Meta depende de conta profissional e permissões de publicação. https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api

Próximos diferenciais úteis: legendas no vídeo com estilo reutilizável, revisão visual antes do lote, calendário unificado por conta e controle de duplicidade entre TikTok e Instagram. Esta entrega implementa o estado de revisão e a legenda de publicação como primeiro passo; não afirma que o texto seja queimado no MP4 nem que Instagram publique ou colete métricas.

## Verificação

- `python -m pytest -q`: 121 aprovados, incluindo organização de perfis, cache de capas e persistência editorial.
- `npm run build`: aprovado; `npm run lint`: sem erros, avisos React já existentes.
- API testada sem iniciar servidor persistente. Aplicação e túnel seguem desligados, conforme pedido anterior.

## Limitações e próximo passo

- A associação de conta TikTok ao perfil não concede permissão OAuth: depende da conta já vinculada no sistema.
- Instagram requer implementação oficial de OAuth, publicação e métricas para contas profissionais; o painel deixa isso explícito.
- A legenda do clipe é um rascunho de texto para publicação. Renderização de legendas sincronizadas no vídeo e integração automática deste rascunho no agendador são próximas tarefas.
- Sem validação visual em navegador remoto nem publicação real, pois a aplicação permaneceu desligada e não há autorização de API social de teste.
