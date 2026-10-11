# ADR 0004 — escritório multicanal com variantes por plataforma

Data: 11/10/2026. Estado: aceito pelo usuário para a arquitetura; implementação pendente.

## Contexto

O usuário quer cada escritório com TikTok, Instagram e YouTube Shorts, quando vinculados, e reconhece que o estilo e a duração ideais para seu conteúdo podem variar. Pediu Shorts mais curtos como preferência editorial. O modelo atual de perfil possui no máximo uma conta TikTok e uma configuração de vídeo por análise.

## Decisão

1. Um escritório representa uma marca/editoria. A primeira versão admite até **uma conta ativa por plataforma**: TikTok, Instagram e canal YouTube. Shorts é um formato do canal YouTube.
2. A live, o download, a transcrição e as evidências são compartilhados no escritório. O acontecimento gera `PlatformVariant` independentes, com limites próprios no vídeo original, preset de edição, MP4, texto de post, revisão, agenda e métricas próprios.
3. `PlatformPreset` é configurável por escritório e plataforma. Faixas iniciais para experimento: TikTok 25–60 s, Reels 20–45 s, Shorts 15–30 s. Não são regras oficiais; o motor não deve cortar uma fala para cumprir a faixa.
4. Uma variante só pode ser publicada na conta correspondente após aprovação humana dessa versão/hash e do texto que será enviado. Aprovar TikTok não aprova Instagram ou YouTube.
5. O escritório usa visão consolidada para operação, com números e fontes separados por plataforma/conta. Agregados só aparecem com definição e denominador comparáveis; dado ausente não vira zero.
6. Criar mais de um escritório é permitido no modo local. A restrição inicial é uma conta por plataforma dentro de cada escritório, não um limite global de escritórios.

## Consequências

- Migrar `EditorialProfile` gradualmente para `Office` e `ChannelConnection`, preservando IDs de lives, histórico e vínculo TikTok.
- Introduzir contratos versionados, exemplos, testes de isolamento e índices por escritório antes da interface em pixel art.
- Reusar worker de mídia com uma reserva de GPU pesada por vez. A variação de duração exige nova seleção de intervalos no material original; não encurtar mecanicamente um MP4 já editado.
- Integrações Instagram/YouTube dependem de autorização e capacidades confirmadas ao implementar; o escritório pode operar apenas com TikTok enquanto isso.
