# HANDOFF — estado real do projeto

Última revisão: 2026-11-22. Divisão original: Luis (metade 1, fundação e raciocínio) → Pedro Rodrigues (metade 2, produto).

## Como rodar
```
make setup && make test          # 504 testes Python (pytest); web: 50 unit + 45 e2e
make sample                      # ingere 20 deputados de MG (2024) + roda o motor -> data/sample/raio_x_sample.duckdb
RAIO_X_DB=data/sample/raio_x_sample.duckdb make dev    # API em http://localhost:8000 (/docs)
cd web && pnpm install && pnpm dev                     # web em http://localhost:3000
```

## Status por componente
| Componente | Status |
|---|---|
| contracts/ (Fact, Finding, Explanation, Graph) v0.2.0 | pronto |
| sources/: camara, ceap, cgu, tse, opensanctions, rfb | prontos, com testes de fixture |
| ingest/pipeline + ingest/resolve (candidatura, emenda, pep, cnpj) | pronto; links com CF e tabela de ambiguidades |
| repo/ DuckDB (`Store`, `read_only`, migrations 001/002) | pronto |
| engine: CF MYCIN, loader YAML, forward, backward com `requer` e detecção de ciclo, explain | pronto |
| Regras R01–R09 e R06b | prontas (R09 só no regressivo) |
| graph/ (projeção, subgrafo, backlinks, afinidade de votos) | pronto |
| api/ (8 endpoints GET, RFC 7807, cache por impressão digital do banco) | pronto |
| DB de amostra (`data/sample/raio_x_sample.duckdb`) | pronto, gerado por `make sample` |
| web/ (ficha, grafo Cytoscape, perguntar/comparar, glossário) | **pronto**: 7 rotas (busca, ficha, grafo, perguntar, comparar, glossário); lint/test/build e e2e Playwright, 45 ok, em desktop e 375px; identidade visual "raio-x" em `web/DESIGN.md` |
| Relatório e roteiro de apresentação | `docs/relatorio/` (este commit) |

