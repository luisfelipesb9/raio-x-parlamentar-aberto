"""Predicados: funções que leem a base de fatos e calculam valores para as regras.

Cada regra YAML aponta para um predicado pelo nome. Para adicionar um novo:
    @predicate("nome")
    def f(fb: FactBase, params: dict) -> list[Candidate]: ...
Guardrails usam @guardrail e retornam (quantidade_excluida, descricao).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from contracts import Evidence
from engine.diagnostico import Diagnostico
from engine.factbase import FactBase


@dataclass
class Candidate:
    deputado_id: str
    valores: dict[str, Any]
    evidencias: list[Evidence] = field(default_factory=list)
    premissas_cf: list[float] = field(default_factory=list)


PREDICATES: dict[str, Callable[[FactBase, dict], list[Candidate]]] = {}
GUARDRAILS: dict[str, Callable[[FactBase, dict], tuple[int, str]]] = {}
# Opcional: por que o predicado não produziu candidato para um deputado (usado pelo regressivo).
# (fb, parametros da regra, deputado_id) -> Diagnostico, ou None quando não há o que dizer.
DIAGNOSTICOS: dict[str, Callable[[FactBase, dict, str], Diagnostico | None]] = {}


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


def diagnostico(name: str):
    """Registra o diagnosticador do predicado `name` (opcional; sem ele vale `sem_regra_aplicavel`)."""
    def deco(fn):
        DIAGNOSTICOS[name] = fn
        return fn
    return deco


