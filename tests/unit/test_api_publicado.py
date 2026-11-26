"""API sobre o banco público enxuto (ADR-011): mesmas respostas que o caminho antigo, sem snapshot de fatos.

Referência = a API sobre o banco COMPLETO (sem `publicacao_meta`, como em `make dev`). Alvo = a API sobre
o arquivo gerado por `publicar`, onde `Store.load_facts`, `graph.project` e `forward.run` não podem rodar.
"""
from __future__ import annotations

from datetime import date
from itertools import permutations
from urllib.parse import quote

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import create_app
from engine.rules import load_rules
from publicar import publicar
from repo.store import Store
from scripts import seed_demo

OBJETIVOS = sorted({r.conclui for r in load_rules() if r.tipo == "inferencia" and r.conclui})


@pytest.fixture(scope="module")
def bancos(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("api_publicado")
    origem, destino = pasta / "origem.duckdb", pasta / "publico.duckdb"
    seed_demo.gerar(origem)
    publicar(origem, destino, hoje=date.today())
    return origem, destino


def _requisicoes(origem) -> list[tuple[str, dict | None]]:
    """Todas as chamadas que comparamos: lidas do banco COMPLETO para cobrir cada deputado e cada nó."""
    s = Store(origem, read_only=True)
    deps = [f.chave for f in s.facts_by_tipo("deputado")]
    finding_ids = [f.id for f in s.load_findings()]
    s.con.close()
    with TestClient(create_app(origem)) as c:
        nos = [n["id"] for n in c.get("/grafo", params={"centro": f"deputado:{deps[0]}",
                                                         "profundidade": 2}).json()["nodes"]]
    reqs: list[tuple[str, dict | None]] = [
        ("/saude", None), ("/cobertura", None), ("/deputados", None),
        ("/deputados", {"q": "demo", "page_size": 2, "page": 2}),
        ("/deputados", {"uf": "sp"}), ("/deputados", {"partido": "fict-b"}),
        ("/deputados", {"q": "inexistente"}),
        ("/deputados/0", None), ("/deputados/0/findings", None), ("/deputados/0/metricas", None),
        ("/perguntar", {"deputado": "0", "objetivo": OBJETIVOS[0]}),
        ("/perguntar", {"deputado": deps[0], "objetivo": "nao_existe"}),
        ("/comparar", {"a": deps[0], "b": deps[0]}), ("/comparar", {"a": deps[0], "b": "0"}),
        ("/grafo", {"centro": "deputado:0"}), ("/grafo/backlinks/deputado:0", None),
        ("/findings/NAO:EXISTE/explicar", None)]
    for d in deps:
        reqs += [(f"/deputados/{d}", None), (f"/deputados/{d}/findings", None),
                 (f"/deputados/{d}/metricas", None)]
        reqs += [("/perguntar", {"deputado": d, "objetivo": o}) for o in OBJETIVOS]
    reqs += [("/comparar", {"a": a, "b": b}) for a, b in permutations(deps, 2)]
    reqs += [(f"/findings/{quote(i)}/explicar", None) for i in finding_ids]
    for n in nos:
        reqs += [("/grafo", {"centro": n, "profundidade": p}) for p in (0, 1, 2)]
        reqs.append((f"/grafo/backlinks/{quote(n, safe=':')}", None))
    reqs += [("/grafo", {"centro": f"deputado:{deps[0]}", "profundidade": 2, "relacoes": "recebeu,doou"}),
             ("/grafo", {"centro": f"deputado:{deps[0]}", "relacoes": "invalida"})]
    return reqs


def _coletar(banco, reqs):
    with TestClient(create_app(banco)) as c:
        respostas = [c.get(url, params=p) for url, p in reqs]
    return [(r.status_code, r.json()) for r in respostas]


@pytest.fixture(scope="module")
def requisicoes(bancos):
    return _requisicoes(bancos[0])


@pytest.fixture(scope="module")
def referencia(bancos, requisicoes):
    return _coletar(bancos[0], requisicoes)


def test_a_referencia_cobre_muita_coisa_e_inclui_erros(requisicoes, referencia):
    assert len(requisicoes) > 300
    assert {s for s, _ in referencia} >= {200, 404, 422}
    assert any(s == 200 and j.get("cf", 0) > 0 for (s, j), (u, _) in zip(referencia, requisicoes, strict=True)
               if u == "/perguntar")


def test_respostas_iguais_nos_dois_caminhos_sem_carregar_os_fatos(bancos, requisicoes, referencia,
                                                                  monkeypatch):
    import api.state as st
    from engine import forward

    proibidas: list[str] = []

    def vigia(nome, original):
        def chamado(*a, **k):
            proibidas.append(nome)
            return original(*a, **k)
        return chamado

    monkeypatch.setattr(Store, "load_facts", vigia("load_facts", Store.load_facts))
    monkeypatch.setattr(st, "project", vigia("project", st.project))
    monkeypatch.setattr(forward, "run", vigia("forward.run", forward.run))
    obtido = _coletar(bancos[1], requisicoes)
    assert proibidas == []
    diferencas = [(u, p) for (u, p), a, b in zip(requisicoes, referencia, obtido, strict=True) if a != b]
    assert diferencas == []


def test_cobertura_vem_do_banco_completo_e_nao_dos_fatos_mantidos(bancos):
    pub = Store(bancos[1], read_only=True)
    mantidos = sum(pub.contagem_por_tipo().values())
    pub.con.close()
    with TestClient(create_app(bancos[1])) as c:
        declarados = sum(f["n_fatos"] for f in c.get("/cobertura").json()["fontes"])
    assert declarados > mantidos


def test_banco_de_trabalho_continua_no_caminho_antigo(bancos, monkeypatch):
    import api.state as st

    chamadas = []
    original = st.project
    monkeypatch.setattr(st, "project", lambda *a, **k: chamadas.append(1) or original(*a, **k))
    with TestClient(create_app(bancos[0])) as c:
        assert c.get("/deputados").status_code == 200 and c.get("/grafo", params={
            "centro": "deputado:9900001"}).status_code == 200
    assert len(chamadas) == 1


def test_grafo_do_banco_publicado_e_carregado_uma_vez_por_processo(bancos, monkeypatch):
    chamadas = []
    original = Store.load_graph
    monkeypatch.setattr(Store, "load_graph", lambda self: chamadas.append(1) or original(self))
    with TestClient(create_app(bancos[1])) as c:
        for _ in range(3):
            c.get("/grafo", params={"centro": "deputado:9900001"})
            c.get("/deputados")
            c.get("/comparar", params={"a": "9900001", "b": "9900002"})
    assert len(chamadas) == 1


def test_saude_nao_monta_o_grafo_no_banco_publicado(bancos, monkeypatch):
    carregou = []
    original = Store.load_graph
    monkeypatch.setattr(Store, "load_graph", lambda self: carregou.append(1) or original(self))
    with TestClient(create_app(bancos[1])) as c:
        assert not carregou
        assert c.get("/saude").json() == {
            "status": "ok", "contract_version": "0.2.0", "n_deputados": 6,
            "n_findings": c.get("/saude").json()["n_findings"], "banco": "ok", "pseudonimizado": True}


def _fatos_simbolicos():
    from contracts import Fact

    def f(tipo, chave, **at):
        return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                    url=f"https://exemplo/{tipo}/{chave}")
    fs = [f("deputado", "1", nome="Ana", partido="ABC", uf="MG")]
    for i in range(6):  # 6 votações nominais e 6 simbólicas, todas com orientação Sim e voto Sim
        for tipo, nominal in (("n", True), ("s", False)):
            fs.append(f("votacao", f"{tipo}{i}", nominal=nominal, orientacao_governo="Sim"))
            fs.append(f("voto", f"{tipo}{i}:1", votacao_id=f"{tipo}{i}", deputado_id="1", voto="Sim"))
    return fs


def test_diagnostico_aplica_os_guardrails_como_o_motor_e_ignora_voto_de_votacao_simbolica(tmp_path):
    from engine import forward
    from engine.factbase import FactBase

    origem, destino = tmp_path / "o.duckdb", tmp_path / "p.duckdb"
    s = Store(origem)
    fatos = _fatos_simbolicos()
    s.upsert_facts(fatos)
    res = forward.run(FactBase(fatos), load_rules())
    s.save_findings(res.findings, res.explanations)
    s.con.close()
    publicar(origem, destino)
    params = {"deputado": "1", "objetivo": "alinhado_governo"}
    respostas = []
    for banco in (origem, destino):
        with TestClient(create_app(banco)) as c:
            respostas.append(c.get("/perguntar", params=params).json())
    assert respostas[0] == respostas[1]
    passo = next(p for p in respostas[1]["trilha"] if p["regra"] == "R01")
    assert passo["diagnostico"]["motivo"] == "dados_insuficientes"
    assert passo["diagnostico"]["detalhes"]["n_votos_validos"] == 6  # os 6 simbólicos ficaram de fora
