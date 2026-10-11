# W3 — reconstrução do frontend

Responsável: sessão principal, sem delegação. Data: 2026-10-02.

## Mudanças

- `frontend/`: React/TypeScript, Vite, Lucide e fontes locais; lock npm versionado.
- Visão geral, biblioteca de projetos, estúdio, configurações, modais de criação e análise,
  grade de cortes e painel lateral de evidências, revisão e feedback.
- `frontend/src/api.ts` concentra integração com FastAPI; `types.ts` explicita os dados;
  `components.tsx` reúne unidades de interface; `App.css` mantém o sistema visual.
- `src/clip_platform/api/app.py`: serve o build na raiz e gera miniaturas JPEG de MP4s
  em `/exports/{id}/thumbnail`, sem alterar o vídeo original.
- `scripts/start_local.ps1` inicia Vite em 8501; `stop_local.ps1` encerra seu processo.
- `frontend/scripts/smoke.mjs` verifica navegação, grade, detalhes, desktop, celular e
  erros JavaScript em navegador Edge headless.

O painel Streamlit fica como implementação legada para preservar testes e histórico,
mas não é iniciado. A API continua em localhost e o frontend atual não implementa
autenticação, cobrança ou publicação. Referências e decisão: `docs/decisions/0003-frontend-react.md`.

## Verificação

- `npm run build`: passou; bundle de produção gerado em `frontend/dist`.
- `npm run lint`: passou, com quatro avisos sobre atualização de estado em efeitos React.
- `npm run smoke`: passou no Edge headless, com cinco cortes, navegação, detalhes,
  miniaturas e layouts desktop/celular; sem erros JavaScript nem rolagem horizontal móvel.
- `.venv/Scripts/python -m pytest -q`: 102 testes passaram; um aviso de depreciação
  externo do Starlette/httpx.
- Inspeção visual das capturas em `runtime/diagnostics/frontend-desktop.png` e
  `frontend-mobile.png`: vídeos e textos legíveis, controles presentes nas duas larguras.

Limites: o produto ainda é local e de usuário único; não há contas ou infraestrutura
multitenant. A miniatura é produzida sob demanda por FFmpeg e armazenada ao lado do MP4.

## Ajuste de contagem no estúdio

Após relato do usuário, a base foi conferida: duas análises concluídas com cinco cortes
cada. O resumo de projeto exibia dez arquivos, mas a grade pertencia somente à análise
selecionada. `App.tsx` agora nomeia as análises com índice e número de cortes, mostra
o total da análise na grade e explica a diferença para o total do projeto. Busca e
filtro são limpos ao trocar de análise. Build e lint passaram.
