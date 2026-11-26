# Backlog de prompts do público

Fase 1 do método de descoberta por IA e buscadores. Estado em 2026-11-26.

## Como esta lista foi feita (e o que ela NÃO é)

- **Os 30 prompts são hipóteses sintéticas**, escritas a partir do que o projeto cobre (README, regras R01 a R09, glossário) e de como as perguntas aparecem em páginas oficiais e em reportagens (ver `fontes-ia.md`). **Não vêm de logs de busca, de Search Console, de suporte ou de comunidades.** Não há volume de busca medido para nenhum deles.
- Para trocar hipótese por dado real, faltam: (1) Search Console do site em produção, quando houver tráfego; (2) as perguntas que professores, colegas e jornalistas já fizeram ao projeto (issues, e-mails, a apresentação); (3) o baseline manual (`como-medir.md`), que mostra se a resposta de cada motor cita alguém.
- O teste "a resposta do motor cita alguma marca ou fonte?" **não foi feito** para nenhum prompt: ninguém rodou os prompts nos motores ainda. Rodar é o primeiro passo do baseline (`como-medir.md`).
- **Prioridade** segue quatro filtros: o projeto tem a ver com a pergunta; tem autoridade real (método próprio, regra documentada, dado verificado); agrega algo que a fonte oficial não tem (explicação, nível de certeza, ressalva); e o risco ético é controlável. Alta = passa nos quatro e há página planejada.
- **Limite de cobertura que toda resposta deve declarar:** a base pública cobre 20 deputados de Minas Gerais, votações de 04/02 a 27/03/2025, despesas CEAP de 2024 e eleição de 2022 (README e relatório). Nenhuma página pode responder "o seu deputado" para os 513.

## Páginas do site citadas na coluna "Página"

Existentes hoje (pastas em `web/src/app`): `/` , `/deputado/[id]`, `/perguntar`, `/comparar`, `/grafo`, `/fontes`, `/glossario`.
Planejadas (nomes sugeridos; ver `briefs/`): `/metodo`, `/regras` e `/regras/[id]`, `/glossario/[termo]`, `/faq`, `/estudantes`, `/dados-e-api`.

## Legenda de risco ético

- **Baixo:** pergunta conceitual; a resposta não toca em pessoa.
- **Médio:** a resposta fala de comportamento de grupo ou de método que poderia virar comparação entre pessoas.
- **Alto:** o prompt convida a acusar, a ranquear "piores" ou a ligar uma pessoa a irregularidade. A página deve **recusar o ranking e o veredito**, explicar o que o dado mostra e não mostra, e apontar a fonte oficial.

## Cluster A. Gastos e cota parlamentar (CEAP)

| ID | Prompt | Intenção | Página | Prioridade | Risco ético e tratamento |
|---|---|---|---|---|---|
| P01 | o que é a cota parlamentar dos deputados e com o que ele pode gastar? | descoberta | `/glossario/ceap` | Média (a Câmara já responde bem; o projeto entra com definição curta e link) | Baixo |
| P02 | como consultar quanto meu deputado gastou da cota parlamentar? | decisão | `/regras/r04` (seção "onde ver o dado oficial") e `/faq` | Alta | Baixo. Apontar a página oficial da Câmara; dizer que a cobertura do projeto é de 20 deputados de MG |
| P03 | quais deputados gastam mais com a cota parlamentar? | comparação | `/regras/r04` | Média | **Alto.** Não publicar ranking. Explicar que o limite mensal varia por estado (Ato da Mesa 43/2009), que gasto alto não é ilegal por si só e que a R04 usa desvio estatístico por categoria, não ordem de gasto. Apontar a tabela oficial da Câmara |
| P04 | gasto alto da cota parlamentar é irregular? | decisão | `/regras/r04` | Alta | Médio. Resposta direta: não necessariamente; a regra só aponta ponto de partida para fiscalizar |
| P05 | como saber se um gasto da cota parlamentar é suspeito? | decisão | `/regras/r04` e `/metodo` | Alta | Médio. Descrever o método (z-score robusto, mínimo de 5 deputados por categoria) sem apontar pessoa |

