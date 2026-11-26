---
slug: para-estudantes
titulo: "Sistema especialista aberto para estudar: o Raio-X Parlamentar"
descricao: "Um sistema especialista pequeno e aberto, com regras em YAML, fatores de certeza no estilo MYCIN, encadeamento progressivo e regressivo e explicação."
resposta: "O Raio-X Parlamentar é um sistema especialista pequeno e aberto: base de fatos, regras em YAML, motor com encadeamento progressivo e regressivo, fatores de certeza no estilo MYCIN e módulo de explicação, aplicados a dados públicos."
atualizado: 2026-11-26
---

**Os exemplos desta página usam dados fictícios. Os dados reais mostram pistas, não acusações; veja o [método](/metodo).** O código é de um trabalho de disciplina de graduação (Sistemas Especialistas, Bacharelado em Sistemas de Informação, Unimontes), não uma referência acadêmica validada. O conteúdo está no [repositório](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto) sob licença MIT.

A base de dados real cobre 20 deputados de Minas Gerais, votações de 04/02/2025 a 27/03/2025, despesas da cota de 2024 e a eleição de 2022. Os fatores de certeza e os limites das regras são escolhas do especialista e não foram calibrados.

## Quais são os blocos de um sistema especialista e onde estão no código?

Um sistema especialista separa o conhecimento do domínio (as regras) do mecanismo que o aplica (o motor) e justifica as respostas. Neste projeto, cada bloco tem um lugar:

- **Base de fatos:** `contracts/models.py` define o `Fact`, com tipo, chave, atributos, fonte, id oficial, URL e data de coleta. O banco é o DuckDB (`repo/store.py`), e `engine/factbase.py` oferece a memória de trabalho, com `of(tipo)` e `exclude(...)`.
- **Base de conhecimento:** os arquivos `knowledge/rules/R*.yaml`, com o formato em `knowledge/rules/_schema.md`.
- **Motor de inferência:** `engine/forward.py` (progressivo) e `engine/backward.py` (regressivo), com `engine/certainty.py` para os fatores de certeza e `engine/safe_expr.py` para avaliar as condições.
- **Módulo de explicação:** `engine/explain.py` e o tipo `Explanation` em `contracts/models.py`.
- **Interface:** `api/main.py` (API somente leitura) e `web/` (site).

Há ainda camadas de aquisição (`sources/`, `ingest/`) e um grafo (`graph/`). A dependência corre em uma direção: `sources`, `ingest`, `repo`, `engine`, `graph`, `api`, `web`, e nenhuma camada importa a que está à sua direita.

## Como é uma regra na base de conhecimento?

Uma regra é um arquivo YAML curto, com a condição, a frase para o leitor e as ressalvas. O conhecimento é dado, não código: acrescentar uma regra não exige mudar o motor. Os campos são:

- `id`, `nome`, `tipo` (inferência ou guardrail) e `categoria`;
- `conclui`: o objetivo que a regra prova, usado no encadeamento regressivo;
- `predicado`: o nome da função que calcula os valores, registrada em `engine/predicates/`;
- `parametros`: limiares e mínimos;
- `se`: a condição sobre os valores calculados, avaliada por um avaliador seguro (só comparações e aritmética, sem `eval`);
- `entao`: a frase em linguagem simples, com variáveis;
- `cf`: a confiança do especialista na regra, de 0 a 1;
- `penalidades`: fatores que reduzem o `cf` quando o dado é incerto, cada um com motivo;
- `por_que`, `limitacoes` e `fonte_metodologica`.

Tome a [R01](/regras/R01). O predicado calcula a taxa de votos iguais à orientação do governo. O `se` compara a taxa com 0,7. O `cf` é 0,95. A penalidade multiplica por 0,7 se há menos de 30 votações. Cada regra declara o que não consegue afirmar.

## Como o fator de certeza é calculado, com a conta feita à mão?

O fator de certeza (CF) do sistema segue o modelo do MYCIN (Shortliffe e Buchanan, 1975), com valores entre −1 e 1; neste projeto as regras usam de 0 a 1. As fórmulas são três.

