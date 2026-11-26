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

from contracts import Explanation, Fact, Finding, GraphEdge, GraphNode
from repo.links import Ambiguidade, EntityLink

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "raio_x.duckdb"
ENV_DB = "RAIO_X_DB"
MIGRATIONS = sorted((Path(__file__).parent / "migrations").glob("*.sql"))
SCHEMA = "\n".join(p.read_text(encoding="utf-8") for p in MIGRATIONS)  # todas idempotentes (IF NOT EXISTS)
# Arquivo público (ADR-011): só as tabelas novas; fact/finding/entity_* nascem por CREATE TABLE AS, sem chave primária.
SCHEMA_PUBLICACAO = (Path(__file__).parent / "migrations" / "003_publicacao.sql").read_text(encoding="utf-8")
TABELAS_PUBLICACAO = ("graph_node", "graph_edge", "inferencia", "publicacao_meta")
CHAVE_PUBLICADO = "gerado_em"  # a API só usa as tabelas novas se `publicacao_meta` tiver esta chave

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
    def __init__(self, path: Path | str | None = None, read_only: bool = False, *,
                 so_publicacao: bool = False):
        path = _caminho(path)
        if read_only and (path == ":memory:" or not Path(path).exists()):
            raise FileNotFoundError(
                f"banco {path} não existe: modo somente leitura não cria arquivo "
                f"(rode `make ingest` antes ou aponte {ENV_DB} para um banco existente)")
        if path != ":memory:" and not read_only:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(path), read_only=read_only)
        if not read_only:
            self.con.execute(SCHEMA_PUBLICACAO if so_publicacao else SCHEMA)

    @classmethod
    def novo_publico(cls, path: Path | str) -> Store:
        """Arquivo novo do banco público: só as tabelas da publicação; o resto vem de `copiar_enxuto`."""
        if Path(path).exists():
            raise FileExistsError(f"{path} já existe: o passo de publicação não sobrescreve arquivo")
        return cls(path, so_publicacao=True)

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

    def load_findings(self) -> list[Finding]:
        rows = self.con.execute("SELECT payload FROM finding ORDER BY id").fetchall()
        return [Finding.model_validate_json(r[0]) for r in rows]

    # ---------- publicação enxuta (ADR-011): cópia, tabelas materializadas e metadados ----------

    def contagem_por_tipo(self) -> dict[str, int]:
        rows = self.con.execute("SELECT tipo, count(*) FROM fact GROUP BY 1 ORDER BY 1").fetchall()
        return {r[0]: int(r[1]) for r in rows}

    def copiar_enxuto(self, origem: Path | str, *, tipos_integrais: Sequence[str]) -> dict[str, int]:
        """Copia da `origem` (somente leitura) o que a API pública ainda precisa, sem chave primária:
        os fatos dos `tipos_integrais`, mais qualquer fato citado como evidência por algum finding
        (par tipo + id_oficial, como `engine.proveniencia.indexar`); todos os findings e explicações;
        e os `entity_link`/`entity_ambiguity` cujas pontas (`tipo:chave`) foram mantidas.
        Devolve a quantidade de fatos mantidos por tipo."""
        tipos = list(tipos_integrais)
        literal = str(origem).replace("'", "''")
        self.con.execute(f"ATTACH '{literal}' AS origem (READ_ONLY)")
        try:
            self.con.execute(
                "CREATE TEMP TABLE _evidencia AS SELECT DISTINCT json_extract_string(e, '$.tipo') AS tipo, "
                "json_extract_string(e, '$.id_oficial') AS id_oficial FROM (SELECT unnest("
                "from_json(json_extract(payload, '$.evidencias'), '[\"JSON\"]')) AS e FROM origem.finding)")
            self.con.execute(
                "CREATE TABLE fact AS SELECT f.* FROM origem.fact f WHERE (f.tipo IN ("
                + ",".join("?" * len(tipos)) + ") OR EXISTS (SELECT 1 FROM _evidencia e "
                "WHERE e.tipo = f.tipo AND e.id_oficial = f.id_oficial)) "
                # votação simbólica não é voto individual: o voto nem chega ao arquivo público
                "AND NOT (f.tipo = 'voto' AND EXISTS (SELECT 1 FROM origem.fact o WHERE o.tipo = 'votacao' "
                "AND o.chave = json_extract_string(f.atributos, '$.votacao_id') "
                "AND coalesce(json_extract_string(o.atributos, '$.nominal'), 'false') <> 'true')) "
                "ORDER BY f.tipo, f.chave", tipos)
            self.con.execute("CREATE TABLE finding AS SELECT * FROM origem.finding ORDER BY id")
            self.con.execute("CREATE TEMP TABLE _mantida AS SELECT tipo || ':' || chave AS k FROM fact")
            self.con.execute(
                "CREATE TABLE entity_link AS SELECT * FROM origem.entity_link WHERE origem IN "
                "(SELECT k FROM _mantida) AND destino IN (SELECT k FROM _mantida) ORDER BY origem, destino")
            self.con.execute(
                "CREATE TABLE entity_ambiguity AS SELECT * FROM origem.entity_ambiguity WHERE origem IN "
                "(SELECT k FROM _mantida) ORDER BY origem")
        finally:
            self.con.execute("DROP TABLE IF EXISTS _evidencia")
            self.con.execute("DROP TABLE IF EXISTS _mantida")
            self.con.execute("DETACH origem")
        return self.contagem_por_tipo()

    def checkpoint(self) -> None:
        self.con.execute("CHECKPOINT")

    def _carregar_ndjson(self, tabela: str, colunas: Sequence[str], json_colunas: Collection[str],
                         linhas: Iterable[Mapping[str, str]]) -> int:
        """INSERT em lote (NDJSON + read_json, como `upsert_facts`); valores já são texto, e as
        colunas em `json_colunas` viram JSON."""
        with tempfile.TemporaryDirectory(prefix="raio_x_") as d:
            arq = Path(d) / "lote.ndjson"
            n = 0
            with arq.open("w", encoding="utf-8") as f:
                for linha in linhas:
                    f.write(json.dumps(dict(linha), ensure_ascii=False) + "\n")
                    n += 1
            if n:
                spec = "{" + ",".join(f"{c}:'VARCHAR'" for c in colunas) + "}"
                sel = ", ".join(f"{c}::JSON" if c in json_colunas else c for c in colunas)
                self.con.execute(f"INSERT INTO {tabela} SELECT {sel} FROM read_json(?, "
                                 f"format='newline_delimited', columns={spec})", [str(arq)])
        return n

    def save_graph(self, nodes: Sequence[GraphNode], edges: Sequence[GraphEdge]) -> None:
        """Substitui `graph_node`/`graph_edge` pela saída de `graph.project` (calculada uma vez)."""
        self.con.execute("DELETE FROM graph_node")
        self.con.execute("DELETE FROM graph_edge")
        self._carregar_ndjson("graph_node", ("id", "payload"), ("payload",), (
            {"id": n.id, "payload": json.dumps(
                n.model_dump(mode="json", exclude={"id"}), ensure_ascii=False)} for n in nodes))
        self._carregar_ndjson("graph_edge", ("origem", "destino", "rel", "payload"), ("payload",), (
            {"origem": e.origem, "destino": e.destino, "rel": e.relacao, "payload": json.dumps(
                e.model_dump(mode="json", include={"peso", "cf", "evidencia_ids"}),
                ensure_ascii=False)} for e in edges))

    def load_graph(self) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Grafo materializado, na mesma ordem de `graph.project` (nós por id; arestas por
        relação, origem e destino), porque o recorte e os backlinks dependem dela."""
        nos = [GraphNode(id=r[0], **json.loads(r[1])) for r in self.con.execute(
            "SELECT id, payload::VARCHAR FROM graph_node ORDER BY id").fetchall()]
        arestas = [GraphEdge(origem=r[0], destino=r[1], relacao=r[2], **json.loads(r[3]))
                   for r in self.con.execute(
                       "SELECT origem, destino, rel, payload::VARCHAR FROM graph_edge "
                       "ORDER BY rel, origem, destino").fetchall()]
        return nos, arestas

    def save_inferencia(self, findings: Iterable[Finding]) -> int:
        """Substitui `inferencia` pelo resultado do forward.run. Sem as evidências (o regressivo só
        lê id, regra, deputado e CF; as completas ficam em `finding`)."""
        self.con.execute("DELETE FROM inferencia")
        return self._carregar_ndjson("inferencia", ("deputado_id", "regra", "payload"), ("payload",), (
            {"deputado_id": f.deputado_id, "regra": f.regra, "payload": f.model_copy(
                update={"evidencias": []}).model_dump_json()} for f in findings))

    def inferencia_de(self, deputado_id: str) -> list[Finding]:
        rows = self.con.execute("SELECT payload::VARCHAR FROM inferencia WHERE deputado_id = ? "
                                "ORDER BY regra", [str(deputado_id)]).fetchall()
        return [Finding.model_validate_json(r[0]) for r in rows]

    def save_publicacao_meta(self, meta: Mapping[str, Any]) -> None:
        self.con.execute("DELETE FROM publicacao_meta")
        self._carregar_ndjson("publicacao_meta", ("chave", "valor"), ("valor",), (
            {"chave": k, "valor": json.dumps(v, ensure_ascii=False, default=str)}
            for k, v in meta.items()))

    def load_publicacao_meta(self) -> dict[str, Any]:
        rows = self.con.execute("SELECT chave, valor::VARCHAR FROM publicacao_meta "
                                "ORDER BY chave").fetchall()
        return {r[0]: json.loads(r[1]) for r in rows}

    def tabelas_publicacao_faltando(self) -> list[str]:
        existentes = {r[0] for r in self.con.execute(
            "SELECT table_name FROM information_schema.tables").fetchall()}
        return [t for t in TABELAS_PUBLICACAO if t not in existentes]

    def publicado(self) -> bool:
        """Banco gerado por `publicar/`: tabelas novas presentes e `publicacao_meta` preenchida.
        Banco de trabalho (tabelas vazias ou ausentes) dá False e a API usa o caminho antigo."""
        if self.tabelas_publicacao_faltando():
            return False
        return bool(self.con.execute("SELECT count(*) FROM publicacao_meta WHERE chave = ?",
                                     [CHAVE_PUBLICADO]).fetchone()[0])

    # ---------- leituras por deputado (API sob demanda, ADR-011) ----------

    def votos_do_deputado(self, deputado_id: str) -> list[Fact]:
        """Fatos `voto` de um deputado (a API não carrega os votos de todos)."""
        rows = self.con.execute(
            "SELECT tipo, chave, atributos, fonte, id_oficial, url, coletado_em FROM fact "
            "WHERE tipo = 'voto' AND json_extract_string(atributos, '$.deputado_id') = ? "
            "ORDER BY chave", [str(deputado_id)]).fetchall()
        return [self._fato(r) for r in rows]

    def fatos_leves(self, pares: Collection[tuple[str, str]], lote: int = 500) -> list[Fact]:
        """Fatos cujo par (tipo, id_oficial) está em `pares`, SEM `atributos`: só o que a proveniência
        das evidências usa (`fonte`, `coletado_em`). Todos os fatos que repetem o par voltam, como em
        `engine.proveniencia.indexar`."""
        por_tipo: dict[str, list[str]] = {}
        for tipo, id_oficial in pares:
            por_tipo.setdefault(tipo, []).append(id_oficial)
        saida: list[Fact] = []
        for tipo, ids in por_tipo.items():
            for i in range(0, len(ids), lote):
                parte = ids[i:i + lote]
                rows = self.con.execute(
                    "SELECT tipo, chave, fonte, id_oficial, url, coletado_em FROM fact WHERE tipo = ? "
                    f"AND id_oficial IN ({','.join('?' * len(parte))})", [tipo, *parte]).fetchall()
                saida += [Fact(tipo=r[0], chave=r[1], atributos={}, fonte=r[2], id_oficial=r[3],
                               url=r[4], coletado_em=r[5]) for r in rows]
        return saida
