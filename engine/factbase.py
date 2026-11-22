"""Base de fatos em memória com índice por tipo. O repo/ carrega daqui ou do DuckDB."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable

from contracts import Fact


class FactBase:
    def __init__(self, facts: Iterable[Fact] = ()):
        self._by_tipo: dict[str, list[Fact]] = defaultdict(list)
        self.excluidos: dict[str, list[Fact]] = defaultdict(list)  # removidos por guardrails
        for f in facts:
            self.add(f)

    def add(self, fact: Fact) -> None:
        self._by_tipo[fact.tipo].append(fact)

    def of(self, tipo: str) -> list[Fact]:
        return list(self._by_tipo.get(tipo, []))

    def tipos(self) -> list[str]:
        return list(self._by_tipo)

    def exclude(self, tipo: str, pred: Callable[[Fact], bool], motivo: str) -> int:
        keep, drop = [], []
        for f in self._by_tipo.get(tipo, []):
            (drop if pred(f) else keep).append(f)
        self._by_tipo[tipo] = keep
        self.excluidos[motivo].extend(drop)
        return len(drop)
