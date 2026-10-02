# Entrega W1-MEDIA

Checkout compartilhado confirmado em `C:/Users/Julio/Documents/cortes-ia`. Lidos AGENTS atualizado, STATUS, tarefa W1 e interfaces; originais v1.1 lidos na fundação e preservados. CPU apenas; nenhum modelo/GPU/dependência Python/configuração raiz alterados.

## Arquivos

- `src/clip_platform/ingestion/local.py`: cópia local com SHA-256, ffprobe, identificação estável por conteúdo, publicação atômica sem sobrescrever ingestão existente. Aceita contêiner audiovisual com áudio e vídeo; rejeita playlists/extensões não suportadas e corrupção.
- `src/clip_platform/media/tools.py`: descoberta env/PATH/portable, subprocess sem shell, timeouts e erro legível, probe JSON/hash.
- `src/clip_platform/media/audio.py`: WAV PCM s16le mono 16 kHz validado, escrita temporária+replace, original preservado.
- `src/clip_platform/media/export.py`: limites/referências/hashes validados, recodificação CPU H.264/AAC, corte no relógio original, duração tolerância 0,2 s e áudio/vídeo confirmados, publicação atômica sem sobrescrever artefatos. Sidecar `.export.json` preserva Export; retry valida hash, duração, IDs e revisão e retorna objeto idêntico sem recodificar.
- `scripts/bootstrap_media.ps1`: portable Windows com checksum fixado, manifesto e hashes executáveis; preserva distribuição existente divergente, sem alterar PATH/global.
- `tests/unit/test_media.py`: fixture audiovisual sintética com evento conhecido, testes reais e rejeições/limpeza.

## Origem e instalação

[FFmpeg oficial](https://ffmpeg.org/download.html) fornece fontes e aponta [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) para builds Windows. O executável é build desse distribuidor, não compilação oficial do projeto. Consulta em 02/10/2026. Baixado portable **9.0.2-essentials_build-www.gyan.dev**, arquivo de 109,4 MiB, para storage/tools ignorado.

[ZIP versionado](https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip); [checksum publicado](https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip.sha256). SHA-256 publicado e obtido: `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`.

Hashes executáveis locais: ffmpeg `3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec`; ffprobe `f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52`. Manifesto local em storage/tools/ffmpeg-manifest.json, versões confirmadas por execução. Script reexecutado e hashes anteriores conferidos antes de executar binários.

## Verificação

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_media.ps1
.\.venv\Scripts\python.exe -m pytest tests/unit/test_media.py -q
```

Teste real CPU: **6 passed**. Fixture 4 s, 160×120, 25 fps: evento aos 2 s muda vermelho/440 Hz para azul/880 Hz. Exportação [2,2;3,7) confirma duração 1,5 s com tolerância, primeiro pixel azul e frequência de áudio ~880 Hz; isso comprova conteúdo e sincronismo do evento, além de presença de tracks. PCM original e PCM do corte são mono 16 kHz s16le. Hash original permanece intacto; duplicata de ingestão reutiliza identificação; mídia inválida e corrupção são preservadas e temporários limpos. Tests dependentes de ferramentas reportam skip quando portable/PATH/env não existem; nesta execução **nenhum skip**.

## Limitações e próximo passo

Sem NVENC/GPU, link downloader ou normalização avançada de clocks/fontes. Timeouts atuais: probe 30 s, áudio/export 1800 s; calibrar com lives reais. Hashes leem arquivos inteiros para preservar proveniência, com custo de I/O. Recodificação tolera quadros/codecs, não promete precisão inferior a um frame. Aceite de sincronismo vale para fixture de evento conhecido; gravações com offsets incomuns precisam testes específicos. Subprocess allowlist de protocolos file/pipe impede consulta HTTP; playlists não são suportadas. Executáveis GPLv3 ficam fora do Git; cada computador roda bootstrap ou configura ferramentas existentes.

Coordenador pode integrar ingestão→áudio→export ao worker e executar e2e CPU. Stack de modelos/fala real e validação RTX são responsabilidades/gates separados.

## Revisão de integração: idempotência de exportação

Resultado final após correção: **8 passed in 3.92s**, sem skips. Os dois testes novos confirmam retry com objeto Export igual sem recodificação nem alteração de mtime; corrupção e destino sem manifesto são preservados com erro claro. Final MP4 e sidecar são publicados individualmente por hardlink atômico sem clobber. Após crash posterior à conclusão da exportação e anterior ao finish do job, retry reutiliza o artefato e manifesto. Uma queda na pequena janela entre publicação de MP4 e manifesto deixa par incompleto, preservado e sinalizado para inspeção; não há transação atômica entre dois arquivos nem sobrescrita automática de saída órfã.

## Revisão final: demuxers de entrada

Ajuda completa de ffmpeg e ffprobe 9.0.2 confirma suporte a `-format_whitelist`. Probe audiovisual e entradas de áudio/export impõem `mov,matroska,webm,avi,mpegts,mpeg` junto a protocolos file/pipe; validação de PCM gerado usa somente `wav`. Assim uma extensão .mp4 não habilita demuxers playlist/concat capazes de seguir caminhos locais externos à mídia enviada. Dois casos reais com HLS/ffconcat renomeados para .mp4 apontam para fixture local: ambos rejeitados pelo probe e cópia temporária limpa, originais intactos. A build já recusa detecção HLS com extensão não padrão; concat é explicitamente bloqueado pela whitelist. Nenhum demuxer adicional habilitado para contornar falha.
