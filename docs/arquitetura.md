# Arquitetura

## Camadas (dependência só da esquerda para a direita)
```
sources/ ─► ingest/ ─► repo/ (fatos, DuckDB) ─► engine/ ─► graph/ ─► api/ ─► web/
                                   ▲                ▲
                     knowledge/rules/*.yaml   contracts/ (usado por todos)
```
| Camada | Papel no Sistema Especialista |
|---|---|
| sources + ingest | Aquisição de dados (fatos) |
| repo | **Base de fatos** (memória de trabalho persistida) |
| knowledge/rules | **Base de conhecimento** (regras SE/ENTÃO com CF) |
| engine | **Motor de inferência** (forward + backward chaining, MYCIN, guardrails) |
| engine/explain | **Módulo de explicação** (como / por quê / limitações) |
| api + web | **Interface com o usuário** leigo |

## Fluxo de uma inferência
1. `make ingest`: cada `Source` baixa bruto → `data/raw/` → `normalize()` → `Fact` com fonte/id/url.
2. `make infer`: carrega fatos → **guardrails** podam a base (ex.: R02 remove votos de votações simbólicas)
   → cada regra chama seu predicado → avalia `se` → CF = cf_regra × min(premissas) × penalidades
   → `Finding` + `Explanation` gravados.
3. API só lê `finding`; web mostra conclusão, semáforo (`nivel`) e trilha.

## Níveis de certeza (contracts.Nivel)
alta ≥ 0.7 · média ≥ 0.4 · indício ≥ 0.2 · inconclusivo < 0.2

## Escala
DuckDB → Postgres (só `repo/`); cron → Prefect/Dagster (um job por source); lote → reavaliação
incremental por tipo de fato; Câmara → Senado/estados = novos plugins. Ver docs/adr/.
