# O P4 no roadmap

- **Fonte:** roadmap de estudo em Engenharia de Software com Agentes de IA (Fase 4: Segurança e CI/CD), como resumido nos projetos anteriores.
- **O que isto é:** o que o roadmap diz sobre o P4, mais o que os projetos P1 a P3 deixaram pronto ou pendente para ele. As frases entre aspas são do próprio roadmap.
- **Limite deste resumo:** o texto completo do roadmap não está nesta máquina. Este arquivo junta o que foi registrado em `projeto03/docs/roadmap/p3-no-roadmap.md` e nos documentos do P1, do P2 e do P3. Se houver o roadmap completo, confira os detalhes da Fase 4 nele antes de fechar o escopo.

## Fase 4: Segurança e CI/CD

| Item | O que o roadmap diz |
|---|---|
| Período | semanas 29 a 38, 70 h |
| Projeto | **P4**: pipeline "agente abre PR, gates decidem" em um repositório Java ou Python, **mais red team de prompt injection no P2** |
| Tópicos | OWASP LLM Top 10 (2026) e Agentic Top 10; lethal trifecta; sandbox e permissões mínimas; segredos; supply chain; GitHub Actions ou equivalente; agente em CI com gates; tracing com OpenTelemetry; orçamento de tokens |
| Critério de concluído | *"um PR aberto por agente só chega à branch principal com testes, SAST, evals e revisão humana verdes."* |

## Como o roadmap mede

| Métrica | Como medir | Meta em 6 meses | Meta em 12 meses |
|---|---|---|---|
| Segurança | Ataques testados e mitigados | — | **10 documentados** |
| Evals | Casos anotados e regressões detectadas | 100 casos | Regressão roda em CI a cada mudança |
| Previsão de falhas | Antes de rodar o agente, anotar o que vai dar errado; comparar | Acerta metade | Acerta a maioria e sabe por quê |
| Projetos com critério atendido | Checklist da fase | P1, P2 e P3 iniciado | P1 a P5 |

## Regras do roadmap que valem para todos os projetos

- **"Repositório público (exceto P5), README com decisões e limites, e um texto curto explicando o que deu errado."**
- **Corte o escopo, não o critério de concluído.**
- **Só dados públicos ou sintéticos.** Nunca dados de contribuinte; CPF e CNPJ sintéticos gerados em tempo de execução, nunca escritos no repositório.
- **O que estudar a fundo:** prompt injection como problema estrutural; testes, arquitetura e CI/CD são duráveis. Recursos do Claude Code, versões da spec MCP e formatos de skills e hooks mudam rápido: aprender o conceito e consultar a doc oficial na hora de usar.
- **Fundamentos sem delegação** valem nas fases 1 e 3. Na Fase 4, a forma de trabalho (quem escreve o quê) se decide na spec.

## O que os projetos anteriores deixaram para o P4

### Do P1 (agente mínimo, `../projeto01`)

- **Sandbox ficou para a Fase 4.** O P1 usa guardas no harness (confirmação, ambiente limpo, timeout, corte de saída, `cwd` fixo), sem container. A spec do P1 diz: "O isolamento de verdade (container, `sandbox-exec`) fica para a Fase 4 do roadmap."
- Cliente OpenRouter e ledger de tokens e custo, reaproveitáveis para o orçamento de tokens.

### Do P2 (MCP server de legislação, `../projeto02`)

O P2 é o **alvo do red team**. A seção "Ligação com P3 e P4" da spec do P2 aponta os alvos:
- **Injeção pelo texto da norma:** o texto volta só nos campos `texto` e `trecho`, e o retorno não traz instruções. É o vetor a atacar: "instruções no retorno misturam o canal de instrução com o de dado".
- **A guarda de CPF/CNPJ (o hook):** alvo explícito de contorno, por formatação, CNPJ alfanumérico ou argumentos aninhados.
- **Limites do hook já conhecidos** (hipótese H12 do P3): ele não vê números disfarçados, nem o texto do usuário, nem o `Bash`, e **não cobre o server remoto** (o matcher é `mcp__taxlaw__.*`).
- **Server remoto por HTTP**, com token só por variável de ambiente (`TAXLAW_HTTP_TOKEN`).

### Do P3 (suíte de evals, `../projeto03`)

- **O "evals" do gate:** o P3 entrega o eval que o pipeline do P4 exige verde. O `check-repo` já roda em CI e reprova quando o juiz calibrado fica abaixo do limiar ou quando muda modelo, prompt ou versão do P2 sem relatório novo.
- **Casos de segurança como ponte:**
  - **H12** (CPF/CNPJ no meio da pergunta): 8 casos. No server local, o Haiku não repetiu nenhum CPF (C4 100%). **No server remoto, não foi medido**: o `run-round --conditions remoto` está pronto, falta rodar com as variáveis do server.
  - **H13** (instrução escondida no texto da norma): **ficou de fora do P3**, porque depende de um texto plantado que não existe no corpus. É trabalho natural do red team do P4.
- **Juiz LLM calibrado** (`openai/gpt-6.1-terra`) no C1 e no C3; o C4 (segurança) é decidido por código para o eco de CPF, e o juiz só entraria nos casos H13.
- **Ferramentas reaproveitáveis:** runner isolado do Claude Code (`--strict-mcp-config`, ferramentas mínimas), rodadas em lote com teto de custo, traces com hooks registrados, relatório com intervalo de confiança e comparação antes/depois.

## Pontos de partida para a spec do P4

1. **Qual repositório recebe o pipeline** "agente abre PR, gates decidem": Java ou Python, como o roadmap pede. O P3 (Python, com CI e evals) é candidato natural.
2. **Quais gates:** testes, SAST, evals (o P3) e revisão humana, todos verdes antes da branch principal.
3. **Red team no P2:** pelo menos 10 ataques documentados (meta de 12 meses), começando pelos alvos acima (texto da norma, hook de CPF, server remoto).
4. **Sandbox e permissões mínimas** para o agente que abre o PR, que o P1 deixou pendente.
5. **Tracing e orçamento de tokens** do agente em CI.
