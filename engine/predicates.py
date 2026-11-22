"""Predicados: funções que leem a base de fatos e calculam valores para as regras.

Cada regra YAML aponta para um predicado pelo nome. Para adicionar um novo:
    @predicate("nome")
    def f(fb: FactBase, params: dict) -> list[Candidate]: ...
Guardrails usam @guardrail e retornam (quantidade_excluida, descricao).
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from statistics import median
from typing import Any

from contracts import Evidence
from engine.factbase import FactBase


@dataclass
class Candidate:
    deputado_id: str
    valores: dict[str, Any]
    evidencias: list[Evidence] = field(default_factory=list)
    premissas_cf: list[float] = field(default_factory=list)


PREDICATES: dict[str, Callable[[FactBase, dict], list[Candidate]]] = {}
GUARDRAILS: dict[str, Callable[[FactBase, dict], tuple[int, str]]] = {}


def predicate(name: str):
    def deco(fn):
        PREDICATES[name] = fn
        return fn
    return deco


def guardrail(name: str):
    def deco(fn):
        GUARDRAILS[name] = fn
        return fn
    return deco


# ---------------------------------------------------------------- guardrails
@guardrail("somente_votacoes_nominais")
def somente_votacoes_nominais(fb: FactBase, params: dict) -> tuple[int, str]:
    simbolicas = {v.chave for v in fb.of("votacao") if not v.atributos.get("nominal", False)}
    n = fb.exclude("voto", lambda f: f.atributos["votacao_id"] in simbolicas,
                   motivo="R02_votacao_simbolica")
    fb.exclude("votacao", lambda f: f.chave in simbolicas, motivo="R02_votacao_simbolica")
    return n, f"{len(simbolicas)} votações simbólicas não usadas para atribuir voto individual"


# ---------------------------------------------------------------- inferência
@predicate("taxa_governismo")
def taxa_governismo(fb: FactBase, params: dict) -> list[Candidate]:
    """Basômetro: % de votos nominais iguais à orientação do governo."""
    orient = {v.chave: v.atributos.get("orientacao_governo") for v in fb.of("votacao")}
    conv, total = defaultdict(int), defaultdict(int)
    ev: dict[str, list[Evidence]] = defaultdict(list)
    for voto in fb.of("voto"):
        o = orient.get(voto.atributos["votacao_id"])
        escolha = voto.atributos.get("voto")
        if o not in ("Sim", "Não") or escolha not in ("Sim", "Não"):
            continue  # sem orientação ou abstenção/obstrução: fora do denominador
        dep = voto.atributos["deputado_id"]
        total[dep] += 1
        conv[dep] += int(escolha == o)
        ev[dep].append(Evidence(tipo="votacao", id_oficial=voto.atributos["votacao_id"],
                                url=voto.url))
    minimo = params.get("minimo_votacoes", 10)
    out = []
    for dep, n in total.items():
        if n < minimo:
            continue
        out.append(Candidate(dep, {"taxa_governismo": round(conv[dep] / n, 3),
                                   "n_votacoes": n, "taxa_pct": round(100 * conv[dep] / n)},
                             ev[dep][:20]))
    return out


@predicate("fornecedor_sancionado")
def fornecedor_sancionado(fb: FactBase, params: dict) -> list[Candidate]:
    """CNPJ que recebeu CEAP enquanto tinha sanção vigente (CEIS/CNEP)."""
    sancoes = defaultdict(list)
    for s in fb.of("sancao"):
        sancoes[s.atributos["cnpj"]].append(s)
    hits: dict[str, Candidate] = {}
    for d in fb.of("despesa_ceap"):
        cnpj = d.atributos.get("cnpj")
        data = _d(d.atributos.get("data"))
        for s in sancoes.get(cnpj, []):
            ini, fim = _d(s.atributos.get("inicio")), _d(s.atributos.get("fim"))
            if data and ini and data >= ini and (fim is None or data <= fim):
                dep = d.atributos["deputado_id"]
                c = hits.setdefault(dep, Candidate(dep, {"n_despesas": 0, "valor_total": 0.0,
                                                         "cnpjs": []}))
                c.valores["n_despesas"] += 1
                c.valores["valor_total"] = round(c.valores["valor_total"]
                                                 + float(d.atributos.get("valor", 0)), 2)
                if cnpj not in c.valores["cnpjs"]:
                    c.valores["cnpjs"].append(cnpj)
                c.evidencias += [
                    Evidence(tipo="despesa_ceap", id_oficial=d.id_oficial, url=d.url),
                    Evidence(tipo="sancao", id_oficial=s.id_oficial, url=s.url,
                             descricao=s.atributos.get("cadastro")),
                ]
    return list(hits.values())


@predicate("outlier_ceap")
def outlier_ceap(fb: FactBase, params: dict) -> list[Candidate]:
    """Rosie/Serenata simplificado: z-score robusto (MAD) do gasto por categoria."""
    limiar = params.get("z_limiar", 3.5)
    tot: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    ev: dict[tuple[str, str], list[Evidence]] = defaultdict(list)
    for d in fb.of("despesa_ceap"):
        cat, dep = d.atributos.get("categoria", "outros"), d.atributos["deputado_id"]
        tot[cat][dep] += float(d.atributos.get("valor", 0))
        ev[(cat, dep)].append(Evidence(tipo="despesa_ceap", id_oficial=d.id_oficial, url=d.url))
    out: dict[str, Candidate] = {}
    for cat, por_dep in tot.items():
        vals = list(por_dep.values())
        if len(vals) < params.get("minimo_deputados", 5):
            continue
        med = median(vals)
        mad = median(abs(v - med) for v in vals) or 1e-9
        for dep, v in por_dep.items():
            z = 0.6745 * (v - med) / mad
            if z > limiar:
                c = out.setdefault(dep, Candidate(dep, {"categorias": [], "z_max": 0.0}))
                c.valores["categorias"].append(
                    {"categoria": cat, "valor": round(v, 2), "mediana": round(med, 2)})
                c.valores["z_max"] = round(max(c.valores["z_max"], z), 2)
                c.evidencias += ev[(cat, dep)][:10]
    for c in out.values():
        top = max(c.valores["categorias"], key=lambda x: x["valor"] / max(x["mediana"], 1))
        c.valores.update(categoria_top=top["categoria"], valor_top=top["valor"],
                         mediana_top=top["mediana"],
                         vezes_mediana=round(top["valor"] / max(top["mediana"], 1), 1))
    return list(out.values())


def _d(v: Any) -> date | None:
    if v is None or isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])
