"""Projeção pura de fatos + findings em nós e arestas (contracts.GraphNode/GraphEdge).

Sem banco, sem rede, sem estado: mesma entrada → mesma saída (ordem determinística).

Direção das arestas (origem → destino):
  filiado_a       deputado → partido
  recebeu         empresa  → deputado   (empresa recebeu CEAP do deputado; peso = R$ somado)
  doou            doador   → deputado   (via candidatura.deputado_id; peso = R$ somado)
  autor_de        deputado → proposicao (autor e coautor)
  relator_de      deputado → proposicao
  enviou_emenda   deputado → municipio  (peso = R$ empenhado somado)
  socio_de        pessoa   → empresa    (ver `project` sobre ids de pessoa)
  votou_com       deputado ↔ deputado   (simétrica; peso = % de votos iguais; só top-k)
"Sancionada" não é aresta: é marca no nó da empresa (atributos["sancionada"]).

Custo: votou_com usa máscaras de bits por votação (popcount), O(D² · V/64) e guarda só as top-k
afinidades por deputado — nunca O(D²) arestas.
"""
from __future__ import annotations

import hashlib
import heapq
import os
import re
import unicodedata
from collections import Counter, defaultdict, deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel

from contracts import Fact, Finding, GraphEdge, GraphNode, Nivel

RELACOES: tuple[str, ...] = (
    "filiado_a", "doou", "recebeu", "enviou_emenda", "socio_de", "votou_com", "relator_de",
    "autor_de",
)  # também é a ordem de desempate das vagas quando o limite de nós corta o subgrafo
SIMETRICAS: frozenset[str] = frozenset({"votou_com"})

VOTOS_VALIDOS = {"sim": "Sim", "nao": "Não", "abstencao": "Abstenção", "obstrucao": "Obstrução"}
CF_NOME_MASCARADO = 0.4  # igual à penalidade do R06: CPF mascarado ⇒ identidade não confirmada
VOTACOES_PARA_CF_PLENO = 30
MAX_EVIDENCIAS = 20
ENV_SAL_ID = "RAIO_X_ID_SALT"  # sal secreto do hash dos ids de pessoa (o mesmo da pseudonimização)
ROTULO_DOADOR_ANONIMO = "Doador(a) pessoa física"


class SalAusenteError(RuntimeError):
    """`RAIO_X_ID_SALT` ausente ou vazio. Não há sal padrão: um sal público tornaria os ids de
    pessoa reversíveis por força bruta do CPF."""


def _sal_ausente() -> SalAusenteError:
    return SalAusenteError(
        f"A variável de ambiente {ENV_SAL_ID} não está definida. Ela é o sal secreto dos ids de "
        "pessoa do grafo (sem ele, os ids poderiam ser revertidos por força bruta). Defina-a "
        f"com uma string longa e fixa, fora do repositório: `export {ENV_SAL_ID}=<segredo>` no "
        "terminal local, ou em Settings > Environment Variables no projeto da API na Vercel. "
        "Use sempre o mesmo valor da base pseudonimizada (ver docs/adr/ADR-006).")


def sal_do_ambiente(env: Mapping[str, str] | None = None) -> str:
    sal = (os.environ if env is None else env).get(ENV_SAL_ID, "").strip()
    if not sal:
        raise _sal_ausente()
    return sal


class Afinidade(BaseModel):
    deputado_a: str
    deputado_b: str
    n_votacoes_comuns: int
    n_iguais: int
    afinidade: float  # n_iguais / n_votacoes_comuns
    cf: float  # min(1, n_comuns / 30)


class Backlink(BaseModel):
    no: GraphNode  # quem aponta para o nó consultado
    aresta: GraphEdge


