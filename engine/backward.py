"""Encadeamento regressivo (goal-driven): 'o deputado X <objetivo>?'

prove() resolve o objetivo recursivamente:
  * regra de folha (com `predicado`): vale o CF do finding que o motor progressivo produz;
  * regra composta (com `requer`): CF = cf_regra × min(CF dos sub-objetivos) — `certainty.propagate`
    — e só dispara se TODOS os sub-objetivos tiverem CF > 0;
  * várias regras para o mesmo objetivo: combinadas por MYCIN (`certainty.combine_all`).
Ciclos (a requer b requer a) são detectados pela pilha de objetivos: o ramo cíclico vale CF 0 e é
registrado na trilha, sem travar e sem impedir outros caminhos de prova.
Pergunta interativa ao usuário continua fora de escopo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engine import certainty, forward
from engine.diagnostico import Diagnostico, sem_regra_aplicavel
from engine.factbase import FactBase
from engine.forward import InferenceResult
from engine.predicates import DIAGNOSTICOS
from engine.rules import Rule


@dataclass
class PassoProva:
    profundidade: int
    objetivo: str
    regra: str | None
    cf: float
    nota: str = ""
    # só em passo sem conclusão (cf = 0): da regra que tem diagnosticador, ou `sem_regra_aplicavel`
    # quando nenhuma regra conclui o objetivo; ver ADR-007
    diagnostico: Diagnostico | None = None


@dataclass
class GoalAnswer:
    objetivo: str
    deputado_id: str
    cf: float
    regras_usadas: list[str]
    finding_ids: list[str]
    trilha: list[PassoProva] = field(default_factory=list)


def prove(goal: str, deputado_id: str, fb: FactBase, rules: list[Rule],
          resultado: InferenceResult | None = None) -> GoalAnswer:
    """`resultado`: InferenceResult de um forward.run já feito (com as regras alcançáveis ou todas);
    se passado, não roda o motor progressivo de novo."""
    por_objetivo: dict[str, list[Rule]] = {}
    for r in rules:
        if r.tipo == "inferencia" and r.conclui:
            por_objetivo.setdefault(r.conclui, []).append(r)

    # só as regras alcançáveis a partir do objetivo (+ guardrails) entram no motor progressivo
    alcancaveis: set[str] = set()
    vistos: set[str] = set()
    fila = [goal]
    while fila:
        g = fila.pop()
        if g in vistos:
            continue
        vistos.add(g)
        for r in por_objetivo.get(g, []):
            alcancaveis.add(r.id)
            fila.extend(r.requer)
    if resultado is None:
        relevantes = [r for r in rules if r.tipo == "guardrail" or r.id in alcancaveis]
        resultado = forward.run(fb, relevantes)
    res = resultado
    findings = {f.regra: f for f in res.findings if f.deputado_id == deputado_id}
    # base já restringida pelos guardrails (a do `resultado`, se houver); só serve ao diagnóstico
    base = res.factbase if res.factbase is not None else fb

    def diagnosticar(r: Rule) -> Diagnostico | None:
        """Só a regra com diagnosticador explica por que não concluiu; as demais ficam sem
        diagnóstico e mantêm a `nota` (ex.: sub-objetivos da regra composta)."""
        fn = DIAGNOSTICOS.get(r.predicado or "")
        return fn(base, r.parametros, deputado_id) if fn else None

    trilha: list[PassoProva] = []
    usadas: set[str] = set()
    fids: list[str] = []

    def resolve(obj: str, pilha: tuple[str, ...]) -> float:
        prof = len(pilha)
        if obj in pilha:
            trilha.append(PassoProva(prof, obj, None, 0.0,
                                     f"ciclo detectado: {' -> '.join((*pilha, obj))}"))
            return 0.0
        regras = por_objetivo.get(obj, [])
        if not regras:
            trilha.append(PassoProva(prof, obj, None, 0.0, "sem regra que conclua este objetivo",
                                     sem_regra_aplicavel()))
            return 0.0
        cfs: list[float] = []
        for r in regras:
            idx = len(trilha)
            trilha.append(PassoProva(prof, obj, r.id, 0.0))
            if r.requer:
                subs = [resolve(s, (*pilha, obj)) for s in r.requer]
                cf = certainty.propagate(r.cf, subs) if all(s > 0 for s in subs) else 0.0
                nota = "sub-objetivos: " + ", ".join(f"{s}={c}" for s, c in zip(r.requer, subs))
            else:
                f = findings.get(r.id)
                cf = f.cf if f else 0.0
                nota = "finding " + f.id if f else "condições não satisfeitas"
                if f and cf > 0:
                    fids.append(f.id)
            trilha[idx] = PassoProva(prof, obj, r.id, round(cf, 3), nota,
                                     diagnosticar(r) if cf <= 0 else None)
            if cf > 0:
                usadas.add(r.id)
                cfs.append(cf)
        return certainty.combine_all(cfs)

    cf = resolve(goal, ())
    return GoalAnswer(goal, deputado_id, round(cf, 3), sorted(usadas), sorted(set(fids)), trilha)
