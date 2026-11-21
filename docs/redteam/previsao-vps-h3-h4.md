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

*A ser preenchida depois, em commit separado. Não é a sua previsão.*

## Resultado

*A ser preenchido depois da rodada.*
