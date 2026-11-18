# Red team no P2: diagramas do que já está implementado

Esta página mostra **só o que existe no código**, em 31 testes verdes. O que ainda não existe aparece tracejado e marcado como "não existe". Os laboratórios de injeção e HTTP, o catálogo de ataques e as sondas estão fora do escopo desta fase.

**Legenda:** verde = pronto e testado · tracejado = ainda não existe · losango = decisão · pílula = fim (sucesso ou erro).

---

## 1. Mapa do pacote

```mermaid
flowchart LR
  subgraph P4["Repositório P4: pronto"]
    integridade["integridade.py<br/>snapshot e conferir"]
    workdir["workdir.py<br/>prepare_workdir"]
    esquema["esquema.py<br/>load_attack e load_catalog"]
    estatistica["estatistica.py<br/>wilson e taxa"]
    varredura["varredura.py<br/>valido, scan_text e main"]
    ataques[("redteam/ataques<br/>vazio: nenhum ataque ainda")]
  end
  subgraph P2["P2, somente leitura"]
    corpus["corpus/dispositivos.json"]
    gitp2["repositório git do P2"]
    mcp[".mcp.json com o server taxlaw"]
  end
  lsfiles["git ls-files do P4"]
  integridade -->|"lê o hash"| corpus
  integridade -->|"lê commit e status"| gitp2
  workdir -->|"copia sem .git e .venv"| gitp2
  workdir -->|"lê só o taxlaw"| mcp
  varredura -->|"lista os arquivos"| lsfiles
  esquema -->|"lê os arquivos"| ataques
  lab_inj["laboratório de injeção: NÃO EXISTE"]
  lab_http["laboratório HTTP: NÃO EXISTE"]
  sondas["sondas do ambiente: NÃO EXISTE"]
  lab_inj -.-> workdir
  lab_inj -.-> integridade
  lab_inj -.-> esquema
  lab_http -.-> integridade
  sondas -.-> workdir
  classDef feito fill:#e1f2e8,stroke:#1b6e41,color:#1b2330
  classDef falta fill:#f3f4f6,stroke:#8a94a6,color:#5a6678,stroke-dasharray:5 5
  class integridade,workdir,esquema,estatistica,varredura feito
  class lab_inj,lab_http,sondas falta
```

**Como ler.** Cada caixa verde é um módulo com testes. As setas sólidas são leituras reais do código. As tracejadas são ligações que só existirão quando os laboratórios forem escritos. `estatistica.py` não tem seta porque ainda não tem consumidor: o relatório que a usará não existe.

**O que prova.** Os cinco módulos funcionam sozinhos, cada um com seus testes.

**O que não prova.** Que um ataque real seja executado. Nada aqui chama o modelo nem a rede.

---

## 2. Ciclo de uma rodada (como a integridade protege o P2)

```mermaid
sequenceDiagram
  participant L as Laboratório rodada futura
  participant P as P2 original somente leitura
  participant C as Cópia de trabalho
  L->>P: snapshot: hash do corpus, commit e git status
  L->>C: prepare_workdir: copia sem .git e .venv
  Note over C: a rodada acontece só aqui, na cópia
  L->>P: snapshot de novo
  alt nada mudou
    L-->>L: conferir passa: rodada válida
  else algo mudou
    L-->>L: P2Mudou: rodada invalidada
  end
```

**Como ler.** O P2 original é consultado duas vezes, antes e depois. Entre as duas consultas, nada roda nele: a rodada acontece só na cópia.

**O que prova.** Se o P2 for alterado durante a rodada, a conferência detecta, com o nome da chave que mudou.

**O que não prova.** A rodada em si. O laboratório que a executaria ainda não existe; o diagrama mostra só o contrato de integridade.

---

## 3. Cópia de trabalho do P2 (`prepare_workdir`)

```mermaid
flowchart TD
  A["P2 original"] --> B["lê .mcp.json e pega só o server taxlaw"]
  A --> C["copia o diretório, ignorando .git, .venv, traces, __pycache__ e .pytest_cache"]
  C --> D{"o destino já existe?"}
  D -->|sim| E(["FileExistsError: nada é reaproveitado"])
  D -->|não| F["cópia criada"]
  B --> G["grava redteam-mcp.json com só o taxlaw"]
  F --> G
  G --> H(["cópia pronta para a rodada"])
```

**Como ler.** A configuração MCP da cópia leva só o server do P2 que o laboratório usará. Os outros servers do `.mcp.json` não entram, e a cópia não herda `.venv` nem `.git`.

**O que prova.** Um destino já usado nunca é reaproveitado por engano. A cópia não tem `.venv`, e a configuração só tem o `taxlaw` (dois testes).

**O que não prova.** Que a cópia rode. Ela só é preparada.

---

## 4. Conferência de integridade (`conferir`)

```mermaid
flowchart TD
  S1["snapshot antes: corpus_sha256, git_head e git_status"] --> S2["snapshot depois, com as mesmas chaves"]
  S2 --> C{"alguma chave ficou diferente?"}
  C -->|não| OK(["conferir passa: a rodada é válida"])
  C -->|sim| E(["P2Mudou: a mensagem diz quais chaves mudaram"])
```

**Como ler.** A comparação é chave por chave. Não há "parecido": um byte a mais no corpus já muda o hash.

**O que prova.** Três casos, testados: snapshots iguais passam; mudança no corpus e arquivo novo sem rastreio são detectados (três testes).

**O que não prova.** Que o P2 esteja "limpo". A linha de base já tinha duas alterações (`meister.config.yaml` e um `.bak`). A regra é "não mudou", e não "está perfeito".

---

