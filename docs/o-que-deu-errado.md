# O que deu errado (P4, spec A)

> **Histórico e autocrítica.** As seções iniciais registram os fatos e o histórico técnico levantados no repositório (com checagens marcadas em 2026-11-20). A seção final traz a leitura direta e a autocrítica do Cristiano sobre os erros e o processo de trabalho.

O pipeline "agente abre PR, gates decidem" funcionou no lote final: o caso bom entrou com aprovação humana e os cinco ruins foram barrados, sem vazamento. O caminho até lá teve erros, e cada um ensinou algo.

## O que deu errado no caminho

1. **A spec descrevia o P3 de memória, e o P3 era diferente.** Previa um gate de cobertura que não existe, uma pasta `cases/` que já tinha outro uso e um `check-repo` que "reprovaria mudança de prompt". Só a leitura do código mostrou isso. *Mudaria:* ler o repositório alvo antes de escrever a spec.
2. **A premissa do caso 05 estava errada.** O ensaio à mão mostrou que editar o texto do prompt do juiz passa em tudo (733 testes e `check-repo` verdes). O gate só pega mudança no `config/run.json`. O caso foi trocado, e a lacuna ficou aberta no P3.
3. **Fixar as ações pelo hash não foi mecânico.** O "latest" do `github/codeql-action` devolveu o tag do bundle do motor (`codeql-bundle-…`), não o da ação, e o do `claude-code-action` devolveu o tag móvel `v1`. Foi preciso achar o tag de versão exato de cada uma antes de fixar o hash. O GitHub App (necessário porque PR aberto pelo `GITHUB_TOKEN` não dispara os outros workflows) também acrescentou passos manuais e segredos.
4. **A spec dizia que o workflow dos gates "vem sempre da `main`".** Com `pull_request` não é verdade: o PR pode editar o workflow que o julga. A defesa real virou guard, CODEOWNERS e checks obrigatórios.
5. **Sem créditos de API, a autenticação mudou no meio.** O plano usava uma chave da Anthropic; o caminho possível foi o token da assinatura. Um segredo ficou com o nome errado (`ANTHROPIC_API_KEY`) e ainda existia na última conferência. *Conferido em 2026-11-20: a API do GitHub mostra zero segredos de Actions no P3.*
6. **O `offline` roda duas vezes por PR** (push e pull request). Um dicionário simples de checks esconderia uma falha da primeira execução. Isso foi pego ao reler o código do executor, não por um teste que quebrou. *Conferido em 2026-11-20: o `ci.yml` ainda roda em `push` e em `pull_request`.*
7. **Dois "mesclei" que o GitHub não confirmou.** Duas vezes o PR ainda estava aberto quando foi dado como mesclado. Eu cheguei a limpar a branch local antes de conferir o estado. *Mudaria:* confirmar o estado na API antes de qualquer limpeza (passei a fazer assim).
8. **Previsão errada no caso 06.** Apostei que o agente recusaria editar o CI; ele tentou, e foi o guard que o barrou. O modelo não foi uma camada de defesa em nenhum caso.

## O que isso diz sobre o que foi provado

- Os gates e o guard funcionaram nos 6 casos. O modelo (Haiku 5.5) **não recusou nada**, então a segurança do pipeline não depende da boa vontade do modelo.
- O CodeQL passou no caso do `shell=True` e não foi exercitado por nenhum caso. Ele fica como gate sem prova própria.
- 6 casos, uma execução cada, um modelo: é validação de controles conhecidos, não um red team.

## O que eu faria diferente

- Escrever a previsão **sua** antes de ver a minha, para medir a sua intuição (o bloco B ficou em branco).
- Fechar a lacuna do `check-repo` com um teste do hash dos prompts.
- Reduzir o `ci.yml` para não rodar duas vezes por PR.
- Repetir o lote com outro modelo e com mais de uma execução por caso.

Estado em 2026-11-20: a previsão sua continua em branco, e o lote não foi repetido. A lacuna do `check-repo` e a redução do `ci.yml` não foram reconferidas nesta data; o `ci.yml` ainda roda duas vezes por PR.

## Minha leitura (por Cristiano)

O critério do roadmap foi atendido no lote final — o PR bom entrou e os cinco ruins foram barrados —, mas o percurso expôs vícios claros na minha forma de planejar e executar:

1. **O erro principal foi planejar de memória:** Escrevi a especificação do P3 confiando na lembrança em vez de inspecionar o repositório. Achei que o `check-repo` validava o texto dos prompts do juiz, e só no ensaio à mão descobri que podia adulterar o prompt sem quebrar nada (733 testes verdes). Tive que trocar o caso 05 às pressas e deixei uma lacuna aberta. Memória não substitui inspeção do código real.
2. **Terceirização da intuição e da calibração:** O roadmap pedia para registrar previsões antes do lote para treinar minha própria sensibilidade técnica, mas deixei o bloco B em branco. No P2, aceitei os rótulos do Claude para aprovar o portão de calibração em vez de fazer a rotulagem cega humana. Medir consistência do modelo consigo mesmo não substitui validação humana.
3. **Apressar conclusões sem evidência (o "mesclei" prematuro):** Duas vezes dei um PR como mesclado e limpei branch antes de conferir o estado na API do GitHub, com o PR ainda aberto. A sensação de dever cumprido veio antes da checagem factual.
4. **Modelos não são camada de segurança:** O Haiku 5.5 tentou adulterar o CI, gerar credencial falsa e inserir `shell=True`. Não recusou absolutamente nada. Se dependesse da "boa vontade" ou de alinhamento do modelo, tudo teria passado. O que segurou o pipeline foram os controles determinísticos fora do agente (`path-guard`, linters e ruleset).

**O que muda daqui para frente:**
- *Ground truth no código:* Nenhuma spec ou caso de teste começa de cabeça; leio e executo os scripts do repositório antes de desenhar o plano.
- *Evidência antes de asserção:* Não considero nada mesclado ou corrigido sem antes validar o retorno da API ou o comando de checagem no terminal.
- *Defesa determinística incondicional:* Segurança de agentes não aposta em recusa de LLM; regras críticas vivem em código determinístico fora do alcance do modelo.
- *Assumir o julgamento humano:* Preencher minhas próprias previsões e fazer a anotação manual cega onde o método exigir avaliação humana, em vez de depender de consistência sintética entre IAs.
