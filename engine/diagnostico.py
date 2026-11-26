"""Diagnóstico de um passo inconclusivo da prova (encadeamento regressivo).

Só descreve por que uma regra não concluiu; nunca muda CF nem decisão. `detalhes` usa só escalares
(número ou texto), para serializar direto na API (ADR-007).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Motivo = Literal["dados_insuficientes", "abaixo_do_limiar", "sem_regra_aplicavel"]


@dataclass
class Diagnostico:
    motivo: Motivo
    detalhes: dict[str, float | int | str] = field(default_factory=dict)


def sem_regra_aplicavel() -> Diagnostico:
    return Diagnostico("sem_regra_aplicavel")
