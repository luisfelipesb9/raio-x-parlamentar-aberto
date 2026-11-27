# Mapa do repositório — Raio-X Parlamentar

Guia para quem trabalha neste repositório. Leia inteiro antes de mudar código.

## O que é
Sistema Especialista que documenta tudo que é público sobre deputados federais e correlaciona as
informações num grafo navegável. Trabalho final de Sistemas Especialistas (BSI/Unimontes).

## Regra de ouro: dependência em uma direção só
```
sources → ingest → repo(fatos) → engine → graph → publicar → api → web
                 ↑ contracts/ é usado por todos, não importa ninguém
```
- Uma camada **nunca** importa a camada à sua direita.
- Tudo que atravessa camadas é um tipo de `contracts/`. Mudou contrato → ADR em `docs/adr/` + bump `CONTRACT_VERSION`.
- `api/` e `web/` só **leem** o banco. Nunca chamam API externa. Única exceção: a API lê, opcionalmente, o
  `data/raw/manifest.json` para completar `sha256_bruto` (`docs/adr/ADR-009-api-le-manifesto-do-bruto.md`).
  O `web/` também lê `knowledge/rules/` e `docs/conteudo/`, só no build, via gerador (`docs/adr/ADR-010-web-le-conteudo-no-build.md`).

## Mapa de pastas e donos
| Pasta | Responsabilidade |
|---|---|
| `contracts/` | Tipos Pydantic: Fact, Entity, Finding, Explanation, Graph |
| `sources/` | Um plugin por órgão (Câmara, CEAP, TSE, CGU, RFB, OpenSanctions) |
| `ingest/` | Pipeline raw→staging→facts, resolução de entidades CPF/CNPJ |
| `repo/` | Acesso ao banco (DuckDB; Postgres depois) e migrations |
| `engine/` | Motor de inferência: forward/backward chaining, fatores de certeza, guardrails, explicação |
| `knowledge/rules/` | Base de conhecimento em YAML: R01–R09 e R06b (R09 é composta, só regressiva) |
| `graph/` | Projeção pura de fatos/findings em nós e arestas (`graph/README.md`) |
| `publicar/` | Banco público enxuto: grafo, inferência e contagens materializados + só os fatos que a API lê (ADR-011) |
| `api/` | FastAPI read-only (endpoints GET em `api/main.py`, ver `api/README.md`) |
| `web/` | Next.js: ficha leiga, grafo, explicação, comparação (pronto: rotas em `web/src/app`, e2e Playwright em `web/`) |
| `docs/` | ADRs, arquitetura, glossário, handoff, relatório |

Status atual de cada item: `docs/HANDOFF.md`.

## Comandos (interface única: Makefile)
```
make setup    # instala dependências Python (uv)
make ingest   # coleta fontes → data/raw → banco (data/raio_x.duckdb)
make infer    # roda o motor e materializa findings
make sample   # ingere a amostra (20 deputados de MG; votações de fev–mar/2025, CEAP do arquivo de 2024, eleição TSE de 2022) em data/sample/raio_x_sample.duckdb e roda o motor
make sample-publico  # amostra pseudonimizada (HMAC) + varredura de CPF em $TMPDIR/raio_x_publico_origem.duckdb (fora da árvore), depois `make publicar`
make publicar # origem pseudonimizada -> data/sample/raio_x_publico.duckdb (enxuto, sem chave primária; ADR-011)
make ingest-nacional   # Onda 4: deputados em exercício (sem --amostra, sem teto de votações/proposições) na origem pseudonimizada ($ORIGEM); coleta longa
make publicar-nacional # depois do anterior: motor, varredura de CPF e o arquivo enxuto em $DESTINO_NACIONAL (data/nacional/, não versionado; origem em $ORIGEM_NACIONAL)
make test     # pytest
make verifica # recalcula governismo e CEAP dos brutos e confronta com o banco/motor (docs/relatorio/verificacao.md)
make lint     # ruff
make dev      # sobe só a API (uvicorn api.main:app --reload); o web roda à parte: `pnpm dev` em web/
```
`make sample` usa `--reusar-raw` (reaproveita `data/raw/`) e `RAIO_X_DB` para apontar o motor ao banco de amostra.
`make ingest-nacional` roda `python -m ingest.pipeline --nacional` (exige `RAIO_X_ID_SALT`); variáveis `ANOS_CEAP`, `JANELA_INICIO`,
`JANELA_FIM`, `FONTE_VOTOS`, `LIMITE_RFB` e `ARGS` (ex.: `ARGS="--reusar-raw --reusar-dumps"`). Flags da Câmara no pipeline:
`--legislatura-completa`, `--fonte-votos {api,dump}`, `--reusar-dumps`, `--retomar/--sem-retomar`. Com `--reusar-raw`, o bruto da Câmara
só é reaproveitado se o escopo gravado nele (`_escopo`: legislatura, janela, fonte de votos, teto de votações) servir ao pedido.
Detalhes: `docs/ampliacao/ingest-nacional.md`.
Banco: `--db` > `$RAIO_X_DB` > `data/raio_x.duckdb`.