## Cluster B. Governismo e votações

| ID | Prompt | Intenção | Página | Prioridade | Risco ético e tratamento |
|---|---|---|---|---|---|
| P06 | o que é taxa de governismo e como é calculada? | descoberta | `/regras/r01` e `/glossario/governismo` | Alta (a regra é nossa, com limiar, mínimo de votações e limitações escritos) | Baixo |
| P07 | como saber se meu deputado vota com o governo? | decisão | `/regras/r01` e `/deputado/[id]` | Alta | Médio. Mostrar votos nominais com orientação, período e n de votações; dizer que o período é curto |
| P08 | qual a diferença entre votação simbólica e votação nominal na Câmara? | descoberta | `/glossario/votacao-simbolica` e `/regras/r02` | Alta | Baixo |
| P09 | como descobrir como um deputado votou em uma proposta? | decisão | `/regras/r02` e `/dados-e-api` | Média | Baixo. Se a votação foi simbólica, não existe voto individual (R02) |
| P10 | qual deputado é o mais governista e qual o mais oposicionista? | comparação | `/regras/r01` | Média | **Médio a alto.** Sem lista ordenada. Explicar o que a taxa mede, que o presidente da Casa não vota e que a taxa depende do período. Apontar o Radar do Congresso como fonte externa que publica a lista |
| P11 | Basômetro ou Radar do Congresso: qual usar para ver governismo? | comparação | `/metodo` (seção "projetos parecidos") e `/regras/r01` | Média | Baixo. Usar só o que está em `docs/relatorio/comparacao-externa.md` (13 de 14 na mesma classificação, diferença média de 12,6 pontos, amostra de 14 deputados de MG) |

## Cluster C. Emendas e municípios

| ID | Prompt | Intenção | Página | Prioridade | Risco ético e tratamento |
|---|---|---|---|---|---|
| P12 | o que é emenda Pix (transferência especial) e por que é polêmica? | descoberta | `/glossario/emenda-pix` e `/regras/r07` | Alta | Baixo. Citar a rastreabilidade anterior a 2027 como parâmetro da R07 e os levantamentos da Transparência Brasil como fonte externa |
| P13 | para onde meu deputado mandou as emendas? | decisão | `/regras/r07` e `/deputado/[id]` | Alta | Médio. Só emenda com deputado identificado e valor empenhado maior que zero; ligação por nome tem CF 0,8 |
| P14 | deputado manda emenda para as cidades onde tem mais votos? | descoberta | `/regras/r07` | Alta (é exatamente o que a R07 mede) | Médio. Correlação não é causa; dizer sempre |
| P15 | como saber o destino final do dinheiro de uma emenda Pix? | decisão | `/regras/r07` e `/faq` | Média | Baixo |
| P16 | quais deputados mandaram mais emendas? | comparação | `/regras/r07` | Baixa | **Alto.** Sem ranking. Apontar a consulta oficial e dizer que a R07 não mede volume, mede concentração eleitoral |

## Cluster D. Sanções e fornecedores

| ID | Prompt | Intenção | Página | Prioridade | Risco ético e tratamento |
|---|---|---|---|---|---|
| P17 | o que são CEIS e CNEP? | descoberta | `/glossario/ceis-cnep` | Média | Baixo. Lembrar que CEIS e CNEP não são listas equivalentes de empresas proibidas de licitar |
| P18 | como saber se uma empresa está proibida de contratar com o governo? | decisão | `/glossario/ceis-cnep` e `/regras/r03` | Média (o portal oficial domina; o projeto entra com o cruzamento por CNPJ e data) | Baixo |
| P19 | deputado pagou empresa punida com dinheiro da cota parlamentar? | decisão | `/regras/r03` | Alta | **Alto.** Descrever o método e os limites ("não prova que o deputado sabia da sanção"). Não nomear pessoa em exemplo; usar a base fictícia da demonstração ou números agregados |
| P20 | empresa de doador de campanha recebe dinheiro da cota do deputado? | descoberta | `/regras/r06` | Média | **Alto.** Falar de "pista", nunca de "esquema". Dizer que o QSA vem mascarado, que por isso o caso real alcançável é a R06b (indício, CF até 0,4), e que o nome do sócio não é exibido (LGPD) |
| P21 | como saber se um deputado é réu ou foi condenado? | decisão | `/regras/r08` | Baixa | **Alto.** Resposta honesta: o projeto ainda não tem fonte de processos; processo sem condenação definitiva não é culpa (R08). Apontar fontes oficiais do Judiciário |

