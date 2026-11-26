# graph/  (Pedro, fase 2)
Projeção **pura** (sem banco/rede) de fatos + findings em `GraphNode`/`GraphEdge` (`contracts/graph.py`).

```python
from graph import build_graph, project, subgrafo, backlinks, afinidade_votos
nodes, edges = build_graph(facts, findings, centro="deputado:204554", profundidade=1)
```

| nó (`tipo:chave`) | origem |
|---|---|
| `deputado:ID` · `partido:SIGLA` · `proposicao:ID` · `municipio:IBGE` | fatos `deputado`, `proposicao`, `emenda` |
| `empresa:CNPJ` | só CNPJ íntegro (14 dígitos): fornecedor CEAP ou doador PJ |
| `pessoa:cpf:<hash>` | doador PF/sócio com **CPF íntegro**: id = hash salgado do CPF (nunca o CPF); mesmo CPF = mesmo nó, rótulo = nome |
| `pessoa:doador:<hash>` · `pessoa:socio:<cnpj>:<hash>` | CPF mascarado/ausente: **um nó por doação/sócio**, não funde homônimos; rótulo genérico ("Doador(a) pessoa física" / "Sócio(a) de {razão social}"), sem nome em id/rótulo/atributos (LGPD) |

| aresta (origem → destino) | peso | cf |
|---|---|---|
| `filiado_a` deputado → partido | 1 | 1 |
| `recebeu` empresa → deputado (CEAP) | R$ somado | 1 |
| `doou` doador → deputado (via `candidatura.deputado_id`; PJ, PF, partido com sigla conhecida; "proprio" fica fora) | R$ somado | 1 |
| `autor_de` (autor e coautor) / `relator_de` deputado → proposição | 1 | 1 |
| `enviou_emenda` deputado → município | R$ empenhado | 1 |
| `socio_de` pessoa → empresa (só empresas já no grafo) | 1 | 1 com CPF íntegro, **0,4** com CPF mascarado |

Sal do hash: `RAIO_X_ID_SALT` (obrigatório, sem valor padrão: `project`/`build_graph` levantam `SalAusenteError` se ele faltar e `sal_id` não for passado), para que os ids não sejam reversíveis por força bruta do CPF. Muitas doações mascaradas viram muitos nós `pessoa` (o corte `max_nos` da API protege).
| `votou_com` deputado ↔ deputado (simétrica, só top-k por deputado) | % votos iguais | `min(1, n_comuns/30)` |

- **Sanção não é aresta**: a empresa recebe `atributos.sancionada`, `sancao_vigente` e `sancoes[]`.
- Findings anotam `deputado` (`n_findings`, `cf_max`, `nivel_max`) e `empresa` (`findings[]`, via `valores.cnpjs`).
- `evidencia_ids` = `"<tipo>:<chave>"` do fato (até 20, os de maior valor). `votou_com` não tem (é agregado).
- `votou_com`: só votação **nominal**; só Sim/Não/Abstenção/Obstrução ("Artigo 17" fora); mínimo 5
  votações comuns (`min_votacoes_comuns`); k=5 (`votou_com_k`). Máscaras de bits + popcount:
  513 deputados × 150 votações em ~1 s; nunca O(n²) arestas.
- `subgrafo(nodes, edges, centro, profundidade, relacoes=, max_nos=)` → `(nós, arestas, truncado)`;
  travessia não-direcionada, admissão por prioridade de relação (ver `RELACOES`) e depois peso.
- `backlinks(node_id, nodes, edges)` → todas as ligações do nó, as que chegam e as que saem; `no` é a outra ponta
  e o sentido está em `aresta.origem`/`aresta.destino`.
- Saída ordenada e determinística (independe da ordem dos fatos).
