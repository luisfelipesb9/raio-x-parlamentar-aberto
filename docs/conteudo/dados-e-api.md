---
slug: dados-e-api
titulo: "Dados e API do Raio-X Parlamentar"
descricao: "O que a API somente leitura entrega, como chamá-la, como rodar o sistema, onde obter os dados oficiais e quais licenças valem."
resposta: "A API do Raio-X Parlamentar é somente leitura: devolve os achados de cada deputado da amostra, com nível de certeza, trilha de explicação e link da fonte oficial. Os dados brutos continuam nas fontes oficiais."
atualizado: 2026-11-26
---

**Os achados da API são pistas rastreáveis, não conclusões sobre a conduta de ninguém.** Veja o [método](/metodo) e a [política de uso e correção](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/docs/politica-de-uso-e-correcao.md).

A base pública cobre 20 deputados de Minas Gerais, votações de 04/02/2025 a 27/03/2025, despesas da cota de 2024 e a eleição de 2022. Não há dados em tempo real nem de todos os deputados.

## O que a API entrega e o que não entrega?

A API entrega achados, perfis, explicações, o grafo de relações e a cobertura da base, só por leitura (GET). Ela não aceita escrita, não chama serviços externos e não redistribui dado bruto nem CPF.

As rotas são:

- `/saude`: estado da API, versão do contrato e contagens;
- `/deputados`: lista paginada, com filtros `q` (trecho do nome), `uf`, `partido`, `page` e `page_size`;
- `/deputados/{id}`: perfil do deputado;
- `/deputados/{id}/findings`: achados do deputado;
- `/deputados/{id}/metricas`: métricas por regra e janela de votos;
- `/cobertura`: fontes, janela de votos e contagens da base;
- `/findings/{id}/explicar`: trilha de explicação de um achado;
- `/grafo` e `/grafo/backlinks/{node_id}`: nós e arestas em torno de um centro;
- `/perguntar`: prova regressiva de um objetivo para um deputado;
- `/comparar`: comparação lado a lado de dois deputados.

A documentação interativa fica em `/docs` da própria API. A API pública do projeto está em `https://raio-x-api.vercel.app`; ela respondeu a `/saude` em 26/11/2026 com 20 deputados e 40 achados. O projeto não definiu limite de uso, garantia de disponibilidade nem prazo de atualização.

## Como chamar a API?

Basta fazer requisições GET, e os exemplos abaixo foram executados contra a base fictícia de demonstração, em `http://localhost:8000`. Todos devolveram resposta 200 com JSON.

```
curl "http://localhost:8000/saude"
curl "http://localhost:8000/deputados?uf=SP&page_size=5"
curl "http://localhost:8000/deputados/9900003/findings"
curl "http://localhost:8000/findings/R04:9900003/explicar"
curl "http://localhost:8000/perguntar?deputado=9900002&objetivo=merece_atencao_fiscalizacao"
curl "http://localhost:8000/comparar?a=9900001&b=9900002"
curl "http://localhost:8000/grafo?centro=deputado:9900001&profundidade=1"
```

Na demonstração, a chamada de `/perguntar` para o objetivo `merece_atencao_fiscalizacao` do deputado fictício 9900002 devolve nível de certeza 0,72 (alta) e uma trilha de passos: a R09 no nível 0 e as regras R03, R04, R06 e R06b no nível 1. Os objetivos válidos são `alinhado_governo`, `risco_integridade`, `concentracao_eleitoral_emendas`, `pontuacao_producao_legislativa` e `merece_atencao_fiscalizacao`.

Erros vêm no formato de problema HTTP (RFC 7807), com código 404 quando o deputado ou o achado não existe e 422 quando um parâmetro é inválido.

## Qual é o formato de um achado?

Um achado (`Finding`) é um objeto JSON com a conclusão em linguagem simples, o nível de certeza e as evidências. Os campos são:

- `id`: identificador, como `R04:9900003` (regra, dois pontos e id do deputado);
- `deputado_id`, `regra` e `categoria` (votacao, gastos, integridade, producao ou emendas);
- `conclusao`: o texto para o leitor;
- `cf`: o fator de certeza e `nivel`: alta, media, indicio ou inconclusivo;
- `evidencias`: lista com tipo, id oficial, URL, descrição, data de coleta e, quando conhecido, o hash do arquivo bruto;
- `guardrails_aplicados` e `valores` (os números calculados).

A explicação (`Explanation`) traz `finding_id`, `como` (passos com regra, condição, resultado e detalhe), `por_que` e `limitacoes`. Os esquemas JSON dos contratos estão em `web/src/types/schemas/` no [repositório](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto). A versão do contrato aparece em `/saude` e no rodapé do site.

## Como ler o nível de certeza?

O nível de certeza é um número de 0 a 1, o fator de certeza (CF), que vira um de quatro níveis: alta a partir de 0,7, média a partir de 0,4, indício a partir de 0,2 e inconclusivo abaixo disso. Ele não é uma probabilidade e não foi calibrado.

