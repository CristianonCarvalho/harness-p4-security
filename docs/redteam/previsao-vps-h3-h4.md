# Previsão: H3 e H4 na VPS

> **Regra:** a previsão do Cristiano é escrita e commitada **antes** de qualquer rodada na VPS. A do Claude vem depois, em commit separado, e não substitui a sua. Não consulte `redteam/ataques/H3.json` nem `H4.json` antes de escrever: esses arquivos trazem a previsão do Claude.

## O que será medido

Duas requisições `POST /mcp` na VPS, com a autenticação correta. Só o cabeçalho muda.

| Ataque | Cabeçalho alterado | Valor |
|---|---|---|
| H3 (Host fora da lista) | `Host` | `exemplo.invalid` |
| H4 (Origin de navegador) | `Origin` | `https://exemplo.invalid` |

Sem CPF ou CNPJ em nenhuma das requisições.

## Previsão do Cristiano

Para cada ataque, escreva o resultado esperado (código HTTP), a confiança em porcentagem e o motivo.

| Ataque | Resultado esperado (código HTTP) | Confiança (0–100%) | Motivo |
|---|---|---|---|
| H3 | 421 | 70% | O SDK do MCP valida o cabeçalho Host contra os hosts permitidos e responde 421 (Misdirected Request), exatamente como ocorreu na réplica. Na VPS, se o Nginx repassar o Host original ($http_host), a requisição atinge o SDK e toma 421; se o Nginx filtrar antes pelo server_name no bloco virtual, pode responder 400. |
| H4 | 403 | 85% | O cabeçalho Origin simula uma requisição de navegador (cross-origin / CSRF). O Nginx repassa o cabeçalho Origin de forma transparente para o backend, e o SDK do MCP rejeita origens não autorizadas com 403 (Forbidden), replicando o comportamento estável da réplica. |

## Previsão do Claude

*Previsão do Claude (não do Cristiano), escrita depois da do Cristiano.*

| Ataque | Resultado esperado (código HTTP) | Confiança (0–100%) | Motivo |
|---|---|---|---|
| H3 | 421 | 80% | O arquivo `deploy/nginx-mcpreforma.conf` tem um único bloco `server`, na porta 80, sem `default_server` e sem bloco que recuse Host desconhecido. Um `Host: exemplo.invalid` cai nesse bloco e chega ao app, porque `proxy_set_header Host $host` repassa o valor. O SDK compara com o `TAXLAW_ALLOWED_HOST` e responde 421, como na réplica. |
| H4 | 403 | 85% | O Nginx não altera o cabeçalho `Origin`: ele só define `Host`, `X-Forwarded-For` e `X-Forwarded-Proto`. O P2 usa `allowed_origins=[]`, então o SDK recusa qualquer `Origin` de navegador com 403, como na réplica. |

Ressalva: li o arquivo de instalação. O certbot edita esse arquivo para HTTPS, então a configuração em produção pode ser outra. Não a conferi.

## Resultado

Rodada em 2026-11-21: duas requisições `POST /mcp` na VPS, com autenticação correta, uma execução de cada. Registros em [`medicao-vps-h3-h4.json`](medicao-vps-h3-h4.json). A assinatura da lista é `67155f65262fae9d653313c4dbd3949bce8ab9825e38dad77bc175fee7d3c9a8`.

| Ataque | Previsão do Cristiano | Previsão do Claude | Real | Veredito |
|---|---|---|---|---|
| H3 | 421 (70%) | 421 (80%) | 405 | inesperado: recusado, mas pelo nginx |
| H4 | 403 (85%) | 403 (85%) | 403 | bateu |

- **H3.** A resposta é a página `405 Not Allowed` do nginx 1.24.0 (Ubuntu), não uma resposta do app. A requisição não chegou ao SDK, então a checagem de `Host` do P2 não foi testada na VPS. As duas previsões partiram do arquivo `deploy/nginx-mcpreforma.conf` do repositório, que tem um só bloco na porta 80. Esse arquivo é o modelo de instalação, e a VPS roda outra configuração: há um `default_server` na porta 80 (`sites-enabled/default`, com `server_name _`) e os blocos de 443 gerenciados pelo certbot, que foram listados mas não lidos por inteiro. Um `Host` desconhecido caiu num desses outros blocos. Não confirmei qual bloco respondeu.
- **H4.** Veio 403 com o corpo `Invalid Origin header`, a mensagem do SDK. Isso mostra que a requisição chegou ao app e foi recusada pela checagem de `Origin`.
- **Limites.** Uma execução por requisição, e só essas duas. A conclusão de H3 vale para a configuração atual da VPS, não para o SDK.
