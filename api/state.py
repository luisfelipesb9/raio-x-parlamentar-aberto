"""Acesso ao banco + cache do grafo/índices. Único lugar de api/ que fala com o DuckDB.

Só SELECT, em conexão somente leitura. O `Snapshot` é construído uma vez por processo e vale até
a API reiniciar: o DuckDB não deixa outro processo escrever no arquivo enquanto a API o mantém
aberto, então o banco não muda por baixo dela. Pare a API antes de `make ingest`/`make infer`.
"""
from __future__ import annotations

import logging
import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from api.schemas import DeputadoResumo
from contracts import Explanation, Fact, Finding, GraphEdge, GraphNode
from engine import backward, forward
from engine.factbase import FactBase
from engine.rules import Rule, load_rules
from graph import SAL_ID, normaliza_nome, project
from repo.store import DB_PATH, Store

log = logging.getLogger("raio_x.api")

CAMPOS_CPF_TERCEIROS = (("doacao", "$.doador_cpf_cnpj"), ("socio", "$.cpf_cnpj"), ("pep", "$.cpf"),
                        ("despesa_ceap", "$.cpf"))
RAIZ = Path(__file__).resolve().parent.parent  # raiz do projeto (caminhos relativos partem daqui)


@dataclass
class Snapshot:
    facts: list[Fact]
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    deputados: dict[str, DeputadoResumo]
    ordem: list[str]  # ids ordenados por nome (sem acento) — base da listagem paginada
    findings: dict[str, list[Finding]]  # por deputado, cf desc
    nos_por_id: dict[str, GraphNode]
    vizinhos: dict[str, set[str]]
    provas: dict[tuple[str, str], Any] = field(default_factory=dict)  # cache de /perguntar
    forward: Any = None  # InferenceResult único do snapshot (todas as regras, guardrails aplicados)


class AppState:
    def __init__(self, store: Store | None, db_path: str | Path | None) -> None:
        self._store = store
        self._db_path = db_path
        self._lock = threading.RLock()  # DuckDB: uma conexão, acesso serializado
        self._snap: Snapshot | None = None
        self._rules: list[Rule] | None = None

    # ---- conexão ----
    def _get_store(self) -> Store:
        if self._store is not None:
            return self._store
        path = Path(self._db_path or os.environ.get("RAIO_X_DB") or DB_PATH)
        if not path.is_absolute():
            path = RAIZ / path
        try:
            self._store = Store(path, read_only=True)  # a API nunca escreve nem cria o banco
        except FileNotFoundError:
            log.error("banco não encontrado: %s", path)
            raise HTTPException(503, "Banco de dados indisponível: rode `make ingest` e "
                                     "`make infer` antes de subir a API.") from None
        return self._store

    def fechar(self) -> None:
        with self._lock:
            if self._store is not None:
                self._store.con.close()

    # ---- regras ----
    def regras(self) -> list[Rule]:
        with self._lock:
            if self._rules is None:
                self._rules = load_rules()
            return self._rules

    # ---- snapshot ----
    def snapshot(self) -> Snapshot:
        with self._lock:
            if self._snap is None:
                self._snap = self._construir(self._get_store())
            return self._snap

    def _construir(self, store: Store) -> Snapshot:
        facts = store.load_facts()
        findings = [Finding.model_validate_json(r[0]) for r in
                    store.con.execute("SELECT payload FROM finding").fetchall()]
        nodes, edges = project(facts, findings,
                               sal_id=os.environ.get("RAIO_X_ID_SALT") or SAL_ID)
        deputados = {
            f.chave: DeputadoResumo(
                id=f.chave, nome=f.atributos.get("nome") or f"Deputado {f.chave}",
                partido=f.atributos.get("partido"), uf=f.atributos.get("uf"),
                foto=f.atributos.get("foto"))
            for f in facts if f.tipo == "deputado"}
        por_dep: dict[str, list[Finding]] = defaultdict(list)
        for fd in findings:
            por_dep[fd.deputado_id].append(fd)
        for lista in por_dep.values():
            lista.sort(key=lambda x: (-x.cf, x.id))
        vizinhos: dict[str, set[str]] = defaultdict(set)
        for e in edges:
            vizinhos[e.origem].add(e.destino)
            vizinhos[e.destino].add(e.origem)
        return Snapshot(
            facts=facts, nodes=nodes, edges=edges, deputados=deputados,
            ordem=sorted(deputados, key=lambda i: (normaliza_nome(deputados[i].nome), i)),
            findings=dict(por_dep), nos_por_id={n.id: n for n in nodes}, vizinhos=dict(vizinhos))

    def prova(self, snap: Snapshot, objetivo: str, deputado: str) -> backward.GoalAnswer:
        """Encadeamento regressivo com UM forward.run por snapshot (todas as regras)."""
        chave = (deputado, objetivo)
        with self._lock:
            if chave not in snap.provas:
                regras = self.regras()
                if snap.forward is None:
                    snap.forward = forward.run(FactBase(snap.facts), regras)
                # `fb` só é usado pelo prove quando não há `resultado`: não montamos um à toa
                snap.provas[chave] = backward.prove(objetivo, deputado, FactBase(), regras,
                                                    resultado=snap.forward)
            return snap.provas[chave]

    def contagens(self) -> tuple[int, int, bool]:
        """(deputados, findings, pseudonimizado) sem montar o snapshot.

        `pseudonimizado` = nenhum CPF íntegro de terceiro nos fatos (doador, sócio, PEP, despesa PF);
        valores `hmac:...` e mascarados não contam."""
        with self._lock:
            q = self._get_store().con.execute
            n_dep = q("SELECT count(*) FROM fact WHERE tipo = 'deputado'").fetchone()[0]
            n_fin = q("SELECT count(*) FROM finding").fetchone()[0]
            n_cpf = sum(q(
                "SELECT count(*) FROM (SELECT json_extract_string(atributos, ?) AS v FROM fact "
                "WHERE tipo = ?) WHERE v IS NOT NULL AND v NOT LIKE 'hmac:%' AND v NOT LIKE '%*%' "
                "AND length(regexp_replace(v, '[^0-9]', '', 'g')) = 11",
                [campo, tipo]).fetchone()[0] for tipo, campo in CAMPOS_CPF_TERCEIROS)
        return int(n_dep), int(n_fin), n_cpf == 0

    # ---- consultas pontuais (parametrizadas) ----
    def explicacao(self, finding_id: str) -> Explanation | None:
        with self._lock:
            row = self._get_store().con.execute(
                "SELECT explanation FROM finding WHERE id = ?", [finding_id]).fetchone()
        return Explanation.model_validate_json(row[0]) if row else None