# ---------------------------------------------------------------------------------- utilidades
def normaliza_nome(nome: str | None) -> str:
    """Mesma normalização do R06 (sem acento, maiúsculo, espaços colapsados)."""
    s = unicodedata.normalize("NFKD", nome or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().upper()


def _num(x: Any) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _digits(x: Any) -> str:
    return re.sub(r"\D", "", str(x or ""))


PREFIXO_HMAC = "hmac:"  # CPF pseudonimizado na ingestão (ingest/pseudonimizar.py)


def _pseudonimo(x: Any) -> bool:
    return str(x or "").startswith(PREFIXO_HMAC)


def _cnpj(x: Any) -> str | None:
    if _pseudonimo(x):
        return None
    d = _digits(x)
    return d if len(d) == 14 and "*" not in str(x) else None


def _cpf_integro(x: Any) -> str | None:
    """Identificador estável de um CPF íntegro: 11 dígitos sem máscara, ou o hash `hmac:...`
    (nunca extrai dígitos do hex). CPF mascarado/ausente não identifica ninguém."""
    if _pseudonimo(x):
        return str(x)
    d = _digits(x)
    return d if len(d) == 11 and "*" not in str(x) else None


def _h(valor: str, sal: str, n: int = 12) -> str:
    return hashlib.sha256(f"{sal}:{valor}".encode()).hexdigest()[:n]


def _data(x: Any) -> date | None:
    try:
        return date.fromisoformat(str(x)[:10])
    except (TypeError, ValueError):
        return None


def _evidencias(itens: Iterable[tuple[float, str]]) -> list[str]:
    """Até MAX_EVIDENCIAS ids, priorizando os de maior valor; saída ordenada."""
    top = heapq.nlargest(MAX_EVIDENCIAS, itens, key=lambda t: (abs(t[0]), t[1]))
    return sorted(i for _, i in top)


class _Acum:
    """Acumula peso e evidências de uma aresta agregada."""

    def __init__(self) -> None:
        self.peso = 0.0
        self.itens: list[tuple[float, str]] = []

    def add(self, valor: float, evid: str) -> None:
        self.peso += valor
        self.itens.append((valor, evid))


# ---------------------------------------------------------------------------------- votou_com
def _matriz_votos(facts: list[Fact]) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """(máscara de votações em que votou, máscara por valor de voto) por deputado.

    Só votação NOMINAL conta (voto em votação simbólica não é voto individual) e só Sim/Não/
    Abstenção/Obstrução ('Artigo 17' é o presidente da sessão)."""
    nominais = {f.chave for f in facts if f.tipo == "votacao" and f.atributos.get("nominal") is True}
    unicos: dict[tuple[str, str], str] = {}
    for f in facts:
        if f.tipo != "voto":
            continue
        vot, dep = str(f.atributos.get("votacao_id")), str(f.atributos.get("deputado_id"))
        valor = VOTOS_VALIDOS.get(normaliza_nome(f.atributos.get("voto")).lower())
        if vot in nominais and valor:
            unicos[(vot, dep)] = valor
    idx = {v: i for i, v in enumerate(sorted({v for v, _ in unicos}))}
    votou: dict[str, int] = defaultdict(int)
    por_valor: dict[str, dict[str, int]] = {v: defaultdict(int) for v in VOTOS_VALIDOS.values()}
    for (vot, dep), valor in unicos.items():
        bit = 1 << idx[vot]
        votou[dep] |= bit
        por_valor[valor][dep] |= bit
    return votou, por_valor


def _iguais(a: str, b: str, por_valor: dict[str, dict[str, int]]) -> int:
    return sum((m.get(a, 0) & m.get(b, 0)).bit_count() for m in por_valor.values())


def afinidade_votos(facts: list[Fact], a: str, b: str) -> Afinidade | None:
    """% de votos iguais entre dois deputados em votações nominais comuns (None se não há)."""
    votou, por_valor = _matriz_votos(facts)
    comuns = (votou.get(a, 0) & votou.get(b, 0)).bit_count()
    if comuns == 0:
        return None
    iguais = _iguais(a, b, por_valor)
    return Afinidade(deputado_a=a, deputado_b=b, n_votacoes_comuns=comuns, n_iguais=iguais,
                     afinidade=round(iguais / comuns, 4),
                     cf=min(1.0, comuns / VOTACOES_PARA_CF_PLENO))


def _arestas_votou_com(facts: list[Fact], deputados: set[str], k: int,
                       min_comuns: int) -> list[GraphEdge]:
    votou, por_valor = _matriz_votos(facts)
    deps = sorted(d for d in votou if d in deputados)
    melhores: dict[str, list[tuple[float, int, str]]] = defaultdict(list)
    for i, a in enumerate(deps):
        va = votou[a]
        for b in deps[i + 1:]:
            comuns = (va & votou[b]).bit_count()
            if comuns < min_comuns:
                continue
            afin = _iguais(a, b, por_valor) / comuns
            melhores[a].append((afin, comuns, b))
            melhores[b].append((afin, comuns, a))
    pares: dict[tuple[str, str], tuple[float, int]] = {}
    for dep, cands in melhores.items():
        for afin, comuns, outro in heapq.nsmallest(k, cands, key=lambda t: (-t[0], -t[1], t[2])):
            pares[tuple(sorted((dep, outro)))] = (afin, comuns)
    return [GraphEdge(origem=f"deputado:{a}", destino=f"deputado:{b}", relacao="votou_com",
                      peso=round(afin, 4), cf=min(1.0, comuns / VOTACOES_PARA_CF_PLENO))
            for (a, b), (afin, comuns) in pares.items()]


# ---------------------------------------------------------------------------------- projeção
def project(facts: list[Fact], findings: list[Finding], *, votou_com_k: int = 5,
            min_votacoes_comuns: int = 5, hoje: date | None = None, sal_id: str | None = None
            ) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Grafo COMPLETO. Para um recorte navegável use `subgrafo`/`build_graph(centro=...)`.

    Nó `pessoa` (LGPD): só CPF íntegro identifica (id = hash salgado do CPF; dois fatos com o
    mesmo CPF íntegro viram um nó, rótulo = nome). CPF mascarado/ausente: um nó por doação/sócio,
    sem nome em id, rótulo ou atributos — nunca funde homônimos."""
    hoje = hoje or date.today()
    if sal_id is None:
        sal_id = sal_do_ambiente()  # sem valor padrão (falha fechado)
    if not sal_id.strip():  # sal vazio passado de forma explícita também é erro
        raise _sal_ausente()
    facts = sorted(facts, key=lambda f: (f.tipo, f.chave))  # determinismo
    por_tipo: dict[str, list[Fact]] = defaultdict(list)
    for f in facts:
        por_tipo[f.tipo].append(f)

    nodes: dict[str, GraphNode] = {}
    acum: dict[tuple[str, str, str], _Acum] = {}
    cf_aresta: dict[tuple[str, str, str], float] = {}

    def no(id_: str, tipo: str, rotulo: str, **atributos: Any) -> None:
        if id_ not in nodes:
            nodes[id_] = GraphNode(id=id_, tipo=tipo, rotulo=rotulo, atributos=atributos)

    def liga(origem: str, destino: str, relacao: str, valor: float, evid: str,
             cf: float = 1.0) -> None:
        a = acum.setdefault((origem, destino, relacao), _Acum())
        a.add(valor, evid)
        cf_aresta[(origem, destino, relacao)] = cf

    # deputados e partidos
    deputados: set[str] = set()
    for f in por_tipo["deputado"]:
        at = f.atributos
        deputados.add(f.chave)
        no(f"deputado:{f.chave}", "deputado", at.get("nome") or f"Deputado {f.chave}",
           partido=at.get("partido"), uf=at.get("uf"), foto=at.get("foto"), n_findings=0)
        if at.get("partido"):
            sigla = str(at["partido"])
            no(f"partido:{sigla}", "partido", sigla, sigla=sigla)
            liga(f"deputado:{f.chave}", f"partido:{sigla}", "filiado_a", 1.0, f"deputado:{f.chave}")
    siglas = {n.rotulo for n in nodes.values() if n.tipo == "partido"}

    # CEAP → empresa
    razao = {f.chave: f.atributos.get("razao_social") for f in por_tipo["empresa"]}
    nomes_fornecedor: dict[str, str] = {}
    for f in por_tipo["despesa_ceap"]:
        dep, cnpj = str(f.atributos.get("deputado_id")), _cnpj(f.atributos.get("cnpj"))
        if dep not in deputados or not cnpj:
            continue
        nomes_fornecedor.setdefault(cnpj, f.atributos.get("fornecedor") or "")
        no(f"empresa:{cnpj}", "empresa", razao.get(cnpj) or nomes_fornecedor[cnpj] or cnpj,
           cnpj=cnpj, sancionada=False, findings=[])
        liga(f"empresa:{cnpj}", f"deputado:{dep}", "recebeu", _num(f.atributos.get("valor")),
             f"despesa_ceap:{f.chave}")

    # doações (TSE) → empresa | pessoa | partido
    sq_dep = {c.chave: str(c.atributos["deputado_id"]) for c in por_tipo["candidatura"]
              if c.atributos.get("deputado_id")}
    for f in por_tipo["doacao"]:
        at = f.atributos
        dep = sq_dep.get(str(at.get("sq_candidato")))
        if dep not in deputados:
            continue
        tipo, nome = at.get("tipo_doador"), at.get("doador_nome") or ""
        origem: str | None = None
        if tipo == "PJ" and _cnpj(at.get("doador_cpf_cnpj")):
            cnpj = _cnpj(at["doador_cpf_cnpj"])
            origem = f"empresa:{cnpj}"
            no(origem, "empresa", razao.get(cnpj) or nome or cnpj, cnpj=cnpj, sancionada=False,
               findings=[])
        elif tipo == "PF":
            cpf = _cpf_integro(at.get("doador_cpf_cnpj"))
            if cpf and nome.strip():
                origem = f"pessoa:cpf:{_h(cpf, sal_id, 16)}"
                no(origem, "pessoa", nome)
            else:
                origem = f"pessoa:doador:{_h(f.chave, sal_id)}"
                no(origem, "pessoa", ROTULO_DOADOR_ANONIMO)
        elif tipo == "partido" and normaliza_nome(nome) in siglas:
            origem = f"partido:{normaliza_nome(nome)}"
        if origem:  # 'proprio' e doador não identificável ficam de fora
            liga(origem, f"deputado:{dep}", "doou", _num(at.get("valor")), f"doacao:{f.chave}")

    # sócios (RFB) — só de empresas que já estão no grafo
    for f in por_tipo["socio"]:
        at = f.atributos
        cnpj, nome = _cnpj(at.get("cnpj")), at.get("nome") or ""
        if not cnpj or f"empresa:{cnpj}" not in nodes:
            continue
        doc = str(at.get("cpf_cnpj") or "")
        if not _pseudonimo(doc) and len(_digits(doc)) == 14:
            continue  # sócio pessoa jurídica: fora de escopo (YAGNI)
        cpf = _cpf_integro(doc)
        if cpf and nome.strip():
            pid = f"pessoa:cpf:{_h(cpf, sal_id, 16)}"
            no(pid, "pessoa", nome)
        else:
            pid = f"pessoa:socio:{cnpj}:{_h(f.chave, sal_id)}"
            no(pid, "pessoa", f"Sócio(a) de {nodes[f'empresa:{cnpj}'].rotulo}")
        liga(pid, f"empresa:{cnpj}", "socio_de", 1.0, f"socio:{f.chave}",
             1.0 if cpf else CF_NOME_MASCARADO)

    # sanções → marca no nó da empresa
    for f in por_tipo["sancao"]:
        n = nodes.get(f"empresa:{_digits(f.atributos.get('cnpj'))}")
        if not n:
            continue
        ini, fim = _data(f.atributos.get("inicio")), _data(f.atributos.get("fim"))
        vigente = (ini is None or ini <= hoje) and (fim is None or fim >= hoje)
        n.atributos.setdefault("sancoes", []).append({
            "cadastro": f.atributos.get("cadastro"), "inicio": f.atributos.get("inicio"),
            "fim": f.atributos.get("fim"), "orgao": f.atributos.get("orgao"),
            "id_oficial": f.id_oficial, "vigente": vigente})
        n.atributos["sancionada"] = True
        n.atributos["sancao_vigente"] = bool(n.atributos.get("sancao_vigente")) or vigente

    # produção legislativa
    for f in por_tipo["proposicao"]:
        at = f.atributos
        rot = (f"{at.get('sigla_tipo')} {at.get('numero')}/{at.get('ano')}"
               if at.get("sigla_tipo") else f"Proposição {f.chave}")
        no(f"proposicao:{f.chave}", "proposicao", rot, sigla_tipo=at.get("sigla_tipo"),
           numero=at.get("numero"), ano=at.get("ano"), ementa=at.get("ementa"), data=at.get("data"))
    for f in por_tipo["autoria"]:
        at = f.atributos
        dep, prop = str(at.get("deputado_id")), str(at.get("proposicao_id"))
        rel = {"autor": "autor_de", "coautor": "autor_de", "relator": "relator_de"}.get(
            str(at.get("papel")))
        if dep not in deputados or not rel:
            continue
        no(f"proposicao:{prop}", "proposicao", f"Proposição {prop}")
        liga(f"deputado:{dep}", f"proposicao:{prop}", rel, 1.0, f"autoria:{f.chave}")

    # emendas → município (a CGU só traz o código IBGE; o nome vem da votação por município do TSE)
    nomes_municipio = {str(f.atributos.get("municipio_ibge")): f.atributos["municipio_nome"]
                       for f in por_tipo["votos_municipio"] if f.atributos.get("municipio_nome")}
    for f in por_tipo["emenda"]:
        at = f.atributos
        dep, ibge = str(at.get("deputado_id")), str(at.get("municipio_ibge") or "")
        if dep not in deputados or not ibge:
            continue
        nome = at.get("municipio_nome") or nomes_municipio.get(ibge) or f"Município {ibge}"
        no(f"municipio:{ibge}", "municipio", nome, municipio_ibge=ibge)
        liga(f"deputado:{dep}", f"municipio:{ibge}", "enviou_emenda",
             _num(at.get("valor_empenhado")), f"emenda:{f.chave}")

    # findings → anotações nos nós
    por_dep: dict[str, list[Finding]] = defaultdict(list)
    for fd in findings:
        por_dep[fd.deputado_id].append(fd)
        cnpjs = fd.valores.get("cnpjs") or ([fd.valores["cnpj"]] if fd.valores.get("cnpj") else [])
        for c in cnpjs:
            emp = nodes.get(f"empresa:{_digits(c)}")
            if emp and fd.id not in emp.atributos["findings"]:
                emp.atributos["findings"].append(fd.id)
    for dep, fds in por_dep.items():
        n = nodes.get(f"deputado:{dep}")
        if n:
            cf_max = max(fd.cf for fd in fds)
            n.atributos.update(n_findings=len(fds), cf_max=cf_max,
                               nivel_max=Nivel.from_cf(cf_max).value)
    for n in nodes.values():
        if n.tipo == "empresa":
            n.atributos["findings"].sort()

    edges = [GraphEdge(origem=o, destino=d, relacao=r, peso=round(a.peso, 2),
                       cf=cf_aresta[(o, d, r)], evidencia_ids=_evidencias(a.itens))
             for (o, d, r), a in acum.items()]
    edges += _arestas_votou_com(facts, deputados, votou_com_k, min_votacoes_comuns)
    edges.sort(key=lambda e: (e.relacao, e.origem, e.destino))
    return sorted(nodes.values(), key=lambda n: n.id), edges


# ---------------------------------------------------------------------------------- recortes
def _valida_relacoes(relacoes: Iterable[str] | None) -> frozenset[str] | None:
    if relacoes is None:
        return None
    rels = frozenset(relacoes)
    desconhecidas = rels - set(RELACOES)
    if desconhecidas:
        raise ValueError(f"relações desconhecidas: {sorted(desconhecidas)}; válidas: {RELACOES}")
    return rels


@dataclass(frozen=True)
class Oculto:
    """Quantos nós de um tipo ficaram fora do recorte e por qual relação entrariam nele."""

    tipo: str
    relacao: str | None
    quantidade: int


@dataclass
class Recorte:
    """Vizinhança de um nó, já cortada em `max_nos`, com o resumo do que ficou de fora."""

    nos: list[GraphNode]
    arestas: list[GraphEdge]
    truncado: bool
    total_nos: int  # tamanho da vizinhança completa, na profundidade pedida
    total_arestas: int
    ocultos: list[Oculto] = field(default_factory=list)


RESERVA_PROXIMO_SALTO = 0.25  # fatia de `max_nos` guardada para o salto seguinte


def _reparte(grupos: dict[str, list[str]], limite: int, prio: dict[str, int]) -> list[str]:
    """Divide `limite` vagas entre os grupos (um por relação) em partes iguais; o que um grupo
    pequeno não usa passa para os maiores. Dentro do grupo vale a ordem recebida (maior valor)."""
    cotas = dict.fromkeys(grupos, 0)
    abertos = sorted(grupos, key=lambda r: prio.get(r, len(prio)))
    restante = limite
    while restante > 0 and abertos:
        parte = max(restante // len(abertos), 1)
        proximos = []
        for r in abertos:
            if restante <= 0:
                break
            dar = min(parte, len(grupos[r]) - cotas[r], restante)
            cotas[r] += dar
            restante -= dar
            if cotas[r] < len(grupos[r]):
                proximos.append(r)
        abertos = proximos
    return [i for r, itens in grupos.items() for i in itens[:cotas[r]]]


def recorte(nodes: list[GraphNode], edges: list[GraphEdge], centro: str, profundidade: int = 1,
            *, relacoes: Iterable[str] | None = None, max_nos: int | None = None) -> Recorte:
    """Vizinhança de `centro` até `profundidade` saltos (arestas tratadas como não-direcionadas).

    Com `max_nos`, o corte é justo: salto a salto, as vagas se dividem em partes iguais entre as
    relações (nenhuma monopoliza) e, dentro de cada uma, ficam os nós de maior valor (peso da
    aresta: R$; em `votou_com` é a %). Parte das vagas fica guardada para o salto seguinte, para
    "2 saltos" não ser uma cópia de "1 salto". O resultado diz o tamanho completo e o que sumiu."""
    if profundidade < 0:
        raise ValueError("profundidade deve ser >= 0")
    rels = _valida_relacoes(relacoes)
    por_id = {n.id: n for n in nodes}
    if centro not in por_id:
        raise KeyError(centro)
    usadas = [e for e in edges if rels is None or e.relacao in rels]
    prio = {r: i for i, r in enumerate(RELACOES)}
    adj: dict[str, list[tuple[str, GraphEdge]]] = defaultdict(list)
    for e in usadas:
        adj[e.origem].append((e.destino, e))
        adj[e.destino].append((e.origem, e))

    # vizinhança completa: salto de cada nó e a relação mais prioritária que o trouxe
    salto = {centro: 0}
    via: dict[str, str] = {}
    fila: deque[str] = deque([centro])
    while fila:
        atual = fila.popleft()
        if salto[atual] >= profundidade:
            continue
        for viz, e in adj[atual]:
            if viz not in salto:
                salto[viz] = salto[atual] + 1
                fila.append(viz)
            if salto[viz] == salto[atual] + 1 and prio[e.relacao] < prio.get(via.get(viz), 99):
                via[viz] = e.relacao
    total_nos = len(salto)
    total_arestas = sum(1 for e in usadas if e.origem in salto and e.destino in salto)

    escolhidos = {centro: 0}  # id -> salto em que entrou

    def candidatos(fontes: list[str]) -> dict[str, list[str]]:
        """Nós de fora ligados às `fontes`, agrupados pela relação e ordenados por valor."""
        achados: dict[str, tuple[int, float]] = {}
        for u in fontes:
            for viz, e in adj[u]:
                if viz in escolhidos:
                    continue
                antigo = achados.get(viz)
                chave = (prio[e.relacao], -abs(e.peso))
                if antigo is None or chave < antigo:
                    achados[viz] = chave
        grupos: dict[str, list[tuple[float, str]]] = defaultdict(list)
        rotulo = {i: r for r, i in prio.items()}
        for viz, (p, v) in achados.items():
            grupos[rotulo[p]].append((v, viz))
        return {r: [i for _, i in sorted(itens)] for r, itens in grupos.items()}

    if max_nos is None or total_nos <= max_nos:
        escolhidos = dict.fromkeys(salto, 0)
    else:
        vagas = max(max_nos, 1) - 1
        for d in range(1, profundidade + 1):
            if vagas <= 0:
                break
            grupos = candidatos([i for i, s in escolhidos.items() if s == d - 1])
            n_cand = sum(len(g) for g in grupos.values())
            guarda = int(max_nos * RESERVA_PROXIMO_SALTO) if d < profundidade else 0
            limite = max(vagas - guarda, 1) if any(s > d for s in salto.values()) else vagas
            tomados = ([i for itens in grupos.values() for i in itens] if n_cand <= limite
                       else _reparte(grupos, limite, prio))
            for i in tomados:
                escolhidos[i] = d
            vagas -= len(tomados)
        while vagas > 0:  # sobra de vagas: completa com o que ficou de fora dos saltos anteriores
            fontes = [i for i, s in escolhidos.items() if s < profundidade]
            grupos = candidatos(fontes)
            if not grupos:
                break
            tomados = _reparte(grupos, vagas, prio)
            niveis = {}
            for u in fontes:
                for viz, _ in adj[u]:
                    niveis[viz] = min(niveis.get(viz, 99), escolhidos[u] + 1)
            for i in tomados:
                escolhidos[i] = niveis[i]
            vagas -= len(tomados)

    ocultos = Counter((por_id[i].tipo, via.get(i)) for i in salto if i not in escolhidos)
    return Recorte(
        nos=sorted((por_id[i] for i in escolhidos), key=lambda n: n.id),
        arestas=[e for e in usadas if e.origem in escolhidos and e.destino in escolhidos],
        truncado=len(escolhidos) < total_nos, total_nos=total_nos, total_arestas=total_arestas,
        ocultos=[Oculto(t, r, q) for (t, r), q in
                 sorted(ocultos.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1] or ""))])


def subgrafo(nodes: list[GraphNode], edges: list[GraphEdge], centro: str, profundidade: int = 1,
             *, relacoes: Iterable[str] | None = None, max_nos: int | None = None
             ) -> tuple[list[GraphNode], list[GraphEdge], bool]:
    """Como `recorte`, mas devolve só (nós, arestas, truncado)."""
    r = recorte(nodes, edges, centro, profundidade, relacoes=relacoes, max_nos=max_nos)
    return r.nos, r.arestas, r.truncado


def build_graph(facts: list[Fact], findings: list[Finding], centro: str | None = None,
                profundidade: int = 1, *, relacoes: Iterable[str] | None = None,
                max_nos: int | None = None, votou_com_k: int = 5, min_votacoes_comuns: int = 5,
                hoje: date | None = None, sal_id: str | None = None
                ) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Projeta o grafo; com `centro` ("deputado:ID") devolve só a vizinhança até `profundidade`."""
    nodes, edges = project(facts, findings, votou_com_k=votou_com_k,
                           min_votacoes_comuns=min_votacoes_comuns, hoje=hoje, sal_id=sal_id)
    if centro is None:
        rels = _valida_relacoes(relacoes)
        return nodes, [e for e in edges if rels is None or e.relacao in rels]
    sub_nos, sub_arestas, _ = subgrafo(nodes, edges, centro, profundidade, relacoes=relacoes,
                                       max_nos=max_nos)
    return sub_nos, sub_arestas


def backlinks(node_id: str, nodes: list[GraphNode], edges: list[GraphEdge]) -> list[Backlink]:
    """Todas as ligações do nó (estilo Obsidian): as que chegam e as que saem dele.

    `no` é sempre a outra ponta; o sentido está em `aresta.origem`/`aresta.destino`. Vêm primeiro as
    que chegam (e as simétricas), depois as que saem; dentro de cada relação, o maior peso primeiro
    (a tela mostra só o começo da lista). Sem as que saem, doadores, sócios e a maioria das empresas
    apareceriam sem ligação nenhuma."""
    por_id = {n.id: n for n in nodes}
    if node_id not in por_id:
        raise KeyError(node_id)
    out: list[Backlink] = []
    for e in edges:
        if e.destino == node_id:
            out.append(Backlink(no=por_id[e.origem], aresta=e))
        elif e.origem == node_id:
            out.append(Backlink(no=por_id[e.destino], aresta=e))

    def ordem(b: Backlink) -> tuple[bool, str, float, str]:
        sai = b.aresta.destino != node_id and b.aresta.relacao not in SIMETRICAS
        return sai, b.aresta.relacao, -b.aresta.peso, b.no.id

    return sorted(out, key=ordem)
