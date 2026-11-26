"""Persistência da base de fatos e dos findings em DuckDB. Único módulo com SQL."""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any, NamedTuple

import duckdb

from contracts import Explanation, Fact, Finding
from repo.links import Ambiguidade, EntityLink

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "raio_x.duckdb"
ENV_DB = "RAIO_X_DB"
MIGRATIONS = sorted((Path(__file__).parent / "migrations").glob("*.sql"))
SCHEMA = "\n".join(p.read_text(encoding="utf-8") for p in MIGRATIONS)  # todas idempotentes (IF NOT EXISTS)

_COLUNAS_NDJSON = ("{tipo:'VARCHAR',chave:'VARCHAR',atributos:'VARCHAR',fonte:'VARCHAR',"
                   "id_oficial:'VARCHAR',url:'VARCHAR',coletado_em:'VARCHAR'}")


class JanelaVotosDb(NamedTuple):
    inicio: date | None
    fim: date | None
    n_votacoes: int
    n_votacoes_nominais: int
    n_votacoes_com_orientacao: int


class FonteDb(NamedTuple):
    fonte: str
    tipos: list[str]
    n_fatos: int
    coletado_em_min: datetime | None
    coletado_em_max: datetime | None


def _data(texto: str | None) -> date | None:
    try:
        return date.fromisoformat(texto) if texto else None
    except ValueError:
        return None


def _caminho(path: Path | str | None) -> Path | str:
    """Explícito > variável RAIO_X_DB > data/raio_x.duckdb."""
    if path is not None:
        return path
    return os.environ.get(ENV_DB) or DB_PATH


