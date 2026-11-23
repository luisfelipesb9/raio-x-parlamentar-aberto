"""Tipos de linha do `entity_link` e do registro de ambiguidade. Sem dependência de banco."""
from __future__ import annotations

from typing import NamedTuple


class EntityLink(NamedTuple):
    """Ligação entre duas entidades. `origem`/`destino` no formato `tipo:chave`."""

    origem: str
    destino: str
    metodo: str  # cpf | cnpj | nome_norm
    cf: float


class Ambiguidade(NamedTuple):
    """Origem que casou com mais de um destino plausível: NÃO vira link, fica registrada."""

    origem: str
    candidatos: tuple[str, ...]
    motivo: str