1. **Combinar duas evidências para a mesma conclusão.** Se os dois CF são positivos: CF = CF1 + CF2 × (1 − CF1). Se os dois são negativos: CF = CF1 + CF2 × (1 + CF1). Se têm sinais opostos: CF = (CF1 + CF2) / (1 − o menor dos módulos).
2. **Conjunção de premissas.** O CF da conclusão é o CF da regra vezes o menor CF das premissas, sem ficar abaixo de zero.
3. **Penalidades.** O CF é multiplicado por cada fator de penalidade.

No sistema, a conta fica: CF final = cf da regra × menor premissa × produto das penalidades. Depois o número vira um nível: alta a partir de 0,7, média a partir de 0,4, indício a partir de 0,2 e inconclusivo abaixo disso.

Exemplo 1, R01: 0,95 × 0,7 = 0,665, que dá o nível média. Exemplo 2, [R06b](/regras/R06b): 0,85 × 0,4 = 0,34, que dá o nível indício. Exemplo 3, combinação: dois sinais de 0,34 e 0,4 para o mesmo objetivo dão 0,34 + 0,4 × (1 − 0,34) = 0,604. Veja o termo [fator de certeza](/glossario#fator-de-certeza).

Os CF são graus ordinais de confiança, não probabilidades.

## Como funciona o encadeamento progressivo?

O encadeamento progressivo vai dos fatos às conclusões, e o motor o executa em dois passos. Ele está em `engine/forward.py`:

1. **Guardrails primeiro.** As regras de prioridade abaixo de 10 rodam e podam a base de fatos.
2. **Regras de inferência.** Para cada regra não composta, o motor chama o predicado, avalia o `se`, calcula o CF e emite um `Finding` com uma `Explanation`.

O comando `make infer` faz isso para todos os deputados e grava os achados. As regras compostas são ignoradas nesse modo.

## Como funciona o encadeamento regressivo?

O encadeamento regressivo parte de um objetivo e busca os fatos que o provam, e o motor o faz com a função `prove(objetivo, deputado)` em `engine/backward.py`. Os passos são:

1. Calcula as regras alcançáveis a partir do objetivo, seguindo os `requer`.
2. Roda o encadeamento progressivo só nelas, depois dos guardrails.
3. Resolve cada sub-objetivo de forma recursiva. Regra de folha usa o CF do achado. Regra composta usa seu `cf` vezes o menor CF dos sub-objetivos.
4. Quando várias regras concluem o mesmo objetivo, combina os CF pela fórmula do MYCIN.
5. Detecta ciclos pela pilha de objetivos: um ramo cíclico vale CF 0 e fica registrado na trilha.

Exemplo: a [R09](/regras/R09) tem `requer: [risco_integridade]`, e esse objetivo é provado por R03, R04, R06 e R06b. A tela [Perguntar](/perguntar) usa esse caminho. A decisão está no ADR-004. Veja [encadeamento progressivo](/glossario#encadeamento-progressivo) e [regressivo](/glossario#encadeamento-regressivo).

## O que são guardrails?

Guardrails são regras que impedem conclusões indevidas e, por isso, rodam antes das outras. A [R02](/regras/R02) retira as votações simbólicas, porque nelas não há voto individual. A [R08](/regras/R08) retira processos sem trânsito em julgado e registra deputados sem dado, sem inventar valor.

Eles têm prioridade menor que 10 e não geram conclusão própria. A [R08](/regras/R08) mostra um limite honesto: nenhum plugin produz ainda o fato "processo", então ela removeu 0 na amostra. Veja o termo [guardrail](/glossario#guardrail).

## Como o sistema explica uma conclusão?

A explicação responde ao "como" e ao "por quê" de cada achado. O módulo `engine/explain.py` monta, para cada `Finding`, uma `Explanation` com os passos "como" (guardrails aplicados, regra e valores calculados, penalidades com motivo e fator), o "por quê" (o `por_que` da regra) e as limitações. As evidências apontam para o documento oficial.

No encadeamento regressivo, a trilha é uma lista de `PassoProva`, com profundidade, objetivo, regra, CF e uma nota. Em alguns casos, como na R01, quando a regra não conclui o sistema diz o motivo, por exemplo "dados insuficientes" ou "abaixo do limite". Você pode ver isso na tela [Perguntar](/perguntar).

## De onde vieram as regras?

As regras vêm de análise documental, não de entrevista com especialistas. Os "especialistas" são metodologias publicadas, como Basômetro, Operação Serenata de Amor, Radar da República, Radar do Voto e Elas no Congresso, e a legislação (Constituição Federal, art. 5º, LVII).

De cada fonte foram extraídas a pergunta, a fórmula e a ressalva, e tudo ficou registrado no YAML (`fonte_metodologica` e `limitacoes`). A validação com especialistas humanos é trabalho futuro.

## Isso é inteligência artificial?

O motor é um sistema especialista clássico: não aprende com dados, aplica regras escritas por pessoas. Não há aprendizado de máquina no cálculo dos achados. Cada resultado é determinístico e pode ser refeito à mão, como nos exemplos acima.

O projeto tem uma extensão **proposta**, ainda não construída, no ADR-008 (status "Proposto"): um "juiz consultivo" que escolheria entre opções fechadas, como mapear uma pergunta em texto livre a um dos objetivos de `/perguntar`. Hoje existe só a interface e o `NullJudge`, determinístico e sem rede, que não está ligado ao `/perguntar`. Mesmo na proposta, o julgamento nunca altera CF, regras nem guardrails.

## O que este sistema não é?

O sistema é um trabalho de graduação, com limites claros. Os principais:

- os CF e os limiares não foram calibrados com casos rotulados;
- os achados não foram validados com leigos;
- a comparação externa cobre só a R01, com o Radar do Congresso: 13 de 14 deputados na mesma classificação, em consulta de 25/11/2026;
- a amostra tem 20 deputados de um estado e um período curto;
- a R06 confirmada não dispara com os dados reais da Receita, porque o quadro de sócios vem mascarado;
- as conclusões do sistema não são afirmações sobre irregularidade.

Ele também não deve ser comparado em qualidade a sistemas históricos como o MYCIN. Usa as ideias dele, em escala pequena.

## Que exercícios posso fazer?

Estes exercícios usam só o que está no repositório:

1. **Duas penalidades.** A [R07](/regras/R07) tem cf 0,6, penalidade ×0,8 por emenda Pix e ×0,7 por menos de 3 municípios. Calcule o CF e o nível. Resposta: 0,6 × 0,8 × 0,7 = 0,336, nível indício. Com a ligação por nome (0,8) como premissa, qual o valor?
2. **Regra nova.** Escreva, no formato de `knowledge/rules/_schema.md`, uma regra com um predicado existente e um limiar seu. Teste os casos positivo, negativo e de guardrail, como pede o `AGENTS.md`.
3. **Ciclo.** Imagine as regras A (`requer: [b]`, `conclui: a`) e B (`requer: [a]`, `conclui: b`). Mostre por que `prove` devolve CF 0 e o que fica na trilha.
4. **Limiar.** Discuta por que o corte de 0,7 da [R01](/regras/R01) é uma escolha do especialista. O que muda com 0,6 ou 0,8?
5. **Contribuição.** Abra uma issue com o modelo "Nova regra" propondo uma regra e sua fonte metodológica.

## Quais são as referências?

- SHORTLIFFE, E. H.; BUCHANAN, B. G. A model of inexact reasoning in medicine. *Mathematical Biosciences*, v. 23, p. 351-379, 1975.
- BUCHANAN, B. G.; SHORTLIFFE, E. H. *Rule-Based Expert Systems: the MYCIN experiments of the Stanford Heuristic Programming Project*. Addison-Wesley, 1984.
- GIARRATANO, J.; RILEY, G. *Expert Systems: Principles and Programming*. 4. ed. Course Technology, 2004.
- BRASIL. Constituição da República Federativa do Brasil de 1988, art. 5º, LVII.
- BRASIL. Lei nº 13.709/2018 (LGPD).

O [relatório do projeto](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/docs/relatorio/relatorio.md) traz a lista completa e a fundamentação. Veja também o [método](/metodo) e as [regras](/regras).
