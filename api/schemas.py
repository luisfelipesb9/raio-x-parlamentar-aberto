"""Respostas da API que não existem em contracts/ (envelopes, paginação, perfil).

Só Pydantic puro (sem FastAPI): scripts/export_schemas.py exporta estes modelos junto com os de
contracts/ para o web gerar tipos TS. Findings, Explanation e GraphNode/GraphEdge continuam sendo
os de contracts/.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from contracts import Finding, GraphEdge, GraphNode, Nivel
from graph import Afinidade, Backlink


class Problem(BaseModel):
    """Erro no formato RFC 7807 (application/problem+json)."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    errors: list[dict[str, str]] | None = None


class DeputadoResumo(BaseModel):
    id: str
    nome: str
    partido: str | None = None
    uf: str | None = None
    foto: str | None = None


class PaginaDeputados(BaseModel):
    items: list[DeputadoResumo]
    total: int
    page: int
    page_size: int


class ResumoCategoria(BaseModel):
    categoria: str  # votacao | gastos | integridade | producao | emendas
    n_findings: int
    cf_max: float
    nivel_max: Nivel


class PerfilDeputado(DeputadoResumo):
    n_findings: int
    categorias: list[ResumoCategoria] = Field(default_factory=list)


class GrafoResposta(BaseModel):
    centro: str
    profundidade: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncado: bool  # True: o limite de nós cortou a expansão


class BacklinksResposta(BaseModel):
    node_id: str
    total: int
    backlinks: list[Backlink]


class PassoProva(BaseModel):
    profundidade: int
    objetivo: str
    regra: str | None
    cf: float
    nota: str


class PerguntarResposta(BaseModel):
    """Resposta do encadeamento regressivo: 'o deputado X <objetivo>?' com a trilha da prova."""

    objetivo: str
    deputado_id: str
    cf: float
    nivel: Nivel
    regras_usadas: list[str]
    finding_ids: list[str]
    trilha: list[PassoProva]


class ComparacaoCategoria(BaseModel):
    categoria: str
    a: ResumoCategoria | None
    b: ResumoCategoria | None


class ComparacaoResposta(BaseModel):
    a: PerfilDeputado
    b: PerfilDeputado
    categorias: list[ComparacaoCategoria]
    afinidade_votos: Afinidade | None  # None = nenhuma votação nominal em comum
    em_comum: list[GraphNode]  # nós ligados aos dois (fornecedores, doadores, municípios, ...)
    findings_a: list[Finding]
    findings_b: list[Finding]


class Saude(BaseModel):
    status: Literal["ok", "degradado"]
    contract_version: str
    n_deputados: int
    n_findings: int
    banco: Literal["ok", "ausente", "erro"]
    pseudonimizado: bool  # True: nenhum CPF íntegro de terceiro no banco
