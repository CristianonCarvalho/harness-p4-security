# Testes da guarda de CPF e CNPJ no P2 (H6 e H7): plano de implementação

> **Para quem executa:** REQUIRED SUB-SKILL: use superpowers:executing-plans (execução nativa) ou superpowers:subagent-driven-development. Os passos usam caixas `- [ ]`.
> **Para estudar:** cada tarefa tem um bloco **Para estudar**. Os passos marcados com **PORTÃO** dependem de você.

**Goal:** medir, na réplica local do server do P2, se a guarda de CPF e CNPJ bloqueia números de contribuinte sintéticos quando eles chegam numa chamada de ferramenta, em formatos canônicos (H6) e em formas disfarçadas (H7), e se algum número volta na resposta.

**Architecture:** módulos novos em `redteam/`. Um gerador de números sintéticos com dígito verificador válido, um conjunto de formas de apresentação do número, um veredito próprio para a guarda e a medição na réplica, reaproveitando o gate e a réplica do laboratório HTTP.

**Tech Stack:** Python 3.13, `uv`, `pytest`, `httpx`, `git`.

**Spec:** [`docs/superpowers/specs/2026-11-18-red-team-p2-design.md`](../specs/2026-11-18-red-team-p2-design.md), itens H6 e H7 do catálogo HTTP.

## Escopo deste plano

**Entra:** gerador de CPF e CNPJ sintéticos, formas de apresentação e detector, veredito da guarda, catálogo H6 e H7, medição na réplica com três repetições e relatório.

**Não entra:** a VPS. Números de contribuinte, mesmo sintéticos, não vão para o servidor público. A injeção pelo texto da norma e as sondas continuam fora.

## Restrições globais

- **Só dados sintéticos.** CPF e CNPJ são gerados em tempo de execução, com dígito verificador válido, e ficam só em memória durante a rodada. Nada é gravado com o número: o registro guarda o **nome da forma** e um **fingerprint**.
- **Nenhum corpo de resposta é gravado.** Só o veredito, o status, o nome das formas que apareceram na resposta e o fingerprint.
- **Um número novo por repetição.** Cada uma das três repetições de cada requisição usa um número diferente.
- **Só a réplica.** Nenhuma requisição desse plano vai para `mcpreforma.cristianocarvalho.cloud`.
- **Previsão antes da medição.** Como no laboratório HTTP, a medição recusa rodar com o motivo vazio. Se você não escrever a sua, a previsão será do Claude, marcada como tal.
- **O P2 não muda.** O `git status` do P2 deve continuar com as duas linhas da linha de base.
- **Varredura antes de cada commit.** Os arquivos novos não podem conter número com dígito verificador válido.
- Testes padrão offline. O teste que sobe a réplica continua marcado com `REDTEAM_INTEGRACAO=1`.

## Fatos do P2 que o plano usa

- A guarda roda antes da validação do SDK, em `TaxLawServer.call_tool`, e varre todos os argumentos de texto, inclusive chaves e listas aninhadas (`find_in_arguments`).
- Quando encontra um número válido, levanta `TaxLawError("dados_de_contribuinte", ...)`, que volta como erro da ferramenta com a mensagem `{"erro": "dados_de_contribuinte", "mensagem": ...}`. A mensagem diz quantos números e de que tipo, sem o número.
- A guarda usa `[0-9]` de propósito, e não `\d`. Dígitos de outro alfabeto não são reconhecidos.
- A ferramenta `buscar_dispositivos` ecoa a `consulta` na resposta. Se a guarda deixar passar um número, ele volta no corpo.

**Hipóteses a medir:** H6, formas canônicas, esperado bloqueado. H7, formas disfarçadas, esperado bloqueado, com a hipótese de que alguma passa e volta no eco.

## Revisão: entradas que a spec não cobre

1. Número gerado com dígito verificador inválido por engano: o teste do gerador pega antes da medição. *(Tarefa 1)*
2. Marcador `{CPF}` que sobra sem substituir na requisição: a medição recusa. *(Tarefa 3)*
3. Corpo de resposta com o número em uma forma que não está na lista: o detector não acha, e o veredito fica como "passou sem eco" quando o número não aparece em nenhuma forma conhecida. *(Tarefa 2)*
4. Chamada `tools/call` sem sessão ou sem `initialize`: a medição começa com um controle positivo, uma consulta benigna, que precisa devolver resultado. *(Tarefa 4)*

---

## Tarefa 1: Gerador de números sintéticos

**Para estudar:** o número sintético é a isca. Ele precisa ser válido o bastante para a guarda reconhecer e nunca pode ser um número real. A validade vem do dígito verificador, o mesmo algoritmo que a varredura já usa. O objeto que carrega o número esconde o valor no `repr`, para que um `print` acidental não o revele.

**Arquivos:** criar `redteam/sintetico.py`; teste `redteam/tests/test_sintetico.py`.

