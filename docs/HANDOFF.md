# HANDOFF — estado real do projeto

Última revisão: 2026-11-22. Divisão original: Luis (metade 1, fundação e raciocínio) → Pedro Rodrigues (metade 2, produto).

## Como rodar
```
make setup && make test          # 472 testes Python (pytest); web: 50 unit + 45 e2e
make sample                      # ingere 20 deputados de MG (2024) + roda o motor -> data/sample/raio_x_sample.duckdb
RAIO_X_DB=data/sample/raio_x_sample.duckdb make dev    # API em http://localhost:8000 (/docs)
cd web && pnpm install && pnpm dev                     # web em http://localhost:3000
```

## Status por componente
| Componente | Status |
|---|---|
| contracts/ (Fact, Finding, Explanation, Graph) v0.1.0 | pronto |
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
5. Validação com leigos e comparação com Basômetro/Radar do Voto/Serenata (plano, passo 9): não feita.
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
- API: `/saude`, forward pré-calculado no `/perguntar`; `vercel.json` + `api/index.py` (deploy pelo Pedro).

## Regra de ouro
Não alterar `contracts/` sem ADR (ver `docs/adr/`). Regras novas: YAML + predicado em `engine/predicates/`.
