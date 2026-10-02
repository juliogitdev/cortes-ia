# Integração da onda 0

Data: 2026-10-02. Coordenador leu os três documentos, inventariou pasta/Git/host antes de escrever.
Pasta tinha somente docs; Git iniciado em main. Originais intactos conforme hashes da ADR 0001.
Delegação real para três subagentes, mesmo cwd, áreas exclusivas definidas antes da execução.
Todos entregaram; relatos W0-CONTRACT, W0-PLAN e W0-ENV revisados e incorporados.

Revisão corrigiu lifecycle e duplicidade de coletas/snapshots nos contratos, acentos dos exemplos,
reserva GPU independente do caminho de saída, identidade dos modelos e medição incompleta explícita.
Coordenador integrou dependências/estrutura/documentação e verificou o conjunto.

Evidências finais: 35 testes em 0,24 s; pip check limpo; compilação src/scripts;
8 JSON válidos e schemas sincronizados. Documentos preservados por SHA-256;
Git ignora dados/venvs/pesos/diagnóstico local. Lock fixa apenas dependências testadas da fundação.

GPU: CIM e PnP mostram AMD Radeon integrada, nvidia-smi ausente. Prova preparada e executada apenas
no caminho de pré-condições: pending/código 2, torch ausente, runs vazio. Nenhum modelo carregado;
versões CUDA, tempo de processamento e consumo de VRAM não medidos. Não extrapolar testes de schema.
Script de inferência real permanece não validado no host RTX; suas limitações estão em INSTALL.

Resultado: entrega da fundação concluída com pendência de hardware explícita; critério completo de saída
da onda 0 depende de W0-GPU. Ondas 1–6 apenas planejadas. Sem API, UI ou modelos de produto implementados.
Git sem commits/remoto; entrega por arquivos locais novos, não commitados. Estado e comandos em docs/STATUS.md.
Próximo: gate GPU no computador correto, depois W1-00 em nova rodada autorizada.
