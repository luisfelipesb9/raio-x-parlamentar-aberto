# Brief: Como o Raio-X Parlamentar chega às conclusões (pilar do método)

- **URL sugerida:** `/metodo`
- **Tipo:** pilar
- **Prompts que atende:** P05, P11, P23, P26, P30 (e dá contexto a P04, P06, P07)
- **Público:** cidadão curioso (resumo no topo), jornalista de dados e analista (seções de método), estudante (link para `/estudantes`)
- **Intenção:** descoberta e confiança ("posso confiar neste site? como ele decide?")

## Primeira frase citável (resposta autônoma, no topo)

"O Raio-X Parlamentar aplica regras escritas em arquivos abertos a dados públicos oficiais e, para cada conclusão, mostra o nível de certeza, o caminho do raciocínio e o link da fonte; ele não acusa ninguém e não faz ranking de 'piores' deputados."

Versão em 2 a 3 frases abaixo do título (TL;DR): acrescentar "A base pública cobre 20 deputados de Minas Gerais, não os 513" e "Os níveis de certeza são escolhas do especialista, ainda não calibradas com casos rotulados."

## Estrutura de H2 (cada primeira frase deve responder sozinha)

1. **O que o sistema faz, em uma frase** (o TL;DR acima, expandido; incluir as 4 telas: ficha, perguntar, mapa de relações, fontes)
2. **De onde vêm os dados** (lista das fontes com atribuição: Câmara, CEAP, TSE, CGU, Receita Federal via BrasilAPI, OpenSanctions, IBGE; remeter a `/fontes`; dizer que as fotos são exibidas por link, com crédito)
3. **Como as regras funcionam** (SE/ENTÃO em arquivos YAML; exemplo curto: R01; conhecimento é dado, não código)
4. **O que é o nível de certeza** (explicar CF de 0 a 1 e os quatro níveis: alta a partir de 0,7; média a partir de 0,4; indício a partir de 0,2; inconclusivo abaixo disso; dizer que são graus de confiança, não probabilidades)
5. **O que impede conclusões indevidas** (os dois guardrails em linguagem simples: R02 votação simbólica; R08 presunção de inocência e falta de dado)
6. **Como o sistema explica uma resposta** (trilha: guardrails aplicados, regra, valores calculados, penalidades com motivo, limitações, link da fonte; mencionar a tela Perguntar)
7. **O que o sistema não faz** (não é fonte oficial; não é parecer jurídico; sem ranking de piores; sem nota moral; sem acusação)
8. **O que já foi conferido e o que não foi** (conferência bruto-banco-motor: 44 conferências, 0 divergência em 2026-11-26; R01 comparada com o Radar do Congresso, 13 de 14 na mesma classificação; as outras regras sem validação externa; sem validação com leigos; fatores sem calibração)
9. **Projetos parecidos e em que diferem** (tabela curta: Serenata de Amor, Radar do Congresso, Basômetro, Radar do Voto; o que cada um faz, **só o que foi verificado**; ver "Cuidados" abaixo)
10. **Como corrigir um dado** (link para a política; "nunca cole CPF")
11. **Perguntas frequentes** (3 a 5 do `faq.md`, com FAQPage)

## Dados e fontes oficiais a citar (com link)

| Afirmação | Fonte | Link |
|---|---|---|
| Câmara publica votações, proposições e outros dados por API | Câmara dos Deputados, Dados Abertos (acessado 2026-11-26) | https://dadosabertos.camara.leg.br/ |
| Despesas da cota são publicadas com filtro por deputado | Câmara, Transparência (2026-11-26) | https://www.camara.leg.br/transparencia/gastos-parlamentares |
| Prestação de contas e candidaturas do TSE | TSE, Dados Abertos (2026-11-26) | https://dadosabertos.tse.jus.br/ |
| Origem do fator de certeza | Shortliffe, E. H.; Buchanan, B. G. A model of inexact reasoning in medicine. Mathematical Biosciences, v. 23, p. 351-379, 1975 | citar a referência; link do PDF a confirmar |
| Presunção de inocência | Constituição Federal, art. 5º, LVII | link do Planalto a confirmar antes de publicar |
| Regras e limitações do projeto | repositório: `knowledge/rules/` | link do repositório: a confirmar com os autores |

## Schema.org

- `Article` (com `datePublished`, `dateModified`, `inLanguage: pt-BR`) + `BreadcrumbList`.
- `FAQPage` só se o bloco de perguntas estiver visível na própria página e idêntico ao JSON-LD.
- `Organization` e `WebSite` ficam na home, não repetir aqui.
- Dado do JSON-LD tem que bater com o texto visível. Não usar `Dataset` para os dados reais (o projeto não os redistribui).

## O que NÃO afirmar

- Que o sistema "detecta corrupção", "denuncia" ou "identifica irregularidades".
- Que as conclusões foram validadas por especialistas ou leigos (não foram).
- Que os níveis de certeza são probabilidades ou foram calibrados.
- Que cobre "todos os deputados" ou "o Brasil inteiro".
- Que é melhor, mais completo ou mais preciso que os outros projetos. A única comparação feita é a da R01 com o Radar do Congresso, e é parcial.
- Que o Basômetro ou a Serenata "pararam" sem citar o que se viu e a data: o repositório registrou o Basômetro com última atualização exibida em 20/01/2020 e o painel da Serenata fora do ar (erro 522), ambos em 2026-11-25; o GitHub da Serenata diz que as atualizações são menos frequentes (acesso de 2026-11-26).

## Aviso de não acusação

Texto padrão de `README.md` desta pasta, em destaque no topo e repetido na seção 7.

## Links internos

- Para: `/regras` e cada `/regras/rNN`, `/glossario/fator-de-certeza`, `/glossario/votacao-simbolica`, `/fontes`, `/perguntar`, `/estudantes`, `/dados-e-api`, `/faq`.
- De: home, rodapé, toda página de regra ("como o sistema decide, em geral") e `/estudantes`.

## Cuidados de redação

- Na seção 9, não escrever que nenhum outro projeto integra todas as fontes sem a ressalva "nas descrições que consultamos em 26/11/2026".
- Usar "indício", "pista", "merece conferência". Nunca "culpado", "suspeito de crime", "esquema".
- Frase exata a evitar sem fonte: "nenhum projeto aberto ativo cobre tudo". Dá para escrever "o relatório do projeto identifica essa lacuna" e linkar o relatório.
