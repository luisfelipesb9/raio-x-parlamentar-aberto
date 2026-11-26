# Brief: Perguntas frequentes

- **URL sugerida:** `/faq`
- **Tipo:** FAQ
- **Prompts que atende:** P02, P04, P08, P10, P15, P16, P21 e perguntas de confiança ("posso confiar?", "isto é acusação?")
- **Público:** cidadão e jornalista
- **Intenção:** descoberta e decisão rápida

## Primeira frase citável

"O Raio-X Parlamentar mostra o que os dados públicos indicam sobre deputados federais, com nível de certeza e link da fonte oficial; não é fonte oficial, não é parecer jurídico e não acusa ninguém."

## Estrutura de H2

Um H2 por grupo e, sob cada um, perguntas como H3 com resposta de 1 a 3 frases (a primeira frase é a resposta). O mesmo texto vai no JSON-LD `FAQPage`.

### Sobre o que é e o que não é
1. **O que é o Raio-X Parlamentar?** Resumo do README (uma frase) + escopo (20 deputados de MG).
2. **Isto é uma acusação contra deputados?** Não. Texto do aviso padrão.
3. **Vocês fazem ranking de piores deputados?** Não: "não faz ranking de 'piores deputados', nem dá nota moral" (`docs/politica-de-uso-e-correcao.md`). Explicar que outras fontes publicam rankings de gasto ou de governismo e que o projeto usa regras e não ordens.
4. **Quem faz e por que?** Projeto acadêmico de Sistemas Especialistas (BSI, Unimontes), voluntário, código MIT. Nomes dos autores só com a confirmação deles.
5. **O site é uma fonte oficial?** Não; confirme na fonte indicada em cada achado.

### Sobre os dados
6. **Quais deputados estão no site?** 20 deputados de Minas Gerais; votações de 04/02/2025 a 27/03/2025; despesas de 2024; eleição de 2022. Ampliar para os 513 está no roteiro (`docs/ROADMAP.md`).
7. **De onde vêm os dados?** Lista curta de fontes com link para `/fontes`.
8. **Com que frequência os dados são atualizados?** Responder só com o que for verdade na data de publicação: hoje a coleta é manual (`make sample`); a data de coleta aparece em `/fontes`. Não prometer periodicidade.
9. **Posso usar os dados?** O código é MIT; os dados seguem a licença de cada fonte (`DATA_LICENSES.md`); a fonte OpenSanctions é de uso não comercial. Ver `/dados-e-api`.

### Sobre os resultados
10. **O que significa o nível de certeza?** Explicar o CF e os quatro níveis; dizer que não é probabilidade e que não foi calibrado.
11. **Por que votação simbólica não aparece nas contas de voto?** Explicar R02.
12. **Processo na Justiça entra na conta?** Hoje o sistema não tem fonte de processos; processo sem condenação definitiva não é culpa (R08).
13. **Gasto alto da cota é irregular?** Não necessariamente (R04): pode ter justificativa; a regra só aponta ponto de partida.
14. **A emenda foi para a cidade onde o deputado tem mais votos. Isso é irregular?** Não: correlação não é causa (R07).
15. **Como saber o destino final de uma emenda Pix?** Antes de 2027 o destino final não é rastreável nos dados que o projeto usa; é por isso que a certeza cai (R07). Dizer isso e linkar a fonte oficial confirmada.

### Sobre correção e privacidade
16. **Achei um dado errado. Como corrijo?** Issue com o modelo "Correção de dado", fonte oficial com link, **nunca CPF**.
17. **O site guarda CPF?** A base publicada não tem CPF íntegro; CPFs de terceiros viram código irreversível (ADR-006); uma varredura confere isso antes de publicar (relatório: 0 CPFs íntegros, controle 752).
18. **Por que o nome de um sócio não aparece?** Enquanto a identidade não for confirmada o nome não é divulgado (R06b; LGPD).

## Dados e fontes a citar

Cada resposta aponta para uma das páginas internas (regras, glossário, `/fontes`) e, quando houver, para a fonte oficial confirmada. Links externos permitidos agora: https://dadosabertos.camara.leg.br/ , https://www.camara.leg.br/transparencia/gastos-parlamentares , https://dadosabertos.tse.jus.br/ (todos abertos em 2026-11-26).

## Schema.org

- `FAQPage` com `mainEntity` de `Question` e `Answer`; texto do JSON-LD idêntico ao visível; só as perguntas que de fato estão na página. Observação: o Google restringiu a exibição de resultado enriquecido de FAQ a poucos tipos de site (conhecimento de 2023; **verificar na documentação atual**); o marcador continua útil como estrutura legível para outros leitores automáticos, mas não prometer resultado enriquecido.
- `BreadcrumbList`.

## O que NÃO afirmar

- Periodicidade de atualização que não existe.
- Que o sistema "monitora" deputados em tempo real.
- Que "todos os dados são confiáveis": dizer que o sistema reproduz o dado oficial (conferência bruto-banco-motor) e que isso não prova que o dado oficial está certo (`verificacao.md`).
- Qualquer nome de deputado.

## Aviso de não acusação

No topo da página, texto padrão.

## Links internos

`/metodo`, `/regras`, `/glossario`, `/fontes`, `/dados-e-api`, `/perguntar`.
