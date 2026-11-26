"""Pacote de predicados. Cada regra nova: um módulo aqui, importado abaixo.

Registro via @predicate / @guardrail / @diagnostico (engine/predicates/registry.py).
"""
from engine.predicates import circuito, core, emendas, presuncao, producao  # noqa: F401  (registra R01–R08)
from engine.predicates.registry import (
    DIAGNOSTICOS,
    GUARDRAILS,
    PREDICATES,
    Candidate,
    diagnostico,
    guardrail,
    predicate,
)

__all__ = ["DIAGNOSTICOS", "GUARDRAILS", "PREDICATES", "Candidate", "diagnostico", "guardrail",
           "predicate"]
