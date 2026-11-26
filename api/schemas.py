"""Respostas da API que não existem em contracts/ (envelopes, paginação, perfil).

Só Pydantic puro (sem FastAPI): scripts/export_schemas.py exporta estes modelos junto com os de
contracts/ para o web gerar tipos TS. Findings, Explanation e GraphNode/GraphEdge continuam sendo
os de contracts/.
"""
from __future__ import annotations

from datetime import date, datetime
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


class OcultoResumo(BaseModel):
    """O que o limite de nós cortou do grafo, agrupado por tipo de nó e relação."""

    tipo: str  # tipo do nó cortado (empresa, municipio, ...)
    relacao: str | None  # relação que ligava o nó cortado; None = não informada
    quantidade: int


class GrafoResposta(BaseModel):
    centro: str
    profundidade: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    truncado: bool  # True: o limite de nós cortou a expansão
    # v0.2.0 (opcionais): tamanho do subgrafo completo e resumo do que foi cortado.
    total_nos: int | None = None
    total_arestas: int | None = None
    ocultos: list[OcultoResumo] = Field(default_factory=list)


class BacklinksResposta(BaseModel):
    node_id: str
    total: int
    backlinks: list[Backlink]


class Diagnostico(BaseModel):
    """Por que um passo da prova ficou inconclusivo, em forma legível por máquina.

    Convenção de `detalhes` para a R01: `n_votos_validos`, `minimo_votos`, `taxa`, `limiar`.
    """

    motivo: Literal["dados_insuficientes", "abaixo_do_limiar", "sem_regra_aplicavel"]
    detalhes: dict[str, float | int | str] = Field(default_factory=dict)


class PassoProva(BaseModel):
    profundidade: int
    objetivo: str
    regra: str | None
    cf: float
    nota: str
    diagnostico: Diagnostico | None = None  # v0.2.0


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


# --------------------------------------------------------------------------- cobertura e métricas
# v0.2.0: modelos prontos, ainda sem endpoint (a lógica que os preenche vem depois).
class JanelaVotos(BaseModel):
    """Período e volume das votações usadas pelas regras de votação."""

    inicio: date | None
    fim: date | None
    n_votacoes: int
    n_votacoes_nominais: int
    n_votacoes_com_orientacao: int


class FonteCobertura(BaseModel):
    """O que a base tem de cada fonte oficial e de quando é."""

    fonte: str
    tipos: list[str]
    n_fatos: int
    coletado_em_min: datetime | None
    coletado_em_max: datetime | None


class CoberturaResposta(BaseModel):
    contract_version: str
    janela_votos: JanelaVotos
    fontes: list[FonteCobertura]
    n_deputados: int
    n_findings: int


class MetricaRegra(BaseModel):
    regra: str
    finding_id: str | None  # None = a regra não gerou finding para este deputado
    valores: dict[str, float | int | str]


class MetricasDeputadoResposta(BaseModel):
    deputado_id: int
    n_votos: int
    n_votos_validos: int
    janela_votos: JanelaVotos
    metricas_por_regra: list[MetricaRegra]
