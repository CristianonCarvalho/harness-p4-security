# Relatório do laboratório HTTP: server do P2 (spec B, seção HTTP)

- **Data:** 2026-11-18
- **Alvo:** o server `taxlaw.http` do P2 no commit `1a02e552` (linha de base). Medido em duas frentes: a réplica local (cópia do P2) e a VPS `mcpreforma.cristianocarvalho.cloud`.
- **Ataques:** H1, H2, H3, H4, H5, H8 e H9. H6 e H7 (CPF e CNPJ) e a injeção pelo texto da norma ficaram fora deste plano.
- **Medição:** réplica, três repetições por requisição; VPS, uma execução por requisição. Na rodada de 2026-11-18 foram três requisições (H1, H2 e H5); na de 2026-11-21, duas (H3 e H4). Cada rodada ficou abaixo do limite de 30.
- **Previsões:** escritas pelo Claude, a pedido do Cristiano, que não escreveu as suas. Cada uma está marcada como "Previsão do Claude" no campo `motivo`. O bloco do Cristiano não foi preenchido: os experimentos rodaram antes da previsão, então não há placar humano.
- **P2:** inalterado antes e depois de todas as rodadas. O `git status` continua com as duas linhas da linha de base.
- **Mitigações:** nenhuma foi aplicada. As recomendações abaixo são só isso.

## Resumo

- Seis das sete previsões acertaram. A errada foi o GET em `/mcp`.
- Na réplica, cada requisição deu o mesmo resultado nas três repetições. O GET não respondeu no prazo de 10 segundos nas três.
- Na VPS, H1, H2, H4 e H5 deram o mesmo resultado que na réplica. H3 não: a VPS respondeu 405 do nginx, antes de a requisição chegar ao app.
- Nenhum token ou número de contribuinte aparece nos registros. A varredura do repositório não acha nada.

## Fichas

| Ataque | Requisição | Previsão | Réplica (3 repetições) | VPS | Veredito | Estabilidade |
|---|---|---|---|---|---|---|
| H1 | `POST /mcp` sem autenticação | defendido, 401 (95%) | 401, 401, 401 | 401 | defendido | estável |
| H2 | `POST /mcp` com token de valor errado | defendido, 401 (95%) | 401, 401, 401 | 401 | defendido | estável |
| H3 | `POST /mcp` com `Host` fora da lista | defendido, 421 (55%) | 421, 421, 421 | 405 do nginx, não do app (2026-11-21) | defendido | estável |
| H4 | `POST /mcp` com `Origin` de navegador | defendido, 403 (50%) | 403, 403, 403 | 403 (2026-11-21) | defendido | estável |
| H5 | `POST /mcp` com corpo de 70 000 caracteres | defendido, 413 (70%) | 413, 413, 413 | 413 | defendido | estável |
| H8 | `GET /mcp` | defendido, 405 (60%) | sem resposta em 10 s, três vezes | não medido | inesperado | estável |
| H8 | `DELETE /mcp` | defendido, 405 (60%) | 405, 405, 405 | não medido | defendido | estável |
| H9 | `POST /mcp` com JSON malformado | defendido, 400 ou 200 (65%) | 400, 400, 400 | não medido | defendido | estável |

## Notas por ataque

**H1 e H2.** O server recusa a requisição antes de chegar ao SDK, com 401 e a mensagem `nao_autorizado`, na réplica e na VPS. A resposta não traz traceback.

**H3 e H4.** Na réplica, os dois são recusados pelo SDK, com 421 e 403. Na VPS, H4 deu 403, com a mensagem `Invalid Origin header`, que é do SDK: a requisição chegou ao app. H3 deu 405 do nginx 1.24.0, então a requisição não chegou ao app, e a checagem de `Host` do SDK não foi testada na VPS. A configuração de produção tem outros blocos de nginx além do arquivo do repositório: um `default_server` na porta 80 e os blocos de 443 do certbot. Pela leitura dessa configuração, o candidato mais provável é o primeiro bloco de 443, o de `chronoastro`. O mecanismo exato do 405 não foi confirmado por requisição nova. Detalhes em [previsao-vps-h3-h4.md](previsao-vps-h3-h4.md).

