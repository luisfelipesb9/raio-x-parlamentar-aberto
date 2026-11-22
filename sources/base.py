"""Interface comum a todos os conectores de dados públicos."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from contracts import Fact

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


class Source(ABC):
    nome: str = "base"

    def raw_path(self, arquivo: str) -> Path:
        p = RAW_DIR / self.nome / arquivo
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @abstractmethod
    def fetch(self, **kwargs: Any) -> dict[str, Any]:
        """Baixa dados brutos, salva em data/raw/<nome>/ e devolve o bruto."""

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> list[Fact]:
        """Converte o bruto em fatos rastreáveis. Função pura (testável com fixture)."""

    def save_raw(self, arquivo: str, data: Any) -> None:
        self.raw_path(arquivo).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
