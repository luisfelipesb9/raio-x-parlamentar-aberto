---
slug: faq
titulo: "Perguntas frequentes sobre o Raio-X Parlamentar"
descricao: "Respostas curtas sobre o que o Raio-X Parlamentar é, de onde vêm os dados, o que o nível de certeza significa e como corrigir um dado."
resposta: "O Raio-X Parlamentar mostra o que os dados públicos indicam sobre deputados federais, com nível de certeza e link da fonte oficial. Não é fonte oficial, não é parecer jurídico e não acusa ninguém."
atualizado: 2026-11-26
---

**Isto não é acusação; é o que os dados públicos mostram.** Um achado é uma pista para quem quiser investigar, não uma conclusão sobre a conduta de alguém. Processo sem condenação definitiva não é culpa. Confira sempre na fonte oficial indicada. Para corrigir um dado, veja a [política de uso e correção](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/docs/politica-de-uso-e-correcao.md).

A base pública cobre 20 deputados de Minas Gerais, votações de 04/02/2025 a 27/03/2025, despesas da cota de 2024 e a eleição de 2022.

## O que é o Raio-X Parlamentar?

O Raio-X Parlamentar é um sistema aberto que reúne dados públicos sobre deputados federais (votos, projetos, gastos da cota, emendas, doações, empresas e sanções) e os explica em linguagem simples. Cada conclusão mostra como foi obtida e o quanto é certa.

Hoje ele cobre 20 deputados de Minas Gerais, não os 513. Veja o [método](/metodo).

## Isto é uma acusação contra deputados?

Não: o site mostra o que os dados públicos indicam, e um achado é uma pista para quem quiser investigar, não uma conclusão sobre a conduta de alguém. Processo sem condenação definitiva não é culpa, e o sistema se recusa a tratá-lo como tal (regra [R08](/regras/R08)).

O site também não é fonte oficial nem parecer jurídico, e não substitui a Justiça nem os órgãos de controle. Confira sempre na fonte oficial indicada em cada achado.

## O Raio-X Parlamentar faz ranking de piores deputados?

Não: o sistema não faz ranking de "piores" deputados, nem dá nota moral. Ele aplica regras com limites escritos e mostra, para cada deputado, o que os dados indicam e com que nível de certeza.

Outras fontes publicam listas ordenadas de gasto ou de governismo. Uma lista ordenada mistura casos diferentes (estado distante, mandato mais longo, período curto) e passa a impressão de ordem de culpa. Por isso este site não a produz.

## Quem faz o projeto e por quê?

É um projeto acadêmico de Sistemas Especialistas do curso de Sistemas de Informação da Unimontes, voluntário e com código aberto sob licença MIT. O objetivo é mostrar, com um sistema pequeno e explicável, como cruzar dados públicos com nível de certeza declarado.

O código está no [repositório do projeto](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto).

## Quais deputados e períodos estão no site?

O site cobre 20 deputados de Minas Gerais, votações de 04/02/2025 a 27/03/2025, despesas da cota de 2024 e a eleição de 2022. Ampliar para os 513 deputados está no roteiro do projeto, sem data definida.

Se o seu deputado não está na lista, o site não tem informação sobre ele. Isso não quer dizer que não haja nada a saber.

## De onde vêm os dados?

Os dados vêm de fontes oficiais abertas: [Câmara dos Deputados](https://dadosabertos.camara.leg.br/) (votos, proposições e cota parlamentar), [TSE](https://dadosabertos.tse.jus.br/) (candidaturas e doações), Controladoria-Geral da União (empresas punidas e emendas), Receita Federal (sócios de empresas), IBGE (códigos de município) e, de forma opcional, OpenSanctions (pessoas politicamente expostas).

Cada achado traz o link do documento oficial. A página Fontes mostra a data da coleta de cada dado.

## Com que frequência os dados são atualizados?

Não há atualização automática: hoje a coleta é feita por quem mantém o projeto, com um comando manual, e a data da coleta aparece na página Fontes. O site não monitora deputados em tempo real.

Por isso, o dado mostrado pode estar atrás do que a fonte oficial publica hoje. Na dúvida, confira na fonte.

## Posso usar os dados e o código?

O código é livre sob licença MIT. Os dados seguem a licença ou os termos de cada fonte, e isso exige citar a fonte. A lista de OpenSanctions é de uso não comercial.

O levantamento de licenças, com o que está confirmado e o que ainda não, está em [`DATA_LICENSES.md`](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/DATA_LICENSES.md). Veja também [dados e API](/dados-e-api).

## O que significa o nível de certeza?

O nível de certeza diz o quanto o sistema confia em uma conclusão, em quatro níveis: alta (a partir de 0,7), média (a partir de 0,4), indício (a partir de 0,2) e inconclusivo (abaixo de 0,2). O número, de 0 a 1, não é uma probabilidade.

Os valores são escolhas do especialista e ainda não foram calibrados com casos rotulados. Pense neles como graus de confiança em ordem, não como chance de acerto. Veja [fator de certeza](/glossario#fator-de-certeza).

## Por que votação simbólica não aparece nas contas de voto?

Porque na votação simbólica os votos individuais não são registrados, então não existe voto de cada deputado para contar. A Câmara adota esse processo na maioria das propostas, segundo o seu [guia para jornalistas](https://www2.camara.leg.br/comunicacao/assessoria-de-imprensa/guia-para-jornalistas/votacao).

O sistema retira essas votações antes de qualquer cálculo (regra [R02](/regras/R02)). Na amostra, foram 121 votações simbólicas retiradas.

## Processo na Justiça entra na conta?

Não: o sistema ainda não tem fonte de processos judiciais, e processo sem condenação definitiva não é culpa. A regra [R08](/regras/R08) retira esse tipo de dado antes de qualquer cálculo.

Isso quer dizer que ausência de processo no site não significa ausência de processo. Para saber se alguém é réu ou foi condenado, a consulta é nos tribunais.

## Gasto alto da cota é irregular?

Não necessariamente: gasto alto pode ter justificativa, como estado distante ou mandato mais longo no período. A regra [R04](/regras/R04) só aponta gastos muito acima do padrão dos colegas da amostra, como ponto de partida para fiscalizar.

O padrão de comparação é o de 20 deputados de Minas Gerais, e não o do país. A fonte oficial das despesas é a [página de gastos da Câmara](https://www.camara.leg.br/transparencia/gastos-parlamentares).

## A emenda foi para a cidade onde o deputado tem mais votos. Isso é irregular?

Não: correlação não é causa. A regra [R07](/regras/R07) só mede se as emendas foram para cidades onde o deputado teve pelo menos 3 vezes a fatia de votos que teve nas demais do estado. Ela não diz o motivo da escolha.

O deputado pode ter mais votos onde atua há mais tempo, e por isso mandar mais emendas ali. Nas emendas Pix anteriores a 2027, o destino final não é rastreável nos dados usados, e a certeza cai.

## Achei um dado errado. Como corrijo?

Abra uma issue com o modelo "Correção de dado" no repositório, diga qual informação está errada e indique o link da fonte oficial que mostra o correto. Nunca cole CPF, nem o seu, nem o de terceiros.

O projeto verifica na fonte, corrige em prazo razoável (é voluntário e não tem prazo contratual) e registra a correção. Se o erro for de identidade, como um homônimo, o dado é removido. A base publicada não tem CPF íntegro: CPFs de terceiros viram um código irreversível. Leia a [política de uso e correção](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/docs/politica-de-uso-e-correcao.md).
