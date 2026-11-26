"""Acesso ao banco + cache do grafo/índices. Único lugar de api/ que fala com o DuckDB.

Só SELECT, em conexão somente leitura. O snapshot é construído uma vez por processo e vale até
a API reiniciar: o DuckDB não deixa outro processo escrever no arquivo enquanto a API o mantém
aberto, então o banco não muda por baixo dela. Pare a API antes de `make ingest`/`make infer`.

Dois modos, escolhidos pelo banco (ADR-011):
* banco PUBLICADO (gerado por `publicar/`: `publicacao_meta.gerado_em` existe): `SnapshotPublicado`
  lê o grafo materializado (`graph_node`/`graph_edge`) e consulta o DuckDB por deputado (findings,
  votos); `/perguntar` usa `inferencia`; `/cobertura` usa `publicacao_meta`. Nunca carrega os fatos;
* banco de TRABALHO completo (`make dev`): `Snapshot` antigo, que carrega todos os fatos e projeta o
  grafo na partida.
"""
from __future__ import annotations

import logging
import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cached_property
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from api.schemas import (
    CoberturaResposta,
    DeputadoResumo,
    FonteCobertura,
    JanelaVotos,
    MetricaRegra,
    MetricasDeputadoResposta,
)
from contracts import CONTRACT_VERSION, Explanation, Fact, Finding, GraphEdge, GraphNode
from engine import backward, forward, proveniencia
from engine.factbase import FactBase
from engine.forward import InferenceResult
from engine.predicates import GUARDRAILS
from engine.rules import Rule, load_rules
from graph import afinidade_votos, normaliza_nome, project, sal_do_ambiente
from repo import proveniencia as manifesto
from repo.store import DB_PATH, Store

log = logging.getLogger("raio_x.api")

CAMPOS_CPF_TERCEIROS = (("doacao", "$.doador_cpf_cnpj"), ("socio", "$.cpf_cnpj"), ("pep", "$.cpf"),
                        ("despesa_ceap", "$.cpf"))
RAIZ = Path(__file__).resolve().parent.parent  # raiz do projeto (caminhos relativos partem daqui)


def _utc(momento: datetime | None) -> datetime | None:
    return momento.astimezone(UTC) if momento else None


def _escalares(valores: dict[str, Any]) -> dict[str, float | int | str]:
    """Reduz os `valores` de um finding ao que MetricaRegra aceita (número ou texto).

    Lista vira `n_<chave>` (quantidade de itens). Ficam de fora: ausente (None), dict e booleano
    (o schema converteria `True` em número, e a flag `confirmado_por_cpf` da R06 viraria um campo
    de nome `cpf*` com valor numérico; as flags continuam em `/deputados/{id}/findings`)."""
    out: dict[str, float | int | str] = {}
    for k, v in valores.items():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float, str)):
            out[k] = v
        elif isinstance(v, list):
            out[f"n_{k}"] = len(v)
    return out


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

    def findings_de(self, deputado_id: str) -> list[Finding]:
        return self.findings.get(deputado_id, [])

    def afinidade(self, a: str, b: str) -> Any:
        return afinidade_votos(self.facts, a, b)


class SnapshotPublicado:
    """Leitura do banco enxuto: grafo em memória (objetos leves) e o resto sob demanda, por deputado."""

    def __init__(self, estado: AppState, nodes: list[GraphNode], edges: list[GraphEdge],
                 deputados: dict[str, DeputadoResumo]) -> None:
        self._estado = estado
        self.nodes, self.edges, self.deputados = nodes, edges, deputados
        self.ordem = sorted(deputados, key=lambda i: (normaliza_nome(deputados[i].nome), i))
        self.nos_por_id = {n.id: n for n in nodes}
        self.provas: dict[tuple[str, str], Any] = {}  # cache de /perguntar
        self._findings: dict[str, list[Finding]] = {}
        self._votacoes: list[Fact] | None = None
        self._votos: dict[str, list[Fact]] = {}

    @cached_property
    def vizinhos(self) -> dict[str, set[str]]:
        viz: dict[str, set[str]] = defaultdict(set)
        for e in self.edges:
            viz[e.origem].add(e.destino)
            viz[e.destino].add(e.origem)
        return dict(viz)

    def findings_de(self, deputado_id: str) -> list[Finding]:
        with self._estado._lock:
            if deputado_id not in self._findings:
                self._findings[deputado_id] = self._estado._findings_do_banco(deputado_id)
            return self._findings[deputado_id]

    def votacoes(self) -> list[Fact]:
        with self._estado._lock:
            if self._votacoes is None:
                self._votacoes = self._estado._get_store().facts_by_tipo("votacao")
            return self._votacoes

    def votos(self, deputado_id: str) -> list[Fact]:
        """Votos de um deputado, lidos do banco uma vez por processo (`/comparar` e `/perguntar` repetem)."""
        with self._estado._lock:
            if deputado_id not in self._votos:
                self._votos[deputado_id] = self._estado._get_store().votos_do_deputado(deputado_id)
            return self._votos[deputado_id]

    def afinidade(self, a: str, b: str) -> Any:
        """Mesma conta de `graph.afinidade_votos`, só com as votações e os votos dos dois deputados."""
        return afinidade_votos([*self.votacoes(), *self.votos(a), *self.votos(b)], a, b)


