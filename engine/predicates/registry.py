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