**Produz:** `gerar_cpf(rng) -> str`, `gerar_cnpj(rng, *, alfanumerico=False) -> str`, `fingerprint(numero) -> str`, e `class Sintetico` com `tipo`, `numero` (propriedade), `fingerprint` (propriedade) e `repr` sem o número.

- [ ] **Passo 1.1: testes**

Os testes pinam propriedades: o número gerado passa em `redteam.varredura.valido`, tem o tamanho certo, não tem todos os dígitos iguais, o `repr` não contém o número, e dois números gerados têm fingerprints diferentes.

- [ ] **Passo 1.2: implementação**

Use a mesma regra de dígito verificador de `redteam/varredura.py`, reaproveitando as tuplas de pesos. Sorteie a base com `random.Random`, e rejeite bases com todos os dígitos iguais.

- [ ] **Passo 1.3: rodar e commitar**

```bash
uv run pytest redteam/tests/test_sintetico.py -q
uv run pytest -q && uv run pytest -q
uv run python -m redteam.varredura
git add redteam/sintetico.py redteam/tests/test_sintetico.py
git commit -m "Gerador de CPF e CNPJ sinteticos com digito verificador valido" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 2: Formas de apresentação e detector

**Para estudar:** o modelo ou um atacante pode mandar o mesmo número em formas diferentes. A guarda reconhece algumas e outras não. O detector procura, na resposta, cada forma que o número pode ter, e devolve o **nome** das formas achadas. O nome é o que vai para o registro, no lugar do número.

**Arquivos:** criar `redteam/formas.py`; teste `redteam/tests/test_formas.py`.

**Produz:** `formas(sintetico) -> dict[str, str]` (nome da forma para o texto), `formas_no_texto(texto, sintetico) -> list[str]`.

As formas são as da spec: **pura**, **pontuada** (com os separadores do tipo), **espaçada** (um espaço entre cada dígito), **largura total** (dígitos e letras do alfabeto em largura total) e **caractere invisível** (um caractere de largura zero entre os dígitos).

- [ ] **Passo 2.1: testes**

1. Cada forma aparece no texto que a contém, e só ela é achada por `formas_no_texto` (o nome certo).
2. Um texto sem o número não acha nada.
3. A forma pontuada de CNPJ tem a estrutura certa.

- [ ] **Passo 2.2: implementação, rodar e commitar**

Implemente cada forma como uma função pequena com nome, e teste cada uma. Depois:

```bash
uv run pytest redteam/tests/test_formas.py -q
uv run pytest -q && uv run pytest -q
git add redteam/formas.py redteam/tests/test_formas.py
git commit -m "Formas de apresentacao do numero sintetico e detector" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 3: Veredito da guarda e substituição do marcador

**Para estudar:** o veredito de H6 e H7 não é o de `julgar`. Ali o que importa é se o número **voltou** na resposta, não só o status. Quatro resultados: **bloqueou** (o número não voltou e a guarda avisou), **vazou** (o número voltou em alguma forma), **passou sem eco** (a chamada seguiu e o número não voltou), e **inesperado** (qualquer outra coisa, inclusive erro de servidor).

**Arquivos:** criar `redteam/guarda.py`; teste `redteam/tests/test_guarda.py`.

**Produz:** `julgar_guarda(status, corpo, sintetico) -> str`, `substituir_marcadores(requisicao, sintetico) -> dict` (troca `{CPF}` ou `{CNPJ}` por um número novo, e levanta erro se sobrar um marcador).

- [ ] **Passo 3.1: testes**

1. Corpo com a mensagem `dados_de_contribuinte` e sem o número: **bloqueou**.
2. Corpo com o número em qualquer forma: **vazou**, mesmo com status 200.
3. Corpo sem o número e sem a mensagem, com status 200: **passou sem eco**.
4. Status 500: **inesperado**.
5. Marcador sobrando na requisição: `substituir_marcadores` levanta erro.

- [ ] **Passo 3.2: implementação, rodar e commitar**