## Como adicionar uma FONTE de dados
1. Crie `sources/<nome>/source.py` com uma classe que herda `sources.base.Source`.
2. Implemente `fetch()` (salva bruto em `data/raw/<nome>/`) e `normalize(raw) -> list[Fact]`.
3. Todo `Fact` precisa de `fonte`, `id_oficial`, `url` (rastreabilidade obrigatória).
4. Registre em `sources/__init__.py::REGISTRY`. Escreva teste com fixture JSON em `tests/unit/fixtures/`.

## Como adicionar uma REGRA (base de conhecimento)
1. Crie `knowledge/rules/RNN_nome.yaml` seguindo `knowledge/rules/_schema.md`.
2. Condições usam predicados registrados no **pacote** `engine/predicates/` (um módulo por regra ou grupo:
   `core` R01–R04, `producao` R05, `circuito` R06/R06b, `emendas` R07, `presuncao` R08). Para um predicado novo,
   crie `engine/predicates/<regra>.py` com `@predicate("nome")` (ou `@guardrail`) e importe-o em
   `engine/predicates/__init__.py`.
   Regra **composta** (ex.: R09): sem `predicado`, com `requer: [objetivo]`; só roda no encadeamento regressivo.
3. Defina `cf` (0–1) e, se houver incerteza de dado, `penalidades`.
4. Teste em `tests/unit/test_rules.py` (ou `test_rules_r05_r08.py`): caso positivo, negativo e guardrail.
O motor **não** precisa ser alterado para regra nova.

## Operação
- O banco de amostra não é versionado (contém CPF de terceiros; minimização LGPD): gere com `make sample`.
- Pare a API antes de `make ingest`/`make infer` (lock de escrita do DuckDB).
- A regra de direção descreve fluxo de dados; exceções em `docs/adr/ADR-005-excecao-direcao-dependencia.md`.

- Envs: `RAIO_X_DB` (caminho do banco), `RAIO_X_ID_SALT` (sal do HMAC da pseudonimização; ADR-006).

## Camada de dados e leitura
- `repo.store.Store(path=None, read_only=False)`: com `read_only=True` não roda migrations nem cria arquivo
  (erro claro se o banco não existir). A API **sempre** usa `read_only=True`.
- `graph/` é projeção pura (sem banco/rede); `api/` o chama sobre fatos lidos do `Store`.
- Resolução de entidades: `ingest/resolve/` (candidatura, emenda, pep, cnpj) grava `entity_link` com CF.

## Princípios éticos (não negociáveis)
- Processo sem condenação definitiva **não** é culpa. Votação simbólica **não** é voto individual.
- Texto para o leitor: linguagem simples, sempre com nível de certeza e link para a fonte oficial.
- CPF/CNPJ só de fontes oficiais abertas; nada de dados de parentes/terceiros não públicos (LGPD).

## Convenções
- Python ≥ 3.11, `ruff` + `pytest`. Commits: conventional commits. Branches descritivos (`feature/...`, `fix/...`). 1 PR por tarefa.