class AppState:
    def __init__(self, store: Store | None, db_path: str | Path | None,
                 raw_dir: str | Path | None = None) -> None:
        self.sal_id = sal_do_ambiente()  # falha na subida da API se RAIO_X_ID_SALT não existir
        self._store = store
        self._db_path = db_path
        self._raw_dir = raw_dir
        self._lock = threading.RLock()  # DuckDB: uma conexão, acesso serializado
        self._snap: Snapshot | None = None
        self._rules: list[Rule] | None = None
        self._janela: JanelaVotos | None = None
        self._cobertura: CoberturaResposta | None = None
        self._modo_publicado: bool | None = None
        self._meta: dict[str, Any] | None = None
        self._sha: dict[str, str] | None = None

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
    def publicado(self) -> bool:
        """Banco gerado por `publicar/` (ADR-011)? Decidido uma vez por processo."""
        with self._lock:
            if self._modo_publicado is None:
                self._modo_publicado = self._get_store().publicado()
            return self._modo_publicado

    def snapshot(self) -> Snapshot | SnapshotPublicado:
        with self._lock:
            if self._snap is None:
                store = self._get_store()
                self._snap = (self._construir_publicado(store) if self.publicado()
                              else self._construir(store))
            return self._snap

    def _construir_publicado(self, store: Store) -> SnapshotPublicado:
        nodes, edges = store.load_graph()
        deputados = {
            f.chave: DeputadoResumo(
                id=f.chave, nome=f.atributos.get("nome") or f"Deputado {f.chave}",
                partido=f.atributos.get("partido"), uf=f.atributos.get("uf"),
                foto=f.atributos.get("foto"))
            for f in store.facts_by_tipo("deputado")}
        return SnapshotPublicado(self, nodes, edges, deputados)

    def _findings_do_banco(self, deputado_id: str) -> list[Finding]:
        """Findings de UM deputado (banco publicado), com a proveniência completada como no snapshot antigo."""
        store = self._get_store()
        findings = [Finding.model_validate_json(r[0]) for r in store.con.execute(
            "SELECT payload FROM finding WHERE deputado_id = ?", [deputado_id]).fetchall()]
        pares = {(e.tipo, e.id_oficial) for f in findings for e in f.evidencias}
        findings = self._enriquecer(findings, proveniencia.indexar(store.fatos_leves(pares)))
        return sorted(findings, key=lambda x: (-x.cf, x.id))

    def _construir(self, store: Store) -> Snapshot:
        facts = store.load_facts()
        findings = self._com_proveniencia(
            [Finding.model_validate_json(r[0]) for r in
             store.con.execute("SELECT payload FROM finding").fetchall()], facts)
        nodes, edges = project(facts, findings,
                               sal_id=self.sal_id)
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

    def _com_proveniencia(self, findings: list[Finding], facts: list[Fact]) -> list[Finding]:
        """Completa `coletado_em` e `sha256_bruto` das evidências de findings gravados antes de o
        motor preencher esses campos. Sem manifesto (ex.: deploy sem data/raw), o hash fica vazio."""
        return self._enriquecer(findings, proveniencia.indexar(facts))

    def _enriquecer(self, findings: list[Finding], indice: proveniencia.Indice) -> list[Finding]:
        if self._sha is None:
            try:
                self._sha = manifesto.sha_por_fonte_fato(Path(self._raw_dir or manifesto.raw_dir_padrao()))
            except (ValueError, OSError):
                log.warning("manifest.json ilegível: evidências sem sha256_bruto", exc_info=True)
                self._sha = {}
        return [f.model_copy(update={"evidencias": proveniencia.enriquecer(f.evidencias, indice,
                                                                           self._sha)})
                for f in findings]

    def prova(self, snap: Snapshot | SnapshotPublicado, objetivo: str,
              deputado: str) -> backward.GoalAnswer:
        """Encadeamento regressivo. Banco de trabalho: UM forward.run por snapshot (todas as regras).
        Banco publicado: a `inferencia` do deputado + uma base mínima para o diagnóstico."""
        chave = (deputado, objetivo)
        with self._lock:
            if chave not in snap.provas:
                regras = self.regras()
                if isinstance(snap, SnapshotPublicado):
                    snap.provas[chave] = backward.prove(
                        objetivo, deputado, FactBase(), regras,
                        resultado=self._inferencia_publicada(snap, deputado, regras))
                    return snap.provas[chave]
                if snap.forward is None:
                    snap.forward = forward.run(FactBase(snap.facts), regras)
                # `fb` só é usado pelo prove quando não há `resultado`: não montamos um à toa
                snap.provas[chave] = backward.prove(objetivo, deputado, FactBase(), regras,
                                                    resultado=snap.forward)
            return snap.provas[chave]

    def _inferencia_publicada(self, snap: SnapshotPublicado, deputado: str,
                              regras: list[Rule]) -> InferenceResult:
        """O que `backward.prove` lê do `forward.run`: os findings (da tabela `inferencia`) e a base já
        restringida pelos guardrails, só usada no diagnóstico. A base mínima = todas as votações + os
        votos do deputado, com os mesmos guardrails; basta ao diagnóstico da R01 (ver ADR-011)."""
        base = FactBase([*snap.votacoes(), *snap.votos(deputado)])
        for r in regras:
            if r.tipo == "guardrail":
                GUARDRAILS[r.predicado](base, r.parametros)
        return InferenceResult(findings=self._get_store().inferencia_de(deputado), factbase=base)

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

    # ---- cobertura e métricas (consultas parametrizadas; cache por processo, como o snapshot) ----
    def meta(self) -> dict[str, Any]:
        with self._lock:
            if self._meta is None:
                self._meta = self._get_store().load_publicacao_meta()
            return self._meta

    def janela_votos(self) -> JanelaVotos:
        with self._lock:
            if self._janela is None:
                self._janela = (JanelaVotos(**self.meta()["janela_votos"]) if self.publicado()
                                else JanelaVotos(**self._get_store().janela_votos()._asdict()))
            return self._janela

    def cobertura(self) -> CoberturaResposta:
        """Banco publicado: as contagens do banco COMPLETO vêm de `publicacao_meta` (os fatos
        mantidos subdeclarariam a cobertura por causa do corte)."""
        with self._lock:
            if self._cobertura is None:
                if self.publicado():
                    meta = self.meta()
                    self._cobertura = CoberturaResposta(
                        contract_version=CONTRACT_VERSION, janela_votos=self.janela_votos(),
                        fontes=[FonteCobertura(**f) for f in meta["cobertura_fontes"]],
                        n_deputados=meta["n_deputados"], n_findings=meta["n_findings"])
                    return self._cobertura
                n_dep, n_fin, _ = self.contagens()
                fontes = [FonteCobertura(
                    fonte=f.fonte, tipos=f.tipos, n_fatos=f.n_fatos,
                    coletado_em_min=_utc(f.coletado_em_min), coletado_em_max=_utc(f.coletado_em_max))
                    for f in self._get_store().cobertura_fontes()]
                self._cobertura = CoberturaResposta(
                    contract_version=CONTRACT_VERSION, janela_votos=self.janela_votos(),
                    fontes=fontes, n_deputados=n_dep, n_findings=n_fin)
            return self._cobertura

    def metricas(self, snap: Snapshot | SnapshotPublicado, deputado_id: str) -> MetricasDeputadoResposta:
        """Contagem de votos + os `valores` dos findings do deputado, uma entrada por regra de
        inferência (`finding_id` None quando a regra não gerou finding)."""
        with self._lock:
            n_votos, n_validos = self._get_store().contagem_votos(deputado_id)
        por_regra = {f.regra: f for f in snap.findings_de(deputado_id)}
        metricas = [MetricaRegra(regra=r.id, finding_id=(f.id if (f := por_regra.get(r.id)) else None),
                                 valores=_escalares(f.valores) if f else {})
                    for r in self.regras() if r.tipo == "inferencia"]
        return MetricasDeputadoResposta(
            deputado_id=int(deputado_id), n_votos=n_votos, n_votos_validos=n_validos,
            janela_votos=self.janela_votos(), metricas_por_regra=metricas)

    # ---- consultas pontuais (parametrizadas) ----
    def explicacao(self, finding_id: str) -> Explanation | None:
        with self._lock:
            row = self._get_store().con.execute(
                "SELECT explanation FROM finding WHERE id = ?", [finding_id]).fetchone()
        return Explanation.model_validate_json(row[0]) if row else None
