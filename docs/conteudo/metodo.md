---
slug: metodo
titulo: "Como o Raio-X Parlamentar chega às conclusões"
descricao: "Regras abertas aplicadas a dados oficiais, com nível de certeza, caminho do raciocínio e link da fonte em cada conclusão. Sem acusação e sem ranking."
resposta: "O Raio-X Parlamentar aplica regras escritas em arquivos abertos a dados públicos oficiais e mostra, em cada conclusão, o nível de certeza, o caminho do raciocínio e o link da fonte. Não acusa ninguém e não faz ranking."
atualizado: 2026-11-26
---

**Isto não é acusação; é o que os dados públicos mostram.** Um achado é uma pista para quem quiser investigar, não uma conclusão sobre a conduta de alguém. Processo sem condenação definitiva não é culpa. Confira sempre na fonte oficial indicada. Para corrigir um dado, veja a [política de uso e correção](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/docs/politica-de-uso-e-correcao.md).

A base pública cobre 20 deputados de Minas Gerais, não os 513. As votações vão de 04/02/2025 a 27/03/2025, as despesas da cota são de 2024 e a eleição é a de 2022. Os níveis de certeza são escolhas do especialista e ainda não foram calibrados com casos rotulados.

## O que o sistema faz?

O sistema reúne dados públicos sobre deputados federais, aplica regras escritas à mão e devolve conclusões em linguagem simples, cada uma com nível de certeza e link da fonte oficial. Ele não decide quem é bom ou mau. Ele mostra padrões nos dados e diz o quanto confia neles.

O site tem quatro telas principais. A **ficha** resume o que se sabe sobre cada deputado. A tela **Perguntar** responde a uma pergunta e mostra o raciocínio passo a passo. O **mapa de relações** liga deputado, empresas, doadores e emendas. A página **Fontes** mostra a origem e a data de coleta de cada dado.

## De onde vêm os dados?

Todos os dados vêm de fontes oficiais abertas, e cada fato guarda a fonte, o identificador oficial e o link. As fontes são:

