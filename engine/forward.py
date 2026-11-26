"""Encadeamento progressivo (data-driven): fatos → todas as conclusões possíveis."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from contracts import Explanation, Finding, Nivel
from engine import certainty, explain, proveniencia
from engine.factbase import FactBase
from engine.predicates import GUARDRAILS, PREDICATES
from engine.rules import Rule
from engine.safe_expr import evaluate


@dataclass
class InferenceResult:
    findings: list[Finding] = field(default_factory=list)
    explanations: dict[str, Explanation] = field(default_factory=dict)
    guardrail_log: dict[str, str] = field(default_factory=dict)
    # base de fatos já restringida pelos guardrails; o regressivo a usa para diagnosticar
    factbase: FactBase | None = None


def run(fb: FactBase, rules: list[Rule], *,
        sha_por_fonte: Mapping[str, str] | None = None) -> InferenceResult:
    """`sha_por_fonte`: `Fact.fonte` -> sha256 do bruto (só as fontes com um único arquivo);
    vai para `Evidence.sha256_bruto`. Sem ele a evidência traz só o `coletado_em`."""
    res = InferenceResult(factbase=fb)
    indice: proveniencia.Indice | None = None  # montado só se algum finding precisar
    # 1) guardrails primeiro: restringem a base de fatos antes de qualquer conclusão
    for r in (r for r in rules if r.tipo == "guardrail"):
        _, desc = GUARDRAILS[r.predicado](fb, r.parametros)
        res.guardrail_log[r.id] = desc
    # 2) regras de inferência
    # regras compostas (`requer`) só existem no encadeamento regressivo (engine/backward.py)
    for r in (r for r in rules if r.tipo == "inferencia" and not r.requer):
        for cand in PREDICATES[r.predicado](fb, r.parametros):
            env = {**r.parametros, **cand.valores}
            if r.se and not evaluate(r.se, env):
                continue
            cf = certainty.propagate(r.cf, cand.premissas_cf)
            aplicadas = [p for p in r.penalidades if evaluate(p.se, env)]
            cf = certainty.penalize(cf, [p.fator for p in aplicadas])
            if indice is None:
                indice = proveniencia.indexar(f for t in fb.tipos() for f in fb.of(t))
            f = Finding(
                id=f"{r.id}:{cand.deputado_id}", deputado_id=cand.deputado_id, regra=r.id,
                categoria=r.categoria, conclusao=(r.entao or r.nome).format(**env),
                cf=round(cf, 3), nivel=Nivel.from_cf(cf),
                evidencias=proveniencia.enriquecer(cand.evidencias, indice, sha_por_fonte),
                guardrails_aplicados=list(res.guardrail_log), valores=cand.valores,
            )
            res.findings.append(f)
            res.explanations[f.id] = explain.build(
                f, r, res.guardrail_log, [f"{p.motivo} (×{p.fator})" for p in aplicadas])
    return res
