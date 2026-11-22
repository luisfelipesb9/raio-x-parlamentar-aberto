"""Carrega a base de conhecimento (knowledge/rules/*.yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

RULES_DIR = Path(__file__).resolve().parent.parent / "knowledge" / "rules"


class Penalidade(BaseModel):
    se: str
    fator: float = Field(gt=0, le=1)
    motivo: str


class Rule(BaseModel):
    id: str
    nome: str
    tipo: Literal["inferencia", "guardrail"] = "inferencia"
    categoria: str = "geral"
    conclui: str | None = None  # objetivo provado (usado no encadeamento regressivo)
    predicado: str  # nome em engine/predicates.py
    parametros: dict[str, Any] = Field(default_factory=dict)
    se: str | None = None  # condição sobre os valores calculados
    entao: str | None = None  # template da conclusão em linguagem simples
    cf: float = Field(default=1.0, ge=0, le=1)
    penalidades: list[Penalidade] = Field(default_factory=list)
    por_que: str = ""
    limitacoes: list[str] = Field(default_factory=list)
    fonte_metodologica: str | None = None
    prioridade: int = 100  # menor roda antes (guardrails devem ser < 10)


def load_rules(directory: Path = RULES_DIR) -> list[Rule]:
    rules = []
    for path in sorted(directory.glob("R*.yaml")):
        rules.append(Rule.model_validate(yaml.safe_load(path.read_text(encoding="utf-8"))))
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise ValueError(f"ids de regra duplicados: {ids}")
    return sorted(rules, key=lambda r: (r.prioridade, r.id))
