"""Fatiamento de janela de datas para a API de votações da Câmara.

A API recusa (HTTP 400: "A diferença entre as datas não pode ser maior que 3 meses", medido em
2026-11-26) uma janela `dataInicio`..`dataFim` maior que 3 meses. Esta função devolve fatias
contíguas, sem lacuna nem sobreposição, cada uma de no máximo 3 meses.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

MESES_POR_FATIA = 3


def _soma_meses(d: date, meses: int) -> date:
    indice = d.year * 12 + (d.month - 1) + meses
    ano, mes = divmod(indice, 12)
    return date(ano, mes + 1, min(d.day, calendar.monthrange(ano, mes + 1)[1]))


def fatiar_janela(inicio: str, fim: str, meses: int = MESES_POR_FATIA) -> list[tuple[str, str]]:
    """[(início, fim)] em ISO, fatias contíguas de até `meses` meses cobrindo `inicio`..`fim`."""
    if meses < 1:
        raise ValueError(f"meses por fatia deve ser >= 1, recebi {meses}")
    ini, ate = date.fromisoformat(inicio), date.fromisoformat(fim)
    if ini > ate:
        raise ValueError(f"início ({inicio}) depois do fim ({fim})")
    fatias: list[tuple[str, str]] = []
    atual = ini
    while atual <= ate:
        fim_fatia = min(_soma_meses(atual, meses) - timedelta(days=1), ate)
        fatias.append((atual.isoformat(), fim_fatia.isoformat()))
        atual = fim_fatia + timedelta(days=1)
    return fatias
