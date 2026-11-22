"""Módulo de explicação: 'Como cheguei aqui' e 'Por que isso importa'."""
from __future__ import annotations

from contracts import Explanation, ExplanationStep, Finding
from engine.rules import Rule


def build(finding: Finding, rule: Rule, guardrail_log: dict[str, str],
          penalidades: list[str]) -> Explanation:
    como = [ExplanationStep(regra=g, condicao="guardrail", resultado=True, detalhe=d)
            for g, d in guardrail_log.items()]
    como.append(ExplanationStep(regra=rule.id, condicao=rule.se or "(sem condição)",
                                resultado=True, detalhe=_fmt(finding.valores)))
    como += [ExplanationStep(regra=rule.id, condicao="penalidade", resultado=True, detalhe=p)
             for p in penalidades]
    return Explanation(finding_id=finding.id, como=como, por_que=rule.por_que,
                       limitacoes=rule.limitacoes)


def _fmt(valores: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in valores.items() if not isinstance(v, (list, dict)))
