# Diagnóstico e correção de downloads duplicados

Na live `Ronaldinho e max`, dois jobs de download do mesmo URL foram enfileirados. O primeiro (`6adb74b1-875d-44e9-8a2a-f2350476878b`) concluiu; o asset local existe, possui 3.150.439.905 bytes e duração registrada de 7.621,341 s. O segundo (`02029af6-e3a3-4471-8c35-7bfaa3c0681f`) seguia em execução no yt-dlp; foi cancelado pela API por ser redundante. O arquivo concluído foi preservado.

`Store.enqueue` agora retorna o download ativo quando o projeto, URL e configurações coincidem, mesmo com outra chave de idempotência. Um download diferente na mesma live é recusado enquanto outro está ativo; uma live com gravação pronta não aceita novo download. O painel passou a exibir os estados de importação e distingue tarefas aguardando das em execução.

Verificação: 122 testes Python aprovados, incluindo repetição de download; build do frontend aprovado. Aplicação local reiniciada e checada: API e painel respondem; os jobs aparecem como `completed` e `cancelled`, e o asset permanece associado à live. Túnel desligado.
