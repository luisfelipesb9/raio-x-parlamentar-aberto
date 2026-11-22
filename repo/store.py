"""Persistência da base de fatos e dos findings em DuckDB. Único módulo com SQL."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from contracts import Explanation, Fact, Finding

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "raio_x.duckdb"
SCHEMA = (Path(__file__).parent / "migrations" / "001_init.sql").read_text()


class Store:
    def __init__(self, path: Path | str = DB_PATH):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(path))
        self.con.execute(SCHEMA)

    def upsert_facts(self, facts: list[Fact]) -> None:
        if not facts:
            return
        rows = [(f.tipo, f.chave, json.dumps(f.atributos, ensure_ascii=False, default=str),
                 f.fonte, f.id_oficial, f.url, f.coletado_em) for f in facts]
        self.con.executemany(
            "INSERT OR REPLACE INTO fact VALUES (?, ?, ?, ?, ?, ?, ?)", rows)

    def load_facts(self) -> list[Fact]:
        rows = self.con.execute("SELECT * FROM fact").fetchall()
        return [Fact(tipo=r[0], chave=r[1], atributos=json.loads(r[2]), fonte=r[3],
                     id_oficial=r[4], url=r[5], coletado_em=r[6]) for r in rows]

    def save_findings(self, findings: list[Finding], expl: dict[str, Explanation]) -> None:
        self.con.execute("DELETE FROM finding")
        if not findings:
            return
        self.con.executemany("INSERT INTO finding VALUES (?, ?, ?, ?, ?, ?)", [
            (f.id, f.deputado_id, f.regra, f.cf, f.model_dump_json(),
             expl[f.id].model_dump_json()) for f in findings])

    def findings_of(self, deputado_id: str) -> list[Finding]:
        rows = self.con.execute("SELECT payload FROM finding WHERE deputado_id = ? "
                                "ORDER BY cf DESC", [deputado_id]).fetchall()
        return [Finding.model_validate_json(r[0]) for r in rows]