## Cluster E. Sistema especialista explicável

| ID | Prompt | Intenção | Página | Prioridade | Risco ético e tratamento |
|---|---|---|---|---|---|
| P22 | o que é um sistema especialista e um exemplo na prática? | descoberta | `/estudantes` | Média (concorre com apostilas e enciclopédia) | Baixo |
| P23 | como funciona o fator de certeza do MYCIN, com exemplo? | decisão | `/estudantes` e `/metodo` | Alta (exemplo trabalhado: R01, 0,95 x 0,7 = 0,665) | Baixo |
| P24 | qual a diferença entre encadeamento progressivo e regressivo, com exemplo? | decisão | `/estudantes` | Alta | Baixo |
| P25 | exemplo de sistema especialista de código aberto com regras em arquivo YAML | decisão | `/estudantes` e `/dados-e-api` | Média | Baixo |
| P26 | como um sistema especialista explica como chegou a uma conclusão? | descoberta | `/metodo` e `/perguntar` | Média | Baixo |

## Cluster F. Dados abertos para desenvolvedores e ferramentas parecidas

| ID | Prompt | Intenção | Página | Prioridade | Risco ético e tratamento |
|---|---|---|---|---|---|
| P27 | como baixar as despesas da cota parlamentar e as votações pela API da Câmara? | decisão | `/dados-e-api` | Média (a Câmara é a fonte; o projeto entra com cuidados de uso: limite de requisições, chave de despesa) | Baixo |
| P28 | como cruzar despesas da cota parlamentar com empresas sancionadas pelo CNPJ? | decisão | `/dados-e-api` e `/regras/r03` | Média | Médio. Mostrar o método; não publicar lista de nomes |
| P29 | como cruzar doações de campanha do TSE com fornecedores de deputados? | decisão | `/dados-e-api` e `/regras/r06` | Baixa a média | Alto (LGPD). Explicar pseudonimização (ADR-006) e que a licença do dado do TSE não dispensa obrigações de dados pessoais |
| P30 | quais projetos abertos fiscalizam a cota e o mandato dos deputados? | comparação | `/metodo` (seção "projetos parecidos") | Média | Baixo. Só afirmar o que foi verificado; ver `fontes-ia.md` |

## Prompts que o site deve se recusar a atender como pedidos (modelo de resposta)

Pedidos como "quem é o pior deputado", "lista de deputados corruptos", "ranking dos que mais roubam" não têm página. A resposta curta que o site e os documentos devem dar é: "O Raio-X Parlamentar não faz ranking de piores deputados nem dá nota moral. Mostra o que os dados públicos indicam sobre cada deputado, com nível de certeza e link da fonte oficial. Um indício não é acusação." (fonte: `docs/politica-de-uso-e-correcao.md`.) Esse texto vive na página `/faq` e no aviso de cada página de regra.

## Próximo passo para este backlog

1. Rodar o baseline (30 prompts x 5 motores) e registrar as fontes citadas. Sem isso a prioridade acima é palpite informado.
2. Cortar prompts em que nenhum motor cita fonte nenhuma (baixo retorno) e reforçar os em que a lacuna aparece.
3. Reordenar a prioridade com a primeira leitura de Search Console, quando houver tráfego.
