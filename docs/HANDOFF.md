# HANDOFF — divisão Luis (metade 1) → Pedro Rodrigues (metade 2)

## Como rodar
```
make setup && make test          # 13 testes
uv run python -m ingest.pipeline --max-votacoes 250   # Câmara real, ~2 min
make infer                       # gera findings no data/raio_x.duckdb
```

## Metade 1 — Luis
| Item | Status |
|---|---|
| Estrutura do repo, AGENTS.md, READMEs, CODEOWNERS, CI | ✅ |
| contracts/ (Fact, Finding, Explanation, Graph) v0.1.0 | ✅ |
| engine: CF MYCIN, loader YAML, forward chaining, guardrails, explicação | ✅ |
| engine/backward.py (objetivo único) | ✅ básico |
| R01 governismo · R02 guardrail simbólica · R03 fornecedor sancionado · R04 outlier CEAP | ✅ com testes |
| sources/camara (deputados, votações, votos, orientação) | ✅ testado com API real |
| repo/ DuckDB (fact, finding, entity_link) | ✅ |
| sources/ceap (camara.leg.br/cotas/Ano-{ano}.json.zip) → `despesa_ceap` | ⏳ |
| sources/cgu (CEIS/CNEP downloads, emendas) → `sancao`, `emenda` | ⏳ |
| sources/tse (candidatos/receitas, CPF) → `candidatura`, `doacao` | ⏳ |
| sources/opensanctions (br_pep CSV) → `pep` | ⏳ |
| sources/rfb via BrasilAPI só p/ CNPJs vistos → `empresa`, `socio` | ⏳ |
| ingest/resolve: CPF TSE↔id_deputado, CNPJ↔RFB, gravar entity_link com CF | ⏳ |
| DB de amostra versionado para o Pedro desenvolver offline | ⏳ |

Atributos esperados pelas regras: `despesa_ceap{deputado_id, cnpj, valor, categoria, data}`,
`sancao{cnpj, cadastro, inicio, fim}`.

## Metade 2 — Pedro
| Item | Detalhe |
|---|---|
| R05 Produção ponderada | iniciativa = autoria + 0,25·coautoria; 32·(1−e^(−ini/25)) + relatoria 8·(1−e^(−rel/10,57)); fonte Radar da República V2 |
| R06 Circuito doador‑sócio‑fornecedor | CNPJ recebeu CEAP/emenda E sócio (QSA) = doador PF; penalidade ×0,4 se CPF mascarado |
| R07 Concentração de emendas | % votos no município destinatário ≫ média estadual (Radar do Voto) |
| R08 Guardrail presunção/lacuna | média partidária só como contexto; processo sem trânsito em julgado não reduz nada |
| backward chaining com sub-objetivos | ver TODO em engine/backward.py |
| graph/ | projetar fatos/findings → GraphNode/GraphEdge |
| api/ FastAPI | endpoints em api/README.md, respostas = contracts |
| web/ Next.js | ficha leiga, semáforo, "Como sabemos disso?", grafo Cytoscape com backlinks, comparação, glossário |
| e2e + teste com leigos + relatório e apresentação | tests/e2e, docs/relatorio |

Regra de ouro para o Pedro: **não alterar contracts/ sem ADR**; regras novas só em YAML + predicado.
