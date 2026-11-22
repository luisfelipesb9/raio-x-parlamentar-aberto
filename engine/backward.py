"""Encadeamento regressivo (goal-driven): 'o deputado X <objetivo>?'

Busca regras cujo campo `conclui` é o objetivo, avalia só essas para o deputado pedido e
combina as evidências por MYCIN. TODO (Pedro, fase 2): sub-objetivos encadeados
(regra cujo `se` referencia outro objetivo) e pergunta interativa ao usuário.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine import certainty, forward
from engine.factbase import FactBase
from engine.rules import Rule


@dataclass
class GoalAnswer:
    objetivo: str
    deputado_id: str
    cf: float
    regras_usadas: list[str]
    finding_ids: list[str]


def prove(goal: str, deputado_id: str, fb: FactBase, rules: list[Rule]) -> GoalAnswer:
    relevantes = [r for r in rules if r.tipo == "guardrail" or r.conclui == goal]
    res = forward.run(fb, relevantes)
    mine = [f for f in res.findings if f.deputado_id == deputado_id]
    return GoalAnswer(goal, deputado_id, round(certainty.combine_all([f.cf for f in mine]), 3),
                      sorted({f.regra for f in mine}), [f.id for f in mine])
