"""Pacote de predicados. Cada regra nova: um módulo aqui, importado abaixo.

Registro via @predicate / @guardrail (engine/predicates/registry.py).
"""
from engine.predicates import circuito, core, emendas, presuncao, producao  # noqa: F401  (registra R01–R08)
from engine.predicates.registry import GUARDRAILS, PREDICATES, Candidate, guardrail, predicate

__all__ = ["GUARDRAILS", "PREDICATES", "Candidate", "guardrail", "predicate"]
