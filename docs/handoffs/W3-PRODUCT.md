# W3 — avaliação, sinais multimodais e workspace

Responsável: sessão principal, execução sequencial sem subagentes. Data: 2026-10-02.
Usuário pediu desligamento da aplicação durante alterações; serviços desligados durante
edição, ligados somente para validar a live e desligados novamente antes deste relato.

## Arquivos

- `src/clip_platform/media/signals.py`: observação de energia RMS e mudança entre quadros.
- `src/clip_platform/worker/runner.py`: executa observadores após fala e registra indisponibilidade sem inventar evento.
- `src/clip_platform/selection/baseline.py`: filtra segmentos repetitivos, considera abertura, fim, possível continuação e sinais de imagem/áudio.
- `src/clip_platform/speech/transcribe.py`: descarta palavras com horários inconsistentes, preservando segmentos e registrando contagem.
- `src/clip_platform/ui/app.py`: navegação, métricas, grade, gerenciamento de projeto e configuração de downloads.
- `src/clip_platform/services/store.py`, `src/clip_platform/api/app.py`: renomeação de projetos e OpenAPI 0.5.0.
- `scripts/evaluate_analysis.py`: avaliação automática sem texto da transcrição; `scripts/start_local.ps1`: modelo local configurável.
- `tests/unit/test_engine.py`, `tests/integration/test_local_flow.py`: validações de sinais, interface e renomeação.

## Evidência e limites

A análise antiga da live contém 291 segmentos de fala, dos quais 257 são repetitivos pelo critério de frequência de palavras. O modelo Whisper small foi baixado para `models/whisper-small` com revisão 536b0662742c02347bc0e980a01041f333bce120 registrada em seu manifesto local. A análise integral com small concluiu com 3169 segmentos, só um repetitivo, 210 mudanças visuais, dois picos de energia e cinco MP4s de 26,23–46,61 s. O desvio máximo entre duração solicitada e exportada foi 0,02 s. A fala levou 486,2 s, incluindo carga e inferência, sem contar o job inteiro. O relatório em `docs/evidence/W3-live-comparison.json` mede sinais e horários, não compreensão do assunto ou avaliação humana. A etapa de fala correu em CUDA real; a observação visual e sonora usou CPU. Mudanças de quadro e picos de áudio não provam interesse editorial. A UI tem aparência de workspace SaaS, mas a implantação continua local e de usuário único, sem autenticação nem cobrança.

Testes: 102 passaram no `.venv`; 101 no `.venv-gpu` antes da última adição de teste visual. Integração API/painel e observação de mídia real passaram. `pip check`, compilação e `git diff --check` sem falhas. API OpenAPI 0.5.0 e painel responderam HTTP 200 na validação. A avaliação humana dos cinco cortes ainda é necessária para julgar início, conclusão e contexto.