## O que falta
1. **web/**: concluído (ver tabela). Resta apenas validação com leigos.
2. **R05**: agora tem dados (`make sample` usa `--incluir-proposicoes`): 10 findings.
3. **CPF do deputado**: resolvido. `CamaraSource.fetch(detalhar_deputados=...)` (flag `--detalhar-deputados`, já em `make sample`) busca `GET /deputados/{id}`; na amostra 20/20 candidaturas ligam por CPF (cf 1,0) e 20/20 PEP por CPF (0,95).
4. **Calibração**: CFs das regras e limiares (z=3,5; razão 3; etc.) são escolhas do especialista, **não** calibradas
   com dados rotulados (ver relatório, seção de limitações).
5. Validação com leigos (plano, passo 9): não feita. Comparação externa: parcial, só a R01
   (`docs/relatorio/comparacao-externa.md`).
6. Fato `processo` (guardrail R08) ainda sem fonte: o guardrail existe, mas nenhum plugin produz `processo`.
7. Divisão R05–R09 e R06b com o Pedro: suposição, a confirmar com o Pedro.

## Resultados na amostra (40 findings)
R01: 14 · R03: 2 · R04: 5 · R05: 10 · R07: 9 (CF médio 0,384 = 0,6 × 0,8 do link por nome × 0,8 Pix) · R02 removeu 121 votações simbólicas e R08 0 processos (guardrails, sem finding). Objetivo da R05: `pontuacao_producao_legislativa`. R06 e R06b: 0 com `--limite-rfb 50` (com 300 surge 1 R06b: o zero era cobertura, não ausência). **R06 confirmado não dispara com dados da RFB**: o QSA vem sempre mascarado (617 sócios mascarados, 96 sem CPF, 0 íntegros), então só a R06b é alcançável.
Escopo da amostra: 2.083 emendas ligadas (o total global da CGU é 37.297 ligadas de 77.113), 1.008 doações, 17.060 votos_municipio.

## Operação e privacidade
- A base de amostra **não é versionada**: contém CPF de terceiros (minimização, LGPD). Gere com `make sample`.
- **Pare a API antes de `make ingest` / `make infer`**: o DuckDB trava o arquivo para escrita enquanto a API o mantém aberto.

## Privacidade e deploy
- `--pseudonimizar` troca CPF por HMAC-SHA256 (`hmac:<32 hex>`, sal em `RAIO_X_ID_SALT`); `doador_cpf_visivel` preserva a R06b; CPF de fornecedor PF dentro de `despesa_ceap.fornecedor` (36 casos) também é substituído. Ver ADR-006.
- `make sample-publico` gera `data/sample/raio_x_publico.duckdb` e roda a varredura (`ingest.varredura`): 0 CPFs íntegros (controle positivo: 752). A varredura **não** cobre `data/raw`.
- API: `/saude`, forward pré-calculado no `/perguntar`; `vercel.json` + `api/index.py` (publicado pelo Pedro).

## Deploy (publicado em 2026-11-25, Vercel Hobby)
- Site: https://raio-x-web-delta.vercel.app (atenção: `raio-x-web.vercel.app` é de terceiros)
- API: https://raio-x-api.vercel.app/saude

**O git não leva a base** (`data/` é ignorado): deploy automático pelo GitHub sobe a API sem banco. Publique pela
CLI, **de dentro da pasta que está sendo publicada** (rodando de outra pasta, a CLI lê o `vercel.json` errado).

**Nunca remova `"framework"` dos `vercel.json`.** Sem ele, um projeto novo cai no preset "Other", que serve os
arquivos da árvore como estáticos (código-fonte baixável) e não monta as rotas da API.

1. `RAIO_X_ID_SALT=<segredo> make sample-publico` (a varredura precisa sair 0). Guarde o sal fora do repositório
   e use sempre o mesmo, senão os ids pseudonimizados mudam a cada atualização.
2. Em um clone limpo, copie só `data/sample/raio_x_publico.duckdb` e rode `make deploy-check` (reprova se houver
   outro `.duckdb` na árvore).
3. API (raiz): `vercel link`; envs `RAIO_X_DB=data/sample/raio_x_publico.duckdb`, `RAIO_X_ID_SALT`,
   `RAIO_X_CORS_ORIGINS=<url do web>`. `vercel deploy --dry --json` deve listar a base e nenhum outro arquivo de
   `data/`. No primeiro deploy do projeto, `vercel deploy --prod` (só pode ser de produção). **Nas atualizações**,
   `vercel deploy` (preview, abre logado na Vercel), conferir `/saude` e só então `vercel deploy --prod`.
4. Web (`cd web`): `vercel link`; envs `NEXT_PUBLIC_API_URL=<url da API>` e `NEXT_PUBLIC_SITE_URL=<url do site>`;
   `vercel deploy --prod`. Se a URL do site só for conhecida agora, grave-a em `RAIO_X_CORS_ORIGINS` e republique a API.
5. Conferir: `/saude` (`status: ok`, `pseudonimizado: true`); `<url da API>/pyproject.toml` deve dar 404.

Validado em produção (2026-11-25): `/saude` ok (20 deputados, 40 findings), DuckDB read-only na função Python,
CORS do site, ficha com "Como sabemos disso?", grafo e "perguntar" no navegador, também em emulação de celular
(375 px, sem rolagem horizontal). **Falta** o teste em um celular de verdade. Os CPFs são pseudonimizados, mas os nomes continuam na base (ADR-006). Mapa de
relações: o painel mostra as ligações nos dois sentidos e os municípios usam o nome da votação do TSE (2 de 185
seguem como código). Falta: cadastro da Receita no painel (só 36 das 1.598 empresas o têm) e link para a fonte oficial.

## Windows
- `make test` passa sem ajustes de encoding ou fuso (`tzdata` entrou como dependência só no Windows).
- Sem `make` instalado, rode os comandos do `Makefile` direto com `uv run ...`.
- Clone em um caminho curto (caminho longo falha com "Filename too long").

E2E no Windows (2026-11-24), no Edge instalado (`channel: "msedge"`), com a amostra completa: 50 casos aprovados e
2 pulados de propósito (desktop e 375px). Não foi uma única rodada limpa: em paralelo houve timeouts (máquina
sobrecarregada ou suspensa); com `--workers=1` restaram 3 falhas do mesmo tipo, resolvidas com `--last-failed`
(2 passaram, 1 é pulo intencional).

## Fonte RFB indisponível
Se a BrasilAPI responder 5xx ou timeout para um CNPJ mesmo após as tentativas, ele vai para a chave `indisponiveis`
(com aviso no log e no relatório do pipeline, em `rfb.indisponiveis`) e o lote segue; a empresa fica sem dados da
Receita. Com 3 CNPJs seguidos sem resposta a ingestão aborta (queda do serviço ou da rede). 429 persistente e 4xx
continuam abortando.

## Regra de ouro
Não alterar `contracts/` sem ADR (ver `docs/adr/`). Regras novas: YAML + predicado em `engine/predicates/`.
