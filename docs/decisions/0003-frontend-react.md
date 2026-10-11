# ADR 0003 — frontend de produto em React

Data: 2026-10-02. O usuário rejeitou o painel Streamlit anterior por baixa qualidade visual
e legibilidade e pediu um frontend profissional, preparado para novas funções.

## Decisão

O frontend ativo passa a ser React, TypeScript e Vite em `frontend/`. Ele consome a API
FastAPI existente; o motor, fila, mídia, banco e contratos permanecem no backend. O
servidor local abre em 127.0.0.1:8501, com proxy para a API em 127.0.0.1:8000. O build
também é servido na raiz da API para facilitar uma implantação futura. O antigo painel
Streamlit permanece temporariamente como código legado e não é iniciado pelos scripts.

O desenho usa navegação persistente, visão geral, biblioteca de projetos, estúdio de
cortes, configurações e detalhes em painel lateral. Como referências funcionais, foram
consultados o [workspace e biblioteca do Descript](https://www.descript.com/tools/video-collaboration)
e o fluxo [gravação, Magic Clips, revisão e exportação do Riverside](https://riverside.fm/video-editor).
A implementação visual é própria. Não há cópia de código ou ativos dessas plataformas.

## Limites

O produto continua local, sem autenticação ou isolamento entre usuários. Preferências de
download são guardadas no navegador. Os MP4s e os dados continuam no disco local. O
frontend foi separado em cliente API, tipos, componentes, formatação e estilos para
receber novas áreas de publicação e aprendizado quando essas funções existirem.
