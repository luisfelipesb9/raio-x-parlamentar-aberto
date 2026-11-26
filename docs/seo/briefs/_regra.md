# Modelo de brief: página de regra (R01 a R09)

Uma página por regra: `/regras/r01` a `/regras/r09` (R06 e R06b ficam na mesma página, `/regras/r06`). Preencher com `regras-notas.md` e com o arquivo da regra em `knowledge/rules/`. **Todo campo vem do YAML da regra** (`nome`, `se`, `entao`, `cf`, `penalidades`, `por_que`, `limitacoes`, `fonte_metodologica`); não parafrasear limitação de forma que a enfraqueça.

- **Tipo:** página de regra (referência técnica em linguagem simples)
- **Público:** cidadão (resposta e exemplo), jornalista e analista (limiar, fonte, limitações), estudante (tipo da regra, CF, predicado)
- **Intenção:** descoberta e decisão ("o que esta regra mede? posso usar isto?")

## Primeira frase citável

Formato fixo, uma frase, sem adjetivo:

"A regra [Rnn] ([nome]) [verbo de medida: mede, aponta, retira, reúne] [o que], usando [fonte oficial], e conclui com nível de certeza [valor/nível] quando [condição em palavras]."

Exemplo de forma (não copiar para outra regra): "A regra R01 (taxa de governismo) mede em quantas votações nominais com orientação do governo o deputado votou igual à orientação e conclui 'alinhado' quando a taxa é de pelo menos 70% e há ao menos 10 votações."

## Estrutura de H2 (ordem fixa, igual em todas as regras)

1. **O que esta regra responde** (a pergunta do cidadão, em uma frase; o campo `por_que`)
2. **Como ela decide** (o `se` em palavras; limiares e mínimos como lista; tipo: inferência ou guardrail)
3. **Qual o nível de certeza** (o `cf`, as `penalidades` com o motivo e o fator, o cálculo de um exemplo, os quatro níveis)
4. **De onde vêm os dados** (fonte oficial, com link e data de coleta; o que o projeto cobre: 20 deputados de MG, período)
5. **O que a regra não diz** (as `limitacoes` do YAML, uma por item, mais as notas da regra)
6. **Exemplo com dado fictício** (usar o gerador de demonstração; texto da `entao` preenchido com números fictícios e a marcação visível "exemplo fictício")
7. **De onde veio a ideia** (o `fonte_metodologica`, com link só se verificado)
8. **Como conferir você mesmo** (passo a passo na fonte oficial; link)
9. **Perguntas frequentes** (2 a 4, FAQPage)
10. **Como corrigir um dado** (link da política)

## Dados e fontes oficiais a citar

Os links exatos de cada regra estão em `regras-notas.md`. Em toda página de regra:
- Link para a página da regra no repositório (a confirmar com os autores) e para `/metodo`.
- Data de coleta e escopo (20 deputados de MG), vindos de `/fontes`.

## Schema.org

- `TechArticle` (ou `Article`) com `about` apontando para um `DefinedTerm` do conceito central (por exemplo, "taxa de governismo"), `datePublished`, `dateModified`, `inLanguage: pt-BR`.
- `BreadcrumbList` (Início > Regras > Rnn).
- `FAQPage` quando houver o bloco visível.
- Não usar `Review`, `Rating` nem `ClaimReview`: o projeto não verifica afirmações de terceiros nem avalia pessoas.

## O que NÃO afirmar (valem para qualquer regra)

- Que um achado "prova", "comprova" ou "revela" irregularidade, fraude ou corrupção. O verbo certo é "indica", "aponta", "merece conferência".
- Que o nível de certeza é probabilidade.
- Nome de pessoa com achado como exemplo. Exemplo é sempre fictício ou agregado.
- Que a regra vale para os 513 deputados.
- Qualquer coisa sobre intenção ou conhecimento do deputado ("sabia", "quis", "escondeu").

## Aviso de não acusação

Bloco padrão (`README.md` desta pasta) logo abaixo do TL;DR, e a limitação principal da regra repetida em uma linha ao lado do resultado.

## Links internos

- Para `/metodo`, `/glossario/fator-de-certeza`, os termos da regra (ver `regras-notas.md`), `/fontes`, `/perguntar` e `/regras`.
- Entre regras relacionadas (indicadas em `regras-notas.md`).
- De: `/regras`, `/metodo`, `/faq`, páginas de termo do glossário.

## Checagens antes de enviar para revisão

- Cada número da página vem do YAML ou de `docs/relatorio/`; cada um tem o arquivo citado no rascunho.
- Os valores de limiar e CF batem com `knowledge/rules/` na data da revisão (abrir o arquivo; os YAML podem mudar).
- O exemplo fictício está marcado como fictício.
- Rodar `../checklist-etica.md`.
