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
| H3 | | | |
| H4 | | | |

## Previsão do Claude

*A ser preenchida depois, em commit separado. Não é a sua previsão.*

## Resultado

*A ser preenchido depois da rodada.*