```bash
uv run pytest redteam/tests/test_guarda.py -q
uv run pytest -q && uv run pytest -q
git add redteam/guarda.py redteam/tests/test_guarda.py
git commit -m "Veredito da guarda de CPF e CNPJ e substituicao de marcadores" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 4: Catálogo H6 e H7 e controle positivo

**Para estudar:** antes de medir um ataque, meça uma requisição benigna. Ela é o **controle positivo**: se a consulta sem número não devolver resultado, o problema está na chamada, e não na guarda. Sem esse controle, um "bloqueou" poderia ser só uma chamada mal formada.

**Arquivos:** criar `redteam/ataques/H6.json`, `redteam/ataques/H7.json`, e um controle `redteam/ataques/C0.json` (controle positivo, não entra na medição de ataques).

**Forma das requisições.** Cada uma é uma chamada `tools/call` à ferramenta `buscar_dispositivos`, com um argumento `consulta` que contém o marcador `{CPF}` ou `{CNPJ}`:

- **H6:** o número puro, o número pontuado, um CNPJ alfanumérico em maiúsculas, o número dentro de uma lista de argumentos. Espera-se **bloqueou** em todas.
- **H7:** as formas disfarçadas da Tarefa 2, cada uma com o número sintético. Espera-se **bloqueou**; a hipótese é que alguma forma passe e volte no eco.
- **C0:** uma consulta benigna, sem número, como "alíquota zero cesta básica". Espera-se **resultado com encontrado** no corpo.

- [ ] **Passo 4.1: testes**

Os testes carregam os três arquivos com o esquema e a validação de requisições, e conferem que o marcador é o único lugar onde o número entra.

- [ ] **Passo 4.2: criar os arquivos, rodar e commitar**

Crie os arquivos com as previsões em branco (`motivo` vazio). **PORTÃO:** a medição só roda depois de você escrever a sua previsão ou de eu escrever a minha, marcada como tal.

```bash
uv run pytest -q && uv run pytest -q
git add redteam/ataques/H6.json redteam/ataques/H7.json redteam/ataques/C0.json redteam/tests
git commit -m "Catalogo dos ataques H6 e H7 e controle positivo" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Tarefa 5: Medição na réplica

**Para estudar:** a medição roda o controle positivo primeiro. Se ele falhar, a rodada para, porque nenhum resultado de bloqueio vale sem ele. Depois roda H6 e H7 com três repetições, cada uma com um número novo. O registro guarda o nome da forma e o fingerprint, nunca o número.

**Arquivos:** criar `redteam/guarda_medicao.py`; teste `redteam/tests/test_guarda_medicao.py`; saída em `docs/redteam/medicao-guarda.json`.

- [ ] **Passo 5.1: testes com transporte falso**

1. O controle positivo que não devolve resultado interrompe a rodada.
2. Cada repetição usa um número com fingerprint diferente.
3. O registro gravado não contém nenhum número nem o corpo da resposta.

- [ ] **Passo 5.2: implementação**

Monte o `tools/call` com o argumento `consulta` substituído, envie pelo cliente da réplica (com o token), julgue com `julgar_guarda`, e registre: ataque, requisição, repetição, status, veredito, nomes das formas achadas e fingerprint. Use o `replica` do laboratório HTTP.

- [ ] **Passo 5.3: rodar na réplica, conferir o P2 e commitar**

```bash
uv run pytest -q
REDTEAM_INTEGRACAO=1 REDTEAM_P2_DIR=/Users/cristianocarvalho/Documents/harness/projeto02 uv run python -m redteam.guarda_medicao
git -C /Users/cristianocarvalho/Documents/harness/projeto02 status --porcelain
uv run python -m redteam.varredura
git add redteam/guarda_medicao.py redteam/tests/test_guarda_medicao.py docs/redteam/medicao-guarda.json
git commit -m "Medicao da guarda de CPF e CNPJ na replica, tres repeticoes" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

Esperado: o controle positivo devolve resultado; o P2 mostra as mesmas duas linhas da linha de base; a varredura não acha nada.

---

## Tarefa 6: Relatório

**Para estudar:** o relatório responde a pergunta do roadmap: a guarda aguenta? Ele separa o que foi **bloqueado**, o que **vazou** e o que **passou sem eco**, e diz qual forma escapou, se alguma escapou. A recomendação de mitigação é escrita e **não aplicada**: o P2 continua intacto.

**Arquivos:** criar `docs/redteam/relatorio-guarda.md`.

- [ ] **Passo 6.1: escrever o relatório**

Uma ficha para H6 e outra para H7, com: previsão, resultado de cada repetição, formas que escaparam (se houver), veredito, recomendação e risco residual. No fim, o controle positivo e os limites: a guarda testada é a do commit `1a02e552`, a réplica não é a VPS, e as formas são as que definimos.

- [ ] **Passo 6.2: confirmações finais e commit**

```bash
uv run python -m redteam.varredura
uv run pytest -q && uv run pytest -q
git add docs/redteam/relatorio-guarda.md
git commit -m "Relatorio da guarda de CPF e CNPJ" -m "Co-Authored-By: Claude Haiku 5.5 <noreply@anthropic.com>"
```

---

## Autoavaliação do plano

**Cobertura:** gerador (Tarefa 1), formas e detector (Tarefa 2), veredito e substituição (Tarefa 3), catálogo e controle (Tarefa 4), medição (Tarefa 5) e relatório (Tarefa 6).

**Fora deste plano:** a VPS, a injeção pelo texto da norma e as sondas.

**Pontos que a execução confirma:** a mensagem exata de erro da guarda no corpo da resposta JSON-RPC (a medição vai mostrar), e se a chamada `tools/call` precisa de `initialize` no modo stateless (o controle positivo responde a isso).

## Escolha de execução

Este plano tem seis tarefas, com dependências claras: gerador e formas antes do veredito, veredito antes do catálogo, catálogo antes da medição. Recomendo a **execução nativa**, como nas etapas anteriores.
