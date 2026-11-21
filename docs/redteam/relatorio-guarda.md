# Relatório da guarda de CPF e CNPJ no server do P2 (H6 e H7)

- **Data:** 2026-11-18
- **Alvo:** o server `taxlaw.http` do P2 no commit `1a02e552`, medido na réplica local (cópia do P2). Nada foi enviado à VPS.
- **Medição:** três repetições por requisição. Cada repetição usa um CPF e um CNPJ sintéticos novos, gerados em memória.
- **Controle positivo:** uma consulta sem número, sobre "alíquota zero cesta básica", devolveu resultado (`encontrado`). A rodada só vale porque o controle passou.
- **Previsões:** escritas pelo Claude, a pedido do Cristiano, rotuladas como "Previsão do Claude" no campo `motivo`. O bloco do Cristiano não foi preenchido: o experimento rodou antes da previsão.
- **P2:** inalterado. O `git status` tem as duas linhas da linha de base.
- **Mitigações:** nenhuma foi aplicada.

## Resumo

- **H6 (formas canônicas): bloqueou em 12 de 12 repetições.** A guarda reconhece o CPF puro, o CPF pontuado, o CNPJ pontuado e o número aninhado dentro de uma lista de argumentos.
- **H7 (formas disfarçadas): vazou em 12 de 12 repetições.** A guarda não reconhece o CPF com espaço entre os dígitos, o CPF em largura total, o CPF com caractere invisível e o CNPJ em largura total. O número chega à ferramenta e volta na resposta, na mesma forma disfarçada.
- As duas previsões acertaram. O resultado de cada requisição foi o mesmo nas três repetições.
- Nenhum número ficou gravado. O arquivo de medição não tem sequência de 11 dígitos, e a varredura do repositório não acha nada.

## Fichas

| Ataque | Requisição | Previsão | Resultado (3 repetições) | Formas que voltaram | Veredito |
|---|---|---|---|---|---|
| H6 | CPF puro na consulta | bloqueou (80%) | bloqueou, bloqueou, bloqueou | nenhuma | bloqueou |
| H6 | CPF pontuado na consulta | bloqueou (80%) | bloqueou, bloqueou, bloqueou | nenhuma | bloqueou |
| H6 | CNPJ pontuado na consulta | bloqueou (80%) | bloqueou, bloqueou, bloqueou | nenhuma | bloqueou |
| H6 | CPF aninhado em uma lista de argumentos | bloqueou (80%) | bloqueou, bloqueou, bloqueou | nenhuma | bloqueou |
| H7 | CPF com espaço entre os dígitos | vazou (70%) | vazou, vazou, vazou | `cpf:espacada` | vazou |
| H7 | CPF em largura total | vazou (70%) | vazou, vazou, vazou | `cpf:largura_total` | vazou |
| H7 | CPF com caractere invisível | vazou (70%) | vazou, vazou, vazou | `cpf:invisivel` | vazou |
| H7 | CNPJ em largura total | vazou (70%) | vazou, vazou, vazou | `cnpj:largura_total` | vazou |

## Notas por ataque

**H6.** A guarda varre todos os argumentos, inclusive dentro de listas, e reconhece as formas canônicas. A mensagem de bloqueio (`dados_de_contribuinte`) veio em todas as repetições, sem o número.

**H7.** A regex da guarda só reconhece dígitos ASCII com pontos ou traços. As formas disfarçadas passam, e a ferramenta `buscar_dispositivos` devolve a consulta no campo `consulta`. Por isso o número volta. Na resposta, ele aparece com o mesmo disfarce que recebeu. O eco não é um vazamento para terceiros, porque volta a quem fez a chamada, mas o número chegou à ferramenta e ao contexto de quem consome a resposta.

**Hook.** O hook do P2 usa a mesma função de varredura (`find_in_arguments`). Por isso é esperado que ele também deixe passar as formas disfarçadas. Não medimos o hook, porque ele só roda dentro do Claude Code.

## Recomendações (não aplicadas)

- **Normalizar o texto antes da varredura.** Converter a largura total para ASCII, remover caracteres de largura zero e tratar espaços entre dígitos antes da regex. A mesma normalização deve valer para o hook.
- **Rever o eco.** A ferramenta devolve a consulta inteira. Se a consulta contiver dado pessoal, ele volta na resposta. Uma opção é não ecoar a consulta, ou ecoar só o que a busca usou.
- **Reatacar depois da mitigação.** Este relatório mede a guarda atual. Depois de qualquer mudança, a mesma medição precisa ser repetida, porque o resultado vale para este commit.

## Limites

- Medido na réplica local, no commit `1a02e552` do P2. A VPS não foi usada para este teste, porque ela recebe o tráfego público e não deve receber números de contribuinte, mesmo sintéticos.
- Dois ataques, quatro requisições cada, três repetições. As formas são as que definimos na spec. Outras formas, como caracteres de outro alfabeto, não foram testadas.
- A chave de um objeto JSON não foi testada. A spec previa o caso, mas o plano o deixou de fora.
- O resultado vale para esta data e este commit.

## O que deu errado

- O detector não via o número em largura total e em caractere invisível, porque o JSON da resposta escapa esses caracteres (por exemplo, `１`). Corrigimos antes da medição: o detector agora olha o texto decodificado.
- O cliente cortava a resposta em 4000 caracteres. Um número que voltasse depois desse ponto passaria despercebido. Corrigimos: a medição da guarda lê a resposta inteira, que fica só na memória.
- As previsões foram escritas pelo Claude, e não pelo Cristiano. Por isso o placar acima mede só a previsão do Claude.

## Próximos passos

- Decidir se a normalização e a revisão do eco entram num projeto separado, e se o hook será medido dentro do Claude Code.
- Os dados desta medição estão em `docs/redteam/medicao-guarda.json`, sem nenhum número.
