# Entrega W1-ENGINE

Data: 2026-10-02. Cwd confirmado: C:/Users/Julio/Documents/cortes-ia. AGENTS, originais v1.1, STATUS, W1-delegacao e interfaces W1-00 consultados. A rodada W1 foi explicitamente atribuída pelo coordenador; registro anterior W0 não foi alterado por este agente.

Arquivos: src/clip_platform/speech/transcribe.py; src/clip_platform/selection/baseline.py; tests/unit/test_engine.py; este relato. Nenhuma dependência, contrato shared, mídia ou módulo alheio alterado; nenhum commit ou download.

Fala: faster-whisper importado apenas na chamada. Modelo exige diretório local CTranslate2 com model.bin, local_files_only=True. CPU int8 ou CUDA float16 escolhidos explicitamente; erro propaga, sem fallback. PT-BR, temperatura zero, beam 5, palavras ativadas e VAD desligado. Áudio integral fornecido pela interface tem offset zero no original; fragmentos com offsets diferentes exigem extensão coordenada da interface. Palavras são preservadas em provenance.settings.words de cada evidência, segmentos no transcript. Validação de finitude, limites e monotonicidade; áudio hash, parâmetros, versões faster-whisper/CTranslate2 e tempo incluindo carregamento/geração registrados.

Followup: identidade dos pesos inclui SHA256 de model.bin e repo/revision de download-manifest.json local quando presente. Hashing dos pesos fica fora de elapsed_s. Memória usa Windows ctypes GetProcessMemoryInfo.PeakWorkingSetSize ou Linux resource.ru_maxrss convertido para bytes; scope é pico de RAM durante toda a vida do processo, incluindo bibliotecas, não incremento exclusivo da transcrição nem VRAM. Retorna null em plataforma/API não disponível. Utilitário medido diretamente neste Windows: 28.917.760 bytes em processo pequeno sem modelo carregado, apenas prova da API de medição. Resultado de memória da inferência real precisa ser medido na execução correspondente.

Seleção: não importa mídia, UI ou backend de fala. Janelas determinísticas por segmento, modo exato/faixa respeitado, referência apenas a segmentos completos para não justificar citações cortadas; score de palavras por segundo, não probabilidade. Ordenação estável, IDs derivados do pedido/mídia/evidência, deduplicação por região sobreposta, top_k máximo. Pedido impossível, silêncio ou falta de fala completa retorna lista vazia com limitação. Instruções livres permanecem dados e não são interpretadas por essa heurística. Não há análise visual nem avaliação de qualidade editorial.

Teste: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_engine.py -q`. Resultado final: **11 passed**. Cobre seleção exata/faixa, estabilidade, referências, limites, silêncio, impossibilidade, top_k, falhas de backend, modelo ausente e timestamps inválidos/não monotônicos. Backend de fala e arquivos de pesos/áudio nesses testes são mocks sintéticos: não comprovam transcrição, CUDA ou compatibilidade RTX.

API conferida na fonte primária: https://raw.githubusercontent.com/SYSTRAN/faster-whisper/master/faster_whisper/transcribe.py (WhisperModel, word_timestamps, local_files_only; consulta 2026-10-02). Versão efetivamente instalada fica registrada em execução; master é referência de implementação, não lock de dependência.

Limitação do trabalho deste agente: testes do adapter usaram mocks. Na integração, o coordenador preparou pesos tiny e amostra artificial local,
executou inferência CPU real e registrou resultado em docs/evidence/W1-cpu-smoke.json (1,55 s fala; pico processo RAM 250023936 bytes).
GPU não executada. Densidade textual pode priorizar fala sem interesse editorial; um segmento maior que a duração pedida não gera candidato pois não é citado parcialmente.
Próximo: avaliar uma gravação representativa e manter gate RTX separado.
