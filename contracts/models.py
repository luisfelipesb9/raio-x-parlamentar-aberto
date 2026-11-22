from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

CONTRACT_VERSION = "0.1.0"


class Fact(BaseModel):
    """Um fato da base de fatos. Sempre rastreável até a fonte oficial."""

    tipo: str  # ex.: "deputado", "voto", "votacao", "despesa_ceap", "sancao"
    chave: str  # identificador estável dentro do tipo (ex.: id_deputado, cnpj)
    atributos: dict[str, Any] = Field(default_factory=dict)
    fonte: str  # ex.: "camara_api_v2"
    id_oficial: str
    url: str | None = None
    coletado_em: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Evidence(BaseModel):
    tipo: str
    id_oficial: str
    url: str | None = None
    descricao: str | None = None


class Nivel(str, Enum):
    ALTA = "alta"  # cf >= 0.7
    MEDIA = "media"  # 0.4 <= cf < 0.7
    INDICIO = "indicio"  # 0.2 <= cf < 0.4
    INCONCLUSIVO = "inconclusivo"  # cf < 0.2

    @classmethod
    def from_cf(cls, cf: float) -> Nivel:
        if cf >= 0.7:
            return cls.ALTA
        if cf >= 0.4:
            return cls.MEDIA
        if cf >= 0.2:
            return cls.INDICIO
        return cls.INCONCLUSIVO


class Finding(BaseModel):
    """Conclusão do motor. Contrato de fronteira engine → api → web."""

    id: str
    deputado_id: str
    regra: str
    categoria: str  # "votacao" | "gastos" | "integridade" | "producao" | "emendas"
    conclusao: str  # texto em linguagem simples para leigos
    cf: float = Field(ge=-1, le=1)
    nivel: Nivel
    evidencias: list[Evidence] = Field(default_factory=list)
    guardrails_aplicados: list[str] = Field(default_factory=list)
    valores: dict[str, Any] = Field(default_factory=dict)


class ExplanationStep(BaseModel):
    regra: str
    condicao: str
    resultado: bool
    detalhe: str | None = None


class Explanation(BaseModel):
    """Trilha 'Como cheguei aqui' + 'Por que isso importa'."""

    finding_id: str
    como: list[ExplanationStep]
    por_que: str
    limitacoes: list[str] = Field(default_factory=list)
