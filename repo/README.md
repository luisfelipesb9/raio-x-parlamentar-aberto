# repo/
Único lugar que fala SQL. DuckDB no MVP; trocar para Postgres altera só esta pasta. Dono: Luis.

- `Store(path=None, read_only=False)`: caminho explícito > `$RAIO_X_DB` > `data/raio_x.duckdb`. Com `read_only=True` não roda migrations nem cria arquivo (erro claro se não existir): use na API.
- Fatos: `upsert_facts` (lotes via NDJSON, ~0,3 s/100 mil fatos), `load_facts`, `facts_by_tipo`, `delete_facts`.
- Ligações: `upsert_links`, `load_links`, `links_to` (backlinks), `save_ambiguities`, `load_ambiguities` (tipos em `repo/links.py`).
- Findings: `save_findings`, `findings_of`.
- `migrations/*.sql` rodam todas, em ordem, a cada abertura (todas idempotentes).