class Store:
    def __init__(self, path: Path | str | None = None, read_only: bool = False):
        path = _caminho(path)
        if read_only and (path == ":memory:" or not Path(path).exists()):
            raise FileNotFoundError(
                f"banco {path} não existe: modo somente leitura não cria arquivo "
                f"(rode `make ingest` antes ou aponte {ENV_DB} para um banco existente)")
        if path != ":memory:" and not read_only:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(path), read_only=read_only)
        if not read_only:
            self.con.execute(SCHEMA)

    # ---------- fatos ----------

    def upsert_facts(self, facts: Sequence[Fact], lote: int = 50_000) -> int:
        """INSERT OR REPLACE por (tipo, chave), em lotes via NDJSON + read_json do DuckDB
        (~0,3 s/100 mil fatos; `executemany` levava ~88 s). Chave repetida: vale a última."""
        unicos = {(f.tipo, f.chave): f for f in facts}
        itens = list(unicos.values())
        for i in range(0, len(itens), lote):
            self._gravar_lote(itens[i:i + lote])
        return len(itens)

    def _gravar_lote(self, fatos: list[Fact]) -> None:
        with tempfile.TemporaryDirectory(prefix="raio_x_") as d:
            arq = Path(d) / "lote.ndjson"
            with arq.open("w", encoding="utf-8") as f:
                for x in fatos:
                    f.write(json.dumps({
                        "tipo": x.tipo, "chave": x.chave, "fonte": x.fonte,
                        "atributos": json.dumps(x.atributos, ensure_ascii=False, default=str),
                        "id_oficial": x.id_oficial, "url": x.url,
                        "coletado_em": x.coletado_em.isoformat()}, ensure_ascii=False) + "\n")
            self.con.execute(
                "INSERT OR REPLACE INTO fact "
                "SELECT tipo, chave, atributos::JSON, fonte, id_oficial, url, "
                "coletado_em::TIMESTAMPTZ "
                "FROM read_json(?, format='newline_delimited', columns=" + _COLUNAS_NDJSON + ")",
                [str(arq)])

    @staticmethod
    def _fato(r: tuple) -> Fact:
        return Fact(tipo=r[0], chave=r[1], atributos=json.loads(r[2]), fonte=r[3],
                    id_oficial=r[4], url=r[5], coletado_em=r[6])

    def load_facts(self) -> list[Fact]:
        rows = self.con.execute(
            "SELECT tipo, chave, atributos, fonte, id_oficial, url, coletado_em FROM fact"
        ).fetchall()
        return [self._fato(r) for r in rows]

    def facts_by_tipo(self, tipo: str | Iterable[str]) -> list[Fact]:
        tipos = [tipo] if isinstance(tipo, str) else list(tipo)
        if not tipos:
            return []
        marcas = ",".join("?" * len(tipos))
        rows = self.con.execute(
            "SELECT tipo, chave, atributos, fonte, id_oficial, url, coletado_em FROM fact "
            f"WHERE tipo IN ({marcas}) ORDER BY tipo, chave", tipos).fetchall()
        return [self._fato(r) for r in rows]

    def delete_facts(self, tipo: str, *, fonte: str | None = None,
                     onde: Mapping[str, Collection[Any]] | None = None,
                     ano_data: int | None = None) -> int:
        """Apaga fatos de um tipo antes de recarregar (INSERT OR REPLACE não remove chave que
        deixou de existir). Filtros se somam: `fonte`; `onde` = {atributo: valores aceitos}
        (número e texto se igualam; lista vazia não casa nada); `ano_data` = fatos cujo atributo
        `data` é desse ano OU está ausente (não dá para saber a que carga pertence)."""
        sql, args = "DELETE FROM fact WHERE tipo = ?", [tipo]
        if fonte is not None:
            sql += " AND fonte = ?"
            args.append(fonte)
        for atributo, valores in (onde or {}).items():
            vals = [str(v) for v in valores]
            if not vals:
                return 0
            sql += (" AND json_extract_string(atributos, '$.' || ?) IN ("
                    + ",".join("?" * len(vals)) + ")")
            args += [atributo, *vals]
        if ano_data is not None:
            sql += (" AND (json_extract_string(atributos, '$.data') IS NULL"
                    " OR substr(json_extract_string(atributos, '$.data'), 1, 4) = ?)")
            args.append(str(ano_data))
        antes = self.con.execute("SELECT count(*) FROM fact WHERE tipo = ?", [tipo]).fetchone()[0]
        self.con.execute(sql, args)
        depois = self.con.execute("SELECT count(*) FROM fact WHERE tipo = ?", [tipo]).fetchone()[0]
        return antes - depois

    # ---------- cobertura (consultas só de leitura) ----------

    def janela_votos(self) -> JanelaVotosDb:
        """Período e volume das votações: datas (`data`), nominais e com orientação do governo.

        Com orientação = Sim ou Não, as únicas que a R01 usa ("Liberado", vazio e ausente não)."""
        ini, fim, n, nominais, orientadas = self.con.execute(
            "SELECT min(d), max(d), count(*), "
            "count(*) FILTER (WHERE nominal = 'true'), "
            "count(*) FILTER (WHERE orientacao IN ('Sim', 'Não')) "
            "FROM (SELECT substr(json_extract_string(atributos, '$.data'), 1, 10) AS d, "
            "json_extract_string(atributos, '$.nominal') AS nominal, "
            "json_extract_string(atributos, '$.orientacao_governo') AS orientacao "
            "FROM fact WHERE tipo = 'votacao')").fetchone()
        return JanelaVotosDb(_data(ini), _data(fim), int(n), int(nominais), int(orientadas))

    def cobertura_fontes(self) -> list[FonteDb]:
        """Por `fonte`: tipos de fato, quantidade e menor/maior `coletado_em` (ordem alfabética)."""
        rows = self.con.execute(
            "SELECT fonte, list(DISTINCT tipo ORDER BY tipo), count(*), min(coletado_em), "
            "max(coletado_em) FROM fact GROUP BY fonte ORDER BY fonte").fetchall()
        return [FonteDb(r[0], list(r[1]), int(r[2]), r[3], r[4]) for r in rows]

    def contagem_votos(self, deputado_id: str) -> tuple[int, int]:
        """(n_votos, n_votos_validos) do deputado, com as mesmas regras do motor.

        n_votos: votos em votação nominal (a R02 descarta o voto de votação simbólica).
        n_votos_validos: dentre eles, Sim/Não em votação em que o governo orientou Sim/Não, o
        denominador da R01 (`engine.predicates.core._votos_validos`; um teste mantém os dois iguais)."""
        n, validos = self.con.execute(
            "SELECT count(*), "
            "count(*) FILTER (WHERE json_extract_string(v.atributos, '$.voto') IN ('Sim', 'Não') "
            "AND json_extract_string(o.atributos, '$.orientacao_governo') IN ('Sim', 'Não')) "
            "FROM fact v LEFT JOIN fact o ON o.tipo = 'votacao' "
            "AND o.chave = json_extract_string(v.atributos, '$.votacao_id') "
            "WHERE v.tipo = 'voto' AND json_extract_string(v.atributos, '$.deputado_id') = ? "
            "AND (o.chave IS NULL OR json_extract_string(o.atributos, '$.nominal') = 'true')",
            [str(deputado_id)]).fetchone()
        return int(n), int(validos)

    def votos_convergentes(self, deputado_id: str) -> int:
        """Dentre os votos válidos do deputado (ver `contagem_votos`), quantos igualam a orientação."""
        return int(self.con.execute(
            "SELECT count(*) FROM fact v JOIN fact o ON o.tipo = 'votacao' "
            "AND o.chave = json_extract_string(v.atributos, '$.votacao_id') "
            "WHERE v.tipo = 'voto' AND json_extract_string(v.atributos, '$.deputado_id') = ? "
            "AND json_extract_string(o.atributos, '$.nominal') = 'true' "
            "AND json_extract_string(o.atributos, '$.orientacao_governo') IN ('Sim', 'Não') "
            "AND json_extract_string(v.atributos, '$.voto') "
            "= json_extract_string(o.atributos, '$.orientacao_governo')",
            [str(deputado_id)]).fetchone()[0])

    def despesas_por_deputado(self) -> dict[str, tuple[int, int]]:
        """{deputado_id: (n_despesas, total em centavos)} da CEAP. Soma em DECIMAL(18,2), não em
        float, para o total não ganhar nem perder centavo."""
        rows = self.con.execute(
            "SELECT json_extract_string(atributos, '$.deputado_id'), count(*), "
            "sum(CAST(json_extract_string(atributos, '$.valor') AS DECIMAL(18, 2))) "
            "FROM fact WHERE tipo = 'despesa_ceap' GROUP BY 1").fetchall()
        return {r[0]: (int(r[1]), int(r[2] * 100)) for r in rows}

    # ---------- entity_link / ambiguidade ----------

    def upsert_links(self, links: Iterable[EntityLink],
                     substituir_origens: Iterable[str] | None = None) -> int:
        """Grava links (idempotente por origem+destino). Com `substituir_origens`, apaga antes
        TODOS os links dessas origens, para não sobrar ligação que a nova resolução desfez."""
        itens = {(lk.origem, lk.destino): lk for lk in links}
        self._apagar_origens("entity_link", substituir_origens)
        if itens:
            with tempfile.TemporaryDirectory(prefix="raio_x_") as d:
                arq = Path(d) / "links.ndjson"
                with arq.open("w", encoding="utf-8") as f:
                    for lk in itens.values():
                        f.write(json.dumps(lk._asdict(), ensure_ascii=False) + "\n")
                self.con.execute(
                    "INSERT OR REPLACE INTO entity_link SELECT origem, destino, metodo, cf "
                    "FROM read_json(?, format='newline_delimited', columns="
                    "{origem:'VARCHAR',destino:'VARCHAR',metodo:'VARCHAR',cf:'DOUBLE'})",
                    [str(arq)])
        return len(itens)

    def load_links(self, origem_tipo: str | None = None) -> list[EntityLink]:
        sql = "SELECT origem, destino, metodo, cf FROM entity_link"
        args: list[str] = []
        if origem_tipo:
            sql += " WHERE starts_with(origem, ?)"
            args.append(f"{origem_tipo}:")
        rows = self.con.execute(sql + " ORDER BY origem, destino", args).fetchall()
        return [EntityLink(*r) for r in rows]

    def links_to(self, destino: str) -> list[EntityLink]:
        rows = self.con.execute(
            "SELECT origem, destino, metodo, cf FROM entity_link WHERE destino = ? "
            "ORDER BY origem", [destino]).fetchall()
        return [EntityLink(*r) for r in rows]

    def save_ambiguities(self, itens: Iterable[Ambiguidade],
                         substituir_origens: Iterable[str] | None = None) -> int:
        linhas = {a.origem: (a.origem, json.dumps(list(a.candidatos)), a.motivo) for a in itens}
        self._apagar_origens("entity_ambiguity", substituir_origens)
        if linhas:
            self.con.executemany("INSERT OR REPLACE INTO entity_ambiguity VALUES (?, ?, ?)",
                                 list(linhas.values()))
        return len(linhas)

    def load_ambiguities(self) -> list[Ambiguidade]:
        rows = self.con.execute(
            "SELECT origem, candidatos, motivo FROM entity_ambiguity ORDER BY origem").fetchall()
        return [Ambiguidade(r[0], tuple(json.loads(r[1])), r[2]) for r in rows]

    def _apagar_origens(self, tabela: str, origens: Iterable[str] | None) -> None:
        lista = list(dict.fromkeys(origens or []))
        for i in range(0, len(lista), 5000):
            parte = lista[i:i + 5000]
            self.con.execute(f"DELETE FROM {tabela} WHERE origem IN ({','.join('?' * len(parte))})",
                             parte)

    # ---------- findings (contrato com engine/api: não mudar assinaturas) ----------

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
