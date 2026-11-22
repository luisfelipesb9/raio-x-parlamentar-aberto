from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str  # "<tipo>:<chave>", ex.: "deputado:204554"
    tipo: str  # deputado | partido | empresa | municipio | proposicao
    rotulo: str
    atributos: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    origem: str
    destino: str
    relacao: str  # votou_com | doou | recebeu | socio_de | autor_de | filiado_a
    peso: float = 1.0
    cf: float = 1.0
    evidencia_ids: list[str] = Field(default_factory=list)
