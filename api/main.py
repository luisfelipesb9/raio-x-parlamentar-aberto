"""API FastAPI read-only do Raio-X Parlamentar. Só lê o banco; nunca chama serviço externo.

Rodar: `make dev` (uvicorn api.main:app). Banco: env RAIO_X_DB (padrão data/raio_x.duckdb).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi import Path as PathParam
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.schemas import (
    BacklinksResposta,
    CoberturaResposta,
    ComparacaoCategoria,
    ComparacaoResposta,
    Diagnostico,
    GrafoResposta,
    MetricasDeputadoResposta,
    PaginaDeputados,
    PassoProva,
    PerfilDeputado,
    PerguntarResposta,
    Problem,
    ResumoCategoria,
    Saude,
)
from api.state import AppState, Snapshot
from contracts import CONTRACT_VERSION, Explanation, Finding, GraphNode, Nivel
from graph import RELACOES, afinidade_votos, backlinks, normaliza_nome, subgrafo
from repo.store import Store

log = logging.getLogger("raio_x.api")

ORIGEM_PADRAO = "http://localhost:3000"
ENV_CORS = "RAIO_X_CORS_ORIGINS"  # lista separada por vírgula; padrão só localhost:3000
PAGE_SIZE_MAX = 100
PROFUNDIDADE_MAX = 2
MAX_NOS_GRAFO = 300
MAX_EM_COMUM = 50

ID_DEPUTADO = r"^[A-Za-z0-9_\-]{1,32}$"
ID_DEPUTADO_NUMERICO = r"^[0-9]{1,12}$"  # /metricas devolve o id como inteiro
ID_FINDING =r"^[A-Za-z0-9_.:\-]{1,128}$"
ID_NO = r"^(deputado|partido|empresa|municipio|proposicao|pessoa):[\w .'\-:]{1,120}$"
OBJETIVO = r"^[a-z0-9_]{1,64}$"

NAO_ENCONTRADO = {404: {"model": Problem, "description": "Recurso não encontrado"}}


def _problem(status: int, detail: str | None = None, **extra) -> JSONResponse:
    corpo = Problem(title=HTTPStatus(status).phrase, status=status, detail=detail, **extra)
    return JSONResponse(corpo.model_dump(exclude_none=True), status_code=status,
                        media_type="application/problem+json")


def _perfil(snap: Snapshot, dep_id: str) -> PerfilDeputado:
    base = snap.deputados.get(dep_id)
    if base is None:
        raise HTTPException(404, f"Deputado {dep_id} não encontrado.")
    fs = snap.findings.get(dep_id, [])
    return PerfilDeputado(**base.model_dump(), n_findings=len(fs), categorias=_categorias(fs))


def _categorias(fs: list[Finding]) -> list[ResumoCategoria]:
    por_cat: dict[str, list[Finding]] = {}
    for f in fs:
        por_cat.setdefault(f.categoria, []).append(f)
    return [ResumoCategoria(categoria=c, n_findings=len(v), cf_max=max(x.cf for x in v),
                            nivel_max=Nivel.from_cf(max(x.cf for x in v)))
            for c, v in sorted(por_cat.items())]


def _relacoes(texto: str | None) -> list[str] | None:
    if not texto:
        return None
    rels = [r.strip() for r in texto.split(",") if r.strip()]
    invalidas = sorted(set(rels) - set(RELACOES))
    if invalidas:
        raise HTTPException(422, f"Relações desconhecidas: {invalidas}. Válidas: {list(RELACOES)}.")
    return rels


def _origens() -> list[str]:
    bruto = os.environ.get(ENV_CORS, "")
    lista = [o.strip().rstrip("/") for o in bruto.split(",") if o.strip() and o.strip() != "*"]
    return lista or [ORIGEM_PADRAO]  # "*" é ignorado de propósito


def create_app(db_path: str | Path | None = None, *, store: Store | None = None,
               max_nos_grafo: int = MAX_NOS_GRAFO, raw_dir: str | Path | None = None) -> FastAPI:
    """`raw_dir`: pasta dos brutos com o manifest.json (padrão: `RAIO_X_RAW` ou data/raw); só serve
    para preencher `Evidence.sha256_bruto`. A API nunca lê nem escreve mais nada ali."""
    state = AppState(store, db_path, raw_dir)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        state.fechar()

    app = FastAPI(title="Raio-X Parlamentar", version="0.1.0", lifespan=lifespan,
                  description="API somente leitura sobre dados públicos de deputados federais.")
    app.add_middleware(CORSMiddleware, allow_origins=_origens(), allow_methods=["GET"],
                       allow_headers=[], allow_credentials=False)

    # ---- erros em RFC 7807 ----
    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return _problem(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, exc: RequestValidationError):
        erros = [{"campo": ".".join(str(p) for p in e["loc"]), "mensagem": e["msg"]}
                 for e in exc.errors()]
        return _problem(422, "Parâmetros inválidos.", errors=erros)

    @app.exception_handler(Exception)
    async def _interno(_: Request, exc: Exception):
        log.exception("erro interno", exc_info=exc)  # stack só no log, nunca na resposta
        return _problem(500, "Erro interno.")

    # ---- saúde ----
    @app.get("/saude", response_model=Saude, responses={503: {"model": Saude}})
    def saude(response: Response) -> Saude:
        def degradado(banco: str) -> Saude:
            response.status_code = 503
            return Saude(status="degradado", contract_version=CONTRACT_VERSION, n_deputados=0,
                         n_findings=0, banco=banco, pseudonimizado=False)

        try:
            n_dep, n_fin, pseudo = state.contagens()
        except HTTPException:  # banco ausente (o detalhe com o caminho só vai para o log)
            return degradado("ausente")
        except Exception:
            log.exception("falha ao consultar o banco em /saude")
            return degradado("erro")
        return Saude(status="ok", contract_version=CONTRACT_VERSION, n_deputados=n_dep,
                     n_findings=n_fin, banco="ok", pseudonimizado=pseudo)

    # ---- deputados ----
    @app.get("/deputados", response_model=PaginaDeputados)
    def listar_deputados(
        q: str | None = Query(None, max_length=80, description="trecho do nome (sem acento/caixa)"),
        uf: str | None = Query(None, pattern=r"^[A-Za-z]{2}$"),
        partido: str | None = Query(None, max_length=30),
        page: int = Query(1, ge=1, le=100_000),
        page_size: int = Query(20, ge=1, le=PAGE_SIZE_MAX),
    ) -> PaginaDeputados:
        snap = state.snapshot()
        termo = normaliza_nome(q)
        sigla = normaliza_nome(partido)
        achados = [
            d for d in (snap.deputados[i] for i in snap.ordem)
            if (not termo or termo in normaliza_nome(d.nome))
            and (not uf or (d.uf or "").upper() == uf.upper())
            and (not sigla or normaliza_nome(d.partido) == sigla)]
        ini = (page - 1) * page_size
        return PaginaDeputados(items=achados[ini:ini + page_size], total=len(achados), page=page,
                               page_size=page_size)

    @app.get("/deputados/{deputado_id}", response_model=PerfilDeputado, responses=NAO_ENCONTRADO)
    def perfil(deputado_id: str = PathParam(pattern=ID_DEPUTADO)) -> PerfilDeputado:
        return _perfil(state.snapshot(), deputado_id)

    @app.get("/deputados/{deputado_id}/findings", response_model=list[Finding],
             responses=NAO_ENCONTRADO)
    def findings(deputado_id: str = PathParam(pattern=ID_DEPUTADO)) -> list[Finding]:
        snap = state.snapshot()
        if deputado_id not in snap.deputados:
            raise HTTPException(404, f"Deputado {deputado_id} não encontrado.")
        return snap.findings.get(deputado_id, [])

    @app.get("/deputados/{deputado_id}/metricas", response_model=MetricasDeputadoResposta,
             responses=NAO_ENCONTRADO)
    def metricas(deputado_id: str = PathParam(pattern=ID_DEPUTADO_NUMERICO)
                 ) -> MetricasDeputadoResposta:
        snap = state.snapshot()
        if deputado_id not in snap.deputados:
            raise HTTPException(404, f"Deputado {deputado_id} não encontrado.")
        return state.metricas(snap, deputado_id)

    @app.get("/cobertura", response_model=CoberturaResposta)
    def cobertura() -> CoberturaResposta:
        return state.cobertura()

    @app.get("/findings/{finding_id}/explicar", response_model=Explanation,
             responses=NAO_ENCONTRADO)
    def explicar(finding_id: str = PathParam(pattern=ID_FINDING)) -> Explanation:
        expl = state.explicacao(finding_id)
        if expl is None:
            raise HTTPException(404, f"Finding {finding_id} não encontrado.")
        return expl

    # ---- grafo ----
    @app.get("/grafo", response_model=GrafoResposta, responses=NAO_ENCONTRADO)
    def grafo(
        centro: str = Query(pattern=ID_NO, examples=["deputado:204554"]),
        profundidade: int = Query(1, ge=0, le=PROFUNDIDADE_MAX),
        relacoes: str | None = Query(None, max_length=200,
                                     description="lista separada por vírgula, ex.: recebeu,doou"),
    ) -> GrafoResposta:
        snap = state.snapshot()
        if centro not in snap.nos_por_id:
            raise HTTPException(404, f"Nó {centro} não encontrado no grafo.")
        nos, arestas, truncado = subgrafo(snap.nodes, snap.edges, centro, profundidade,
                                          relacoes=_relacoes(relacoes), max_nos=max_nos_grafo)
        return GrafoResposta(centro=centro, profundidade=profundidade, nodes=nos, edges=arestas,
                             truncado=truncado)

    @app.get("/grafo/backlinks/{node_id}", response_model=BacklinksResposta,
             responses=NAO_ENCONTRADO)
    def grafo_backlinks(node_id: str = PathParam(pattern=ID_NO)) -> BacklinksResposta:
        snap = state.snapshot()
        if node_id not in snap.nos_por_id:
            raise HTTPException(404, f"Nó {node_id} não encontrado no grafo.")
        links = backlinks(node_id, snap.nodes, snap.edges)
        return BacklinksResposta(node_id=node_id, total=len(links), backlinks=links)

    # ---- perguntar (encadeamento regressivo) ----
    @app.get("/perguntar", response_model=PerguntarResposta, responses=NAO_ENCONTRADO)
    def perguntar(
        deputado: str = Query(pattern=ID_DEPUTADO),
        objetivo: str = Query(pattern=OBJETIVO, examples=["risco_integridade"]),
    ) -> PerguntarResposta:
        snap = state.snapshot()
        if deputado not in snap.deputados:
            raise HTTPException(404, f"Deputado {deputado} não encontrado.")
        regras = state.regras()
        validos = sorted({r.conclui for r in regras if r.tipo == "inferencia" and r.conclui})
        if objetivo not in validos:
            raise HTTPException(422, f"Objetivo desconhecido: {objetivo}. Válidos: {validos}.")
        r = state.prova(snap, objetivo, deputado)
        return PerguntarResposta(
            objetivo=r.objetivo, deputado_id=r.deputado_id, cf=r.cf, nivel=Nivel.from_cf(r.cf),
            regras_usadas=r.regras_usadas, finding_ids=r.finding_ids,
            trilha=[PassoProva(profundidade=p.profundidade, objetivo=p.objetivo, regra=p.regra,
                               cf=p.cf, nota=p.nota,
                               diagnostico=Diagnostico(motivo=p.diagnostico.motivo,
                                                       detalhes=p.diagnostico.detalhes)
                               if p.diagnostico else None) for p in r.trilha])

    # ---- comparar ----
    @app.get("/comparar", response_model=ComparacaoResposta, responses=NAO_ENCONTRADO)
    def comparar(a: str = Query(pattern=ID_DEPUTADO), b: str = Query(pattern=ID_DEPUTADO)
                 ) -> ComparacaoResposta:
        if a == b:
            raise HTTPException(422, "Informe dois deputados diferentes.")
        snap = state.snapshot()
        pa, pb = _perfil(snap, a), _perfil(snap, b)
        cat_a = {c.categoria: c for c in pa.categorias}
        cat_b = {c.categoria: c for c in pb.categorias}
        categorias = [ComparacaoCategoria(categoria=c, a=cat_a.get(c), b=cat_b.get(c))
                      for c in sorted(cat_a.keys() | cat_b.keys())]
        comum = (snap.vizinhos.get(f"deputado:{a}", set()) & snap.vizinhos.get(f"deputado:{b}", set())
                 ) - {f"deputado:{a}", f"deputado:{b}"}
        em_comum: list[GraphNode] = [snap.nos_por_id[i] for i in sorted(comum)][:MAX_EM_COMUM]
        return ComparacaoResposta(
            a=pa, b=pb, categorias=categorias, afinidade_votos=afinidade_votos(snap.facts, a, b),
            em_comum=em_comum, findings_a=snap.findings.get(a, []),
            findings_b=snap.findings.get(b, []))

    return app


app = create_app()
