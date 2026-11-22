"""Fatores de certeza no estilo MYCIN (Shortliffe & Buchanan, 1975).

CF em [-1, 1]: 1 = certeza de que é verdade, -1 = certeza de que é falso, 0 = sem informação.
"""
from __future__ import annotations


def combine(cf1: float, cf2: float) -> float:
    """Combina duas evidências independentes para a MESMA conclusão."""
    if cf1 >= 0 and cf2 >= 0:
        return cf1 + cf2 * (1 - cf1)
    if cf1 < 0 and cf2 < 0:
        return cf1 + cf2 * (1 + cf1)
    return (cf1 + cf2) / (1 - min(abs(cf1), abs(cf2)))


def combine_all(cfs: list[float]) -> float:
    total = 0.0
    for cf in cfs:
        total = combine(total, cf)
    return total


def propagate(cf_rule: float, cf_premises: list[float]) -> float:
    """CF da conclusão = CF da regra × menor CF das premissas (conjunção)."""
    if not cf_premises:
        return cf_rule
    return cf_rule * max(0.0, min(cf_premises))


def penalize(cf: float, fatores: list[float]) -> float:
    """Aplica penalidades multiplicativas (ex.: CPF mascarado ×0.4)."""
    for f in fatores:
        cf *= f
    return cf
