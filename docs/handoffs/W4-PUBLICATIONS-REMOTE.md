# Publicações manuais e acesso remoto

Execução sequencial pela sessão principal, sem subagentes. Data: 2026-10-02.

## Implementação

- `services/store.py`, `api/app.py`: cadastro de publicação vinculado à revisão,
  listagem e histórico de métricas manuais. Cadastro e GET não chamam redes externas;
  nenhuma coleta ou treino ocorre ao registrar feedback ou métricas.
- `frontend/src/PublicationsPage.tsx`: área Resultados para vincular o corte exportado
  a uma publicação e registrar visualizações, curtidas, comentários e compartilhamentos.
  Valores ausentes são exibidos como desconhecidos, não zero.
- `scripts/start_remote.ps1` e `stop_remote.ps1`: Quick Tunnel HTTP/2 com API remota
  separada na porta local 8001. `api/remote.py` exige autenticação HTTP Basic em
  todas as rotas, incluindo vídeos. Credencial aleatória persistida somente em
  `runtime/remote-auth.json`, ignorada pelo Git.

## Verificação e limites

O contrato OpenAPI foi atualizado para 0.7.0. O teste de integração cobre publicação,
métrica manual, persistência e ausência de coleta automática. Quick Tunnel precisa de
internet; o hostname é temporário e muda após
reinício. O PC precisa permanecer ligado, conectado e com API/worker/túnel ativos.
Coleta automática de métricas e contas de usuário SaaS continuam fora desta entrega.

Após falhas remotas observadas com a autenticação por e-mail do Quick Tunnel, a
entrada remota passou a usar senha da própria API. Conferência pelo endereço externo:
401 sem senha, 200 para projetos e miniatura, 206 para vídeo com Range; Edge headless
carregou cinco cartões, metadados reais de vídeo e API 200, sem erro JavaScript.
