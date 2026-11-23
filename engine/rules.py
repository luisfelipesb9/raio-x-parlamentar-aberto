"""Carrega a base de conhecimento (knowledge/rules/*.yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

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
    predicado: str | None = None  # nome em engine/predicates; ausente só em regra composta
    requer: list[str] = Field(default_factory=list)  # sub-objetivos (regra composta, só regressivo)
    parametros: dict[str, Any] = Field(default_factory=dict)
    se: str | None = None  # condição sobre os valores calculados
    entao: str | None = None  # template da conclusão em linguagem simples
    cf: float = Field(default=1.0, ge=0, le=1)
    penalidades: list[Penalidade] = Field(default_factory=list)
    por_que: str = ""
    limitacoes: list[str] = Field(default_factory=list)
    fonte_metodologica: str | None = None
    prioridade: int = 100  # menor roda antes (guardrails devem ser < 10)

    @model_validator(mode="after")
    def _predicado_xor_requer(self) -> Rule:
        if bool(self.predicado) == bool(self.requer):
            raise ValueError(f"{self.id}: informe exatamente um entre `predicado` e `requer` "
                             "(sub-objetivos); recebido nenhum ou ambos")
        if self.requer and (self.se or self.penalidades):
            raise ValueError(f"{self.id}: regra composta não aceita `se` nem `penalidades` "
                             "(o CF vem de cf × min(sub-objetivos))")
        if self.requer and (self.tipo == "guardrail" or not self.conclui):
            raise ValueError(f"{self.id}: regra composta precisa ser de inferência e ter `conclui`")
        return self


def load_rules(directory: Path = RULES_DIR) -> list[Rule]:
    rules = []
    for path in sorted(directory.glob("R*.yaml")):
        rules.append(Rule.model_validate(yaml.safe_load(path.read_text(encoding="utf-8"))))
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise ValueError(f"ids de regra duplicados: {ids}")
    return sorted(rules, key=lambda r: (r.prioridade, r.id))