## 5. Validação de um ataque no catálogo (`load_attack`)

```mermaid
flowchart TD
  F["arquivo JSON de um ataque"] --> J{"é JSON e tem os 6 campos?"}
  J -->|não| X(["ValueError com o nome do arquivo"])
  J -->|sim| I{"id no formato, como I1 ou H12, sem zero à frente?"}
  I -->|não| X
  I -->|sim| P{"superfície é injecao ou http, e o prefixo do id bate?"}
  P -->|não| X
  P -->|sim| N{"nome do arquivo é o id, e nucleo é booleano?"}
  N -->|não| X
  N -->|sim| R{"rotulos e previsao são objetos?"}
  R -->|não| X
  R -->|sim| OK(["Attack criado"])
```

**Como ler.** Cada losango é uma regra, na ordem em que o código a verifica. A primeira regra quebrada para tudo, com uma mensagem que cita o arquivo.

**O que prova.** Dez casos de erro e um de sucesso testados, mais a ordem do catálogo: injeção antes de HTTP, e por número dentro de cada uma (dez testes).

**O que não prova.** O conteúdo do ataque. O esquema valida só os campos comuns; o bloco de entrada e de critério será validado pelo laboratório que o usar. O diretório `redteam/ataques` está vazio.

---

## 6. Taxa com intervalo de Wilson (`wilson` e `taxa`)

```mermaid
flowchart TD
  A["k sucessos em n execuções"] --> V{"k entre zero e n, com n não negativo?"}
  V -->|não| E(["ValueError"])
  V -->|sim| Z{"n é zero?"}
  Z -->|sim| U(["intervalo de 0 a 1; taxa diz: sem execuções"])
  Z -->|não| P["p igual a k dividido por n"]
  P --> C1["centro<br/>p mais z ao quadrado sobre 2n<br/>dividido por 1 mais z ao quadrado sobre n"]
  P --> M1["meio<br/>z vezes raiz de p vezes 1 menos p sobre n,<br/>mais z ao quadrado sobre 4n ao quadrado<br/>dividido por 1 mais z ao quadrado sobre n"]
  C1 --> L["limites: centro menos meio, e centro mais meio, cortados em 0 e 1"]
  M1 --> L
  L --> T(["taxa: k/n = p por cento, IC 95 por cento de a a b"])
```

**Como ler.** O centro e a metade do intervalo são calculados separadamente, e depois se cortam os limites em 0 e 1. O caminho de `n = 0` é um atalho, para não haver divisão por zero.

**O que prova.** Os valores de 0 de 5, 2 de 5 e 5 de 5 batem com os esperados, e os casos inválidos e n = 0 são recusados ou tratados (oito testes).

| Caso | Taxa exibida |
|---|---|
| 0 de 5 | 0% (IC 95%: 0% a 43%) |
| 2 de 5 | 40% (IC 95%: 12% a 77%) |
| 5 de 5 | 100% (IC 95%: 57% a 100%) |

**O que não prova.** Que o relatório use essas taxas: ele ainda não existe.

---

## 7. Varredura de números de contribuinte (`main`)

```mermaid
flowchart TD
  A["git ls-files: arquivos rastreados"] --> B{"até 5 MB e UTF-8?"}
  B -->|não| S(["ignora o arquivo"])
  B -->|sim| C["quatro padrões com fronteira: CPF formatado, CPF puro, CNPJ formatado, CNPJ puro"]
  C --> D["tira pontos, barras e traços, e põe em maiúsculas"]
  D --> E{"dígito verificador válido?"}
  E -->|não| I(["não é achado"])
  E -->|sim| F["fingerprint: 12 caracteres do SHA-256"]
  F --> G{"o fingerprint está na lista de exceções?"}
  G -->|sim| I
  G -->|não| H(["achado: caminho, linha, tipo e fingerprint; sai com 1"])
  I --> N{"sobrou algum achado?"}
  N -->|não| OK(["nenhum CPF ou CNPJ válido; sai com 0"])
```

**Como ler.** O número nunca aparece na saída, só o fingerprint. A regra de dígito verificador é o que separa um CPF real de um número de processo com a mesma forma.

**O que prova.** Números válidos são achados, em formato puro e formatado; DV errado e número colado não são; arquivos binários são ignorados; a lista de exceções funciona; e o `main` sai com 1 ou 0 (sete testes). Na execução sobre o P4, nenhum achado.

**O que não prova.**
- Roda **à mão**. Não há gancho de commit nem CI, e a spec pede varredura automática.
- CNPJ alfanumérico em minúsculas não é coberto.
- Um número de 11 dígitos com DV válido por acaso vira achado; a solução é a lista de exceções pelo fingerprint.

---

## Resumo do que existe

| Módulo | Testes | Pronto para | Ainda falta |
|---|---|---|---|
| `integridade.py` | 3 | conferir o P2 antes e depois | a rodada que a usaria |
| `workdir.py` | 2 | preparar a cópia do P2 | o laboratório que roda dentro dela |
| `esquema.py` | 10 | validar a parte comum de um ataque | o conteúdo dos ataques |
| `estatistica.py` | 8 | calcular taxas com intervalo | o relatório que as usaria |
| `varredura.py` | 7 | achar CPF e CNPJ válidos nos arquivos | rodar automaticamente no commit |
| **Total** | **31** | | |

Plano: [`docs/superpowers/plans/2026-11-18-red-team-p2.md`](../superpowers/plans/2026-11-18-red-team-p2.md) · Spec: [`docs/superpowers/specs/2026-11-18-red-team-p2-design.md`](../superpowers/specs/2026-11-18-red-team-p2-design.md)