- **Câmara dos Deputados:** deputados, votações, votos, orientação do governo e proposições, pela [API de Dados Abertos](https://dadosabertos.camara.leg.br/).
- **Cota parlamentar (CEAP):** despesas publicadas pela Câmara em [Transparência](https://www.camara.leg.br/transparencia/gastos-parlamentares).
- **TSE:** candidaturas, prestação de contas e votos por município na eleição de 2022, nos [Dados Abertos do TSE](https://dadosabertos.tse.jus.br/).
- **CGU (Portal da Transparência):** empresas punidas (CEIS e CNEP) e emendas parlamentares.
- **Receita Federal:** sócios das empresas (QSA), consultados pela BrasilAPI apenas para os CNPJs que aparecem nos dados.
- **OpenSanctions:** lista de pessoas politicamente expostas, fonte opcional e de uso não comercial.
- **IBGE:** códigos de município.

As fotos dos deputados são exibidas por link, com o crédito "Câmara dos Deputados". Licenças e créditos estão em [`DATA_LICENSES.md`](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/DATA_LICENSES.md). Veja também [dados e API](/dados-e-api).

## Como as regras funcionam?

Cada regra é um texto SE/ENTÃO guardado em um arquivo YAML, separado do programa. Uma regra diz o que medir, qual limite usar, qual frase mostrar ao leitor, quanta confiança merece e o que ela não consegue afirmar. Para criar uma regra nova não é preciso mudar o motor.

Exemplo, a regra [R01](/regras/R01): SE a taxa de votos iguais à orientação do governo é de pelo menos 0,7 (70%), ENTÃO mostra "Votou junto com o governo em X% das N votações nominais em que o governo orientou". Ela só conta deputados com ao menos 10 votações nominais com orientação.

São nove regras e uma variante: R01 a R09 e R06b. Duas delas são guardrails (R02 e R08), que impedem conclusões indevidas. Veja a lista em [regras](/regras).

## O que é o nível de certeza?

O nível de certeza é um número de 0 a 1, o fator de certeza (CF), que diz o quanto o sistema confia em uma conclusão. Ele não é uma probabilidade. É um grau de confiança escolhido pelo especialista, no estilo do sistema MYCIN (Shortliffe e Buchanan, 1975).

O número vira um de quatro níveis:

- **alta:** a partir de 0,7;
- **média:** a partir de 0,4;
- **indício:** a partir de 0,2;
- **inconclusivo:** abaixo de 0,2.

A conta é simples: a confiança da regra, multiplicada pela confiança nos dados e pelas penalidades por dado incerto. Na R01, por exemplo, a confiança da regra é 0,95. Com menos de 30 votações, ela é multiplicada por 0,7, e o resultado é 0,665, nível média. Veja o termo [fator de certeza](/glossario#fator-de-certeza).

## O que impede conclusões indevidas?

Dois guardrails, que são regras que rodam antes de todas as outras e retiram dados que levariam a erro. A **R02** retira as votações simbólicas das contas de voto, porque nelas ninguém registra como cada deputado votou. A **R08** retira processos sem condenação definitiva e não inventa valor quando falta dado.

Na amostra, a R02 retirou 121 votações simbólicas. A R08 retirou 0 processos, porque ainda não existe fonte de processos no sistema. Falta de dado aparece como "sem dado", nunca como zero.

## Como o sistema explica uma resposta?

Cada conclusão vem com uma trilha que mostra o caminho até ela. A trilha lista os guardrails aplicados, a regra e os valores calculados, as penalidades com o motivo de cada uma, as limitações e as evidências com link para o documento oficial.

Na tela **Perguntar** você escolhe um deputado e um objetivo, e o sistema monta a prova passo a passo. Se não houver conclusão, ele diz por quê, por exemplo "poucos votos válidos" ou "abaixo do limite".

## O que o sistema não faz?

O Raio-X Parlamentar não é fonte oficial, não é parecer jurídico e não substitui a Justiça nem os órgãos de controle. Ele não faz ranking de "piores" deputados, não dá nota moral e não acusa ninguém.

Ausência de achado também não é atestado: o sistema só olha para o que as fontes publicam e para o que as regras sabem medir. Confirme sempre na fonte indicada em cada achado.

## O que já foi conferido e o que não foi?

Os números do sistema foram conferidos contra os arquivos brutos, mas as regras ainda não foram validadas por especialistas nem por leigos. A conferência de 26/11/2026 fez 44 verificações (votações, governismo da R01 e despesas da cota) e não achou nenhuma divergência. Isso prova que o sistema reproduz o dado oficial. Não prova que o dado oficial esteja certo.

Só a R01 foi comparada com uma ferramenta externa, o Radar do Congresso, em consulta de 25/11/2026. Houve a mesma classificação em 13 de 14 deputados, com diferença média de 12,6 pontos percentuais. A diferença pode vir do período curto e de critérios diferentes, mas isso é hipótese e não foi verificado. As outras regras não têm validação externa. Os fatores de certeza e os limites não foram calibrados.

## Que outros projetos existem e no que este difere?

Existem outros projetos abertos sobre o Congresso, e o Raio-X Parlamentar usa as metodologias deles como ponto de partida. O que ele tenta somar é o cruzamento de várias fontes com explicação e incerteza visíveis. Nas descrições que consultamos em 26/11/2026, o relatório do projeto identifica essa lacuna, e essa avaliação pode estar incompleta.

- **Operação Serenata de Amor:** analisa gastos da cota com modelos estatísticos. Inspirou a regra [R04](/regras/R04).
- **Basômetro (Estadão):** calcula taxa de governismo. É a base metodológica da [R01](/regras/R01). O repositório registrou a última atualização exibida em 20/01/2020, em consulta de 25/11/2026.
- **Radar do Congresso:** publica índice de alinhamento. Foi a referência da comparação externa da R01.
- **Radar do Voto:** relaciona votos e destino de emendas. Inspirou a [R07](/regras/R07).

O [relatório do projeto](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/docs/relatorio/relatorio.md) traz a lista completa.

## Como corrigir um dado?

Abra uma issue com o modelo "Correção de dado", diga qual informação está errada e indique o link da fonte oficial que mostra o correto. **Nunca cole CPF**, nem o seu, nem o de terceiros. O projeto verifica na fonte, corrige em prazo razoável (é voluntário e não tem prazo contratual) e registra a correção. Quando o erro é de identidade, como um homônimo, o dado é removido. Leia a [política de uso e correção](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/docs/politica-de-uso-e-correcao.md).

## Onde ver mais?

Veja as [perguntas frequentes](/faq), a página de [regras](/regras), a página [para estudantes](/para-estudantes) e a documentação de [dados e API](/dados-e-api).
