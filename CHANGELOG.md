# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Correções de dado
(veja a [política](docs/politica-de-uso-e-correcao.md)) também são registradas aqui.

## [Não lançado]
### Adicionado
- Banco público enxuto ([ADR-011](docs/adr/ADR-011-publicacao-enxuta-e-leitura-sob-demanda.md)): `make publicar` materializa grafo,
  inferência e contagens do banco completo e grava só os fatos que a API lê, sem chave primária, para caber na Vercel Hobby com 513 deputados.
### Alterado
- A API, quando o banco foi gerado por `make publicar`, deixa de carregar todos os fatos na partida: lê o grafo materializado e consulta
  o DuckDB por deputado. Com o banco de trabalho completo (`make dev`) continua no caminho antigo. As respostas não mudam.

## [0.3.0] - 2026-11-26
### Adicionado
- Fichas e lista de deputados renderizadas no servidor (ISR): o HTML já traz nome, resumo, alertas com nível de certeza
  e aviso de não acusação; ids inexistentes ou malformados respondem 404.
- Descoberta por buscadores e por assistentes de IA: `robots.txt`, `sitemap.xml`, `llms.txt`, `manifest`, endereço canônico
  por página, imagem de compartilhamento por deputado e dados estruturados (JSON-LD).
- Páginas de conteúdo geradas dos textos do repositório e dos YAML das regras: método, regras R01 a R09 e R06b, perguntas
  frequentes, dados e API, para estudantes e um verbete por termo do glossário ([ADR-010](docs/adr/ADR-010-web-le-conteudo-no-build.md)).
- CI com teste de fumaça de SEO sem JavaScript, Dependabot agrupado, `scripts/gh_publicar.sh` e verificação mais rígida do
  sal no `make deploy-check`.
- Estudo de público e plano de medição em `docs/seo/`, termos e atribuição dos dados em `DATA_LICENSES.md` e
  `docs/licencas/`, e pesquisa de viabilidade para cobrir os 513 deputados em `docs/ampliacao/`.

## [0.2.0] - 2026-11-26
### Adicionado
- Mapa de relações legível: ligações nos dois sentidos, agrupamento de folhas, corte justo por relação e valor
  com resumo do que ficou de fora, e verbetes leigos no glossário.
- Diagnóstico do passo "inconclusivo" no encadeamento regressivo (`dados_insuficientes`, `abaixo_do_limiar`,
  `sem_regra_aplicavel`), exibido em Perguntar com os números.
- Cobertura e verificação: endpoints `/cobertura` e `/deputados/{id}/metricas`, manifesto do bruto com sha256,
  `coletado_em` nas evidências e `make verifica`, que recalcula governismo e CEAP direto dos brutos.
- Página **Fontes e método** e painel "Dados e verificação" na ficha, com "Verificar na fonte" em cada achado.
- Interface de juiz consultivo opcional, com implementação nula (ADR-008).
- Documentação de comunidade: licença MIT, guia de contribuição, código de conduta, política de segurança e política de uso e correção.
- Demonstração offline com dados 100% fictícios: `make seed-demo` (gera o banco), `make demo` (gera e explica como subir) e
  `make dev-demo` (sobe a API sobre o banco da demo, com sal e banco já definidos). Ver [docs/demo.md](docs/demo.md).
- Guarda de dados pessoais: `scripts/checa_pii` (`make checa-pii`) e gitleaks no CI.
- Fixtures sintéticas nos testes (sem CPF ou CNPJ de pessoa real) e [DATA_LICENSES](DATA_LICENSES.md) com os termos de
  cada fonte de dados.

### Alterado
- Tema claro como padrão; o escuro só por escolha no botão.
- Contrato `contracts/` na versão 0.2.0 ([ADR-007](docs/adr/ADR-007-contrato-v0-2-0.md)).
- A API lê o manifesto do bruto ([ADR-009](docs/adr/ADR-009-api-le-manifesto-do-bruto.md)).
- Pseudonimização da base pública aceita ([ADR-006](docs/adr/ADR-006-pseudonimizacao.md)).
- **Quebra de deploy:** a API não sobe sem `RAIO_X_ID_SALT` (e `build_graph`/`project` levantam `SalAusenteError`; sal
  vazio explícito também é erro). Antes, o sal dos ids de pessoa do grafo tinha um valor padrão. Quem já publica a API deve
  definir `RAIO_X_ID_SALT` (string longa e secreta, fora do repositório; na Vercel, em Settings > Environment Variables) e
  usar o mesmo valor da base pseudonimizada. Os ids `pessoa:...` do grafo mudam em relação à 0.1.x.
- Versão do projeto, da API e do site alinhada em 0.2.0.

### Segurança
- O reconhecimento de CPF em texto livre (pseudonimização da ingestão, varredura e `checa_pii`) passou a cobrir hífen,
  barra, espaço, espaço sem quebra e ponto seguido de espaço entre os grupos, e o CPF numérico que perdeu o zero à
  esquerda em campos `cpf*`; o dígito verificador continua validado, sem aumentar falsos positivos.
- Sem sal padrão para os ids de pessoa do grafo: sem `RAIO_X_ID_SALT` a API não inicia.

## [0.1.0] - 2026-11-22
### Adicionado
- Fundação: contratos, motor de inferência (fatores de certeza, encadeamento progressivo e regressivo),
  regras R01 a R09 e R06b em YAML, guardrails de votação simbólica e presunção de inocência.
- Fontes: Câmara, CEAP, CGU, TSE, OpenSanctions e RFB; pipeline de ingestão com resolução de entidades.
- Banco DuckDB, API somente leitura, projeção em grafo e site (ficha, grafo, perguntar, comparar, glossário).
- Pseudonimização HMAC e varredura de CPF para a base pública.