**H5.** O limite de 64 KB aparece duas vezes: no nginx da VPS e no SDK da réplica. Ambos respondem 413.

**H8, GET.** Com um token válido, o GET em `/mcp` não é recusado. O server abre um fluxo SSE e o mantém aberto, então a requisição não termina no prazo. A expectativa que escrevemos no catálogo (404 ou 405) estava errada para esse método. O veredito "inesperado" aponta para a nossa expectativa, não para uma falha comprovada. Ainda assim, uma conexão que não termina pode ocupar recursos do server, e isso merece uma decisão.

**H8, DELETE.** Recusado com 405 nas três repetições.

**H9.** O JSON malformado vira um erro de parse, com 400, sem traceback.

## Recomendações (não aplicadas)

- **H8, GET:** decidir se o server deve limitar o tempo ou o número de fluxos SSE abertos por cliente. Medir isso exigiria um teste de carga, que está fora do escopo porque é negação de serviço.
- **H1, H2, H5 e H9:** manter como estão. O comportamento é o esperado nos dois alvos.
- **H4:** manter. Foi medido na VPS e bateu com a réplica (403).
- **H3:** a dúvida sobre o `Host` voltou. O candidato mais provável é o bloco de `chronoastro` (ver as notas). Para fechar, falta confirmar o mecanismo do 405 com uma requisição controlada. Isso só se faz com decisão explícita, porque cada requisição à VPS conta.

## Limites

- Sete ataques, um commit do P2 (`1a02e552`) e uma data. Outro commit ou outro dia podem dar outro resultado.
- As previsões são do Claude. Sem o bloco do Cristiano, este relatório não mede a intuição humana.
- A VPS recebeu cinco requisições, uma vez cada: H1, H2 e H5 em 2026-11-18, e H3 e H4 em 2026-11-21. H8 e H9 não foram medidos lá. O H3 da VPS não testou a checagem de `Host` do SDK.
- O veredito compara com expectativas que escrevemos antes. "Inesperado" pode significar expectativa errada, como no GET.

## O que deu errado

- A primeira medição na réplica caiu com um timeout que não estava no plano. O GET em `/mcp` nunca responde no prazo, e o cliente não tratava esse caso. Corrigimos: um timeout agora vira um resultado sem status.
- Na primeira rodada da VPS, o token da área de transferência tinha 7456 caracteres, e não o token. A verificação de tamanho só olhava se havia mais de 32 caracteres, então deixou passar. A rodada parou na H5, com um erro de codificação. Pela ordem da lista, H1 e H2 provavelmente já tinham sido enviadas, e a rodada seguinte as repetiu. Corrigimos o gate, que agora registra erros no meio da rodada sem a mensagem.
- A primeira cópia do token deu 28 caracteres, em vez de 43. A cópia feita pelo Cristiano com o comando do guia funcionou. Uma tentativa minha de refazer a cópia foi bloqueada pelo sistema, e eu parei ali.
- A previsão do GET em `/mcp` estava errada. A expectativa do catálogo também estava.
- A previsão de H3 estava errada: a VPS respondeu 405 do nginx, e não 421 do SDK. A previsão partiu do arquivo `deploy/nginx-mcpreforma.conf`, que a produção não usa como está.
- Na rodada de 2026-11-21, a cópia do token no Mac deu 28 caracteres de novo. O `.env` da VPS tinha 43. A cópia foi refeita direto da VPS, com conferência do tamanho antes do envio.

## Próximos passos

- Decidir se o GET com token deve ter limite de tempo ou de fluxos abertos.
- Os CPF e CNPJ do H6 e H7, e a injeção pelo texto da norma, continuam sendo decisões do Cristiano.
- A medição da VPS e a da réplica estão em `docs/redteam/medicao-replica.json` e `docs/redteam/medicao-vps.json`. A rodada de H3 e H4 na VPS está em `docs/redteam/medicao-vps-h3-h4.json`.
