# W5 — Biblioteca por live, sinais afetivos e consulta TikTok

Data: 2026-10-02. Responsável: sessão principal. Checkout compartilhado confirmado em `C:\Users\Cesar\Documents\GitHub\cortes-ia`.

## Entrega

- O estúdio carrega todas as análises concluídas da live selecionada, agrega os cortes e preserva o vínculo de cada cartão com sua análise, revisão, exportação e descarte. O projeto observado tem duas análises de cinco cortes.
- A transcrição PT-BR passa por um detector determinístico de expressões afetivas literais. Ele registra observação, interpretação, hipótese e proveniência em segundos do vídeo original; o ranking usa contribuição pequena e limitada. Isso **não** identifica a emoção interna da pessoa nem estima probabilidade de viralização. Análises antigas permanecem com as evidências anteriores até reprocessamento.
- Publicações TikTok têm consulta pela Display API oficial, com execução idempotente, histórico de tentativas e snapshots. O painel solicita uma coleta por sessão de navegador quando a integração está conectada; também oferece atualização manual. Cadastro e GET permanecem somente leitura. Nenhuma conta está conectada neste ambiente.
- Contrato `PublicationCollectionRun.trigger` ampliado com `authorized_session_start`; OpenAPI 0.8.0 regenerado. Consumidores de `PublicationRecord` e do endpoint novo atualizados.

## Dependência externa

É preciso criar aplicativo em TikTok for Developers, obter aprovação para `video.list` e autorizar a conta publicadora pelo Login Kit. A configuração fica apenas em `storage/integrations/tiktok.json` (ignorado pelo Git): `access_token`, `refresh_token`, `client_key`, `client_secret`, `expires_at` (ISO 8601 com fuso). Tokens e segredo nunca devem ser enviados em chat ou versionados. Um domínio HTTPS fixo será necessário para concluir o fluxo OAuth web em produção; o Quick Tunnel troca de hostname a cada reinício. Até a aprovação e autorização, o painel mostra a integração indisponível e mantém métricas manuais.

Documentação oficial: https://developers.tiktok.com/docs/en/display-api-get-started ; https://developers.tiktok.com/docs/en/tiktok-api-v2-video-query ; https://developers.tiktok.com/docs/en/login-kit-web ; https://developers.tiktok.com/docs/en/oauth-user-access-token-management .

## Verificação e limites

Build TypeScript e lint passaram (avisos React de estado em efeitos). A suíte completa teve 107 testes aprovados. Navegador Edge pelo túnel confirmou 10 cartões, vídeo MP4 carregado, API 200 e nenhum erro JavaScript. A consulta TikTok real não foi testada porque falta aplicativo autorizado. O sinal afetivo depende da qualidade da transcrição e pode confundir citação, ironia e erro de ASR. A coleta uma vez por sessão usa `sessionStorage` do navegador, que representa aba/sessão web, não o evento de autenticação do proxy Basic.

Próximo: configurar domínio estável e fluxo OAuth depois da aprovação do TikTok; validar dados reais e revisar falsos positivos afetivos com amostras anotadas da live.
