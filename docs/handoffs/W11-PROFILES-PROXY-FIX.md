# Correção do 404 ao criar perfil

O Vite em `frontend/vite.config.ts` não encaminhava `/profiles` para a API local. O GET retornava o HTML do painel e o POST recebia 404, embora a API tivesse a rota.

Incluído `profiles` na expressão do proxy. Verificação pela porta 8501: GET `/profiles` retornou `200 application/json`; POST inválido retornou `422` da API, confirmando o encaminhamento. Aplicação local permaneceu ligada e o túnel desligado.