O número é a confiança da regra, multiplicada pela confiança nos dados e pelas penalidades. Veja o [método](/metodo) e o termo [fator de certeza](/glossario#fator-de-certeza).

## Como rodar o sistema na sua máquina?

Você precisa de Python 3.11 ou mais novo com o gerenciador uv, e de Node 22 com pnpm. Os comandos, na raiz do repositório, são:

1. `make setup`: instala as dependências Python.
2. `make demo`: gera o banco fictício, sem internet e sem dados reais.
3. `make dev-demo`: sobe a API em `http://localhost:8000`.
4. Em outro terminal: `pnpm install` e `pnpm dev` na pasta `web/`, para o site em `http://localhost:3000`.

Para usar outro banco, defina `RAIO_X_DB` (caminho do banco) e `RAIO_X_ID_SALT` (sal dos identificadores de pessoa no grafo). Sem o sal, a API não sobe. O valor do sal da demonstração é público e só serve para dados fictícios: nunca o use em uma base real. Pare a API antes de rodar `make ingest` ou `make infer`, por causa do bloqueio de escrita do banco.

Com dados reais, `make sample` ingere os 20 deputados de MG e roda o motor. Isso precisa de internet e gera um banco local que não deve ser publicado.

## Como obter os dados oficiais?

Os dados brutos devem ser obtidos nas fontes oficiais. Os caminhos são:

- **Câmara dos Deputados:** a [API de Dados Abertos](https://dadosabertos.camara.leg.br/), com documentação em [Swagger](https://dadosabertos.camara.leg.br/swagger/api.html), cobre deputados, votações e proposições.
- **Cota parlamentar (CEAP):** tabela e arquivos na página de [gastos parlamentares](https://www.camara.leg.br/transparencia/gastos-parlamentares).
- **TSE:** candidaturas, prestação de contas e votos em [dadosabertos.tse.jus.br](https://dadosabertos.tse.jus.br/).
- **CGU:** CEIS, CNEP e emendas parlamentares, no [Portal da Transparência](https://portaldatransparencia.gov.br/).

Para cruzar despesas da cota com empresas sancionadas, use o CNPJ exato e compare a data do gasto com o início e o fim da sanção, como na regra [R03](/regras/R03).

## Que cuidados o projeto aprendeu ao usar essas fontes?

Estes cuidados valem para o uso do projeto e podem mudar com o tempo:

- a API da Câmara já devolveu o erro HTTP 429 e o limite não é documentado, por isso o projeto faz pausas, novas tentativas e usa arquivos em lote;
- o id de despesa da cota se repete, por isso o projeto monta uma chave com o `idDocumento` mais um hash da linha;
- o quadro de sócios da Receita vem com CPF mascarado;
- a BrasilAPI não é adequada para ingestão em massa, e o projeto a usa só para uma amostra pequena de CNPJs.

Para a conferência dos dados, `make verifica` recalcula o governismo e a cota a partir dos brutos e compara com o banco. Em 26/11/2026 foram 44 conferências e nenhuma divergência. Isso prova que o sistema reproduz o dado oficial, não que o dado oficial esteja certo.

## Quais licenças e atribuições valem?

O código é MIT, e os dados seguem a licença ou os termos de cada fonte. O levantamento, com o que está confirmado e o que ainda falta, está em [`DATA_LICENSES.md`](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/DATA_LICENSES.md). O resumo, levantado em 26/11/2026, é:

- **Câmara dos Deputados e CEAP:** sem licença nomeada; os termos do portal pedem a citação da fonte. A licença formal da API está a confirmar.
- **TSE:** Creative Commons Atribuição (CC BY) nos conjuntos de 2022, sem versão declarada. A licença não dispensa as obrigações da LGPD.
- **CGU:** CEIS e CNEP aparecem no catálogo como domínio público (leitura indireta). Emendas e PEP têm licença não especificada. Em todos os casos, cite a fonte.
- **Receita Federal:** conjunto mensal do CNPJ em CC BY (leitura indireta); a BrasilAPI não tem termos de uso dos dados.
- **OpenSanctions:** CC BY-NC 4.0, só para uso não comercial. Quem usar o projeto para fins comerciais deve desativar essa fonte ou obter licença própria.
- **Fotos:** exibidas por link, com o crédito "Foto: Câmara dos Deputados".

Textos de crédito prontos estão em [`docs/licencas/atribuicao.md`](https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/docs/licencas/atribuicao.md). O projeto não distribui dados reais de pessoas: o repositório só tem código, regras e dados fictícios.

## O que vale sobre dados pessoais e LGPD?

Ser público não dispensa finalidade, boa-fé e interesse público (LGPD, art. 7º, § 3º). Por isso o projeto minimiza dados: o CPF de terceiros (doadores, sócios, fornecedores) é trocado por um código irreversível sem a chave (HMAC-SHA256 com sal, ADR-006), e a base publicada não tem CPF íntegro. Uma varredura confere isso antes de publicar: 0 CPFs íntegros, com controle positivo de 752 na base não pseudonimizada.

Pseudonimizar não é anonimizar: quem tiver o sal pode reidentificar. Para corrigir um dado, abra uma issue "Correção de dado" e **nunca cole CPF**. Veja o termo [pseudonimização](/glossario#pseudonimizacao).

## Como contribuir com uma fonte nova?

Abra uma issue com o modelo "Nova fonte" e leia o `CONTRIBUTING.md` e o roteiro do projeto, em `docs/ROADMAP.md`. Cada fonte é um plugin em `sources/NOME/source.py` e todo fato precisa de fonte, id oficial e URL.

Veja também as [regras](/regras), a página [para estudantes](/para-estudantes) e as [perguntas frequentes](/faq).
