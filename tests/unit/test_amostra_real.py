"""Casos reais da amostra de 20 deputados de MG (só roda se o banco de amostra existir).

O banco não é versionado (CPF de terceiros). Aponte `RAIO_X_DB_AMOSTRA` para ele ou gere com
`make sample` (padrão: data/sample/raio_x_sample.duckdb).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import create_app

RAIZ = Path(__file__).resolve().parents[2]
AMOSTRA = Path(os.environ.get("RAIO_X_DB_AMOSTRA") or RAIZ / "data" / "sample" / "raio_x_sample.duckdb")

pytestmark = pytest.mark.skipif(not AMOSTRA.exists(), reason="banco de amostra não gerado")


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(AMOSTRA)) as c:
        yield c


def diagnostico_r01(client, dep):
    r = client.get("/perguntar", params={"deputado": dep, "objetivo": "alinhado_governo"})
    assert r.status_code == 200, r.text
    corpo = r.json()
    passo = next(p for p in corpo["trilha"] if p["regra"] == "R01")
    return corpo, passo["diagnostico"]


@pytest.mark.parametrize("dep,n", [("74581", 0), ("77003", 0), ("74646", 9), ("98057", 9),
                                   ("160510", 6)])
def test_poucos_votos_validos_e_dados_insuficientes(client, dep, n):
    corpo, diag = diagnostico_r01(client, dep)
    assert corpo["cf"] == 0.0
    assert diag["motivo"] == "dados_insuficientes"
    assert diag["detalhes"]["n_votos_validos"] == n and diag["detalhes"]["minimo_votos"] == 10


def test_17_votos_e_taxa_baixa_e_abaixo_do_limiar(client):
    corpo, diag = diagnostico_r01(client, "74585")
    assert corpo["cf"] == 0.0 and diag["motivo"] == "abaixo_do_limiar"
    assert diag["detalhes"]["n_votos_validos"] == 17
    assert diag["detalhes"]["taxa"] == pytest.approx(0.529, abs=0.001)
    assert diag["detalhes"]["limiar"] == 0.7


def test_deputados_que_disparam_a_r01_nao_tem_diagnostico(client):
    deps = [d["id"] for d in client.get("/deputados", params={"page_size": 100}).json()["items"]]
    disparam = []
    for dep in deps:
        corpo, diag = diagnostico_r01(client, dep)
        if corpo["cf"] > 0:
            assert diag is None
            disparam.append(dep)
    assert len(disparam) == 14


# --------------------------------------------------------------------------- cobertura e métricas
def test_cobertura_da_amostra(client):
    c = client.get("/cobertura").json()
    assert c["janela_votos"] == {"inicio": "2025-02-04", "fim": "2025-03-27", "n_votacoes": 145,
                                 "n_votacoes_nominais": 24, "n_votacoes_com_orientacao": 22}
    assert c["n_deputados"] == 20 and c["n_findings"] == 40
    por_fonte = {f["fonte"]: f for f in c["fontes"]}
    assert por_fonte["camara_ceap"]["n_fatos"] == 10950
    assert por_fonte["camara_api_v2"]["tipos"] == [
        "autoria", "deputado", "proposicao", "votacao", "voto"]


def test_metricas_da_amostra_batem_com_o_diagnostico(client):
    for dep, n_validos in (("74581", 0), ("74646", 9), ("74585", 17)):
        m = client.get(f"/deputados/{dep}/metricas").json()
        assert m["n_votos_validos"] == n_validos and m["n_votos"] >= n_validos
        _, diag = diagnostico_r01(client, dep)
        assert diag["detalhes"]["n_votos_validos"] == m["n_votos_validos"]


def test_n_votos_validos_e_igual_a_n_votacoes_da_r01_quando_ela_dispara(client):
    deps = [d["id"] for d in client.get("/deputados", params={"page_size": 100}).json()["items"]]
    conferidos = 0
    for dep in deps:
        m = client.get(f"/deputados/{dep}/metricas").json()
        r01 = next(x for x in m["metricas_por_regra"] if x["regra"] == "R01")
        if r01["finding_id"]:
            assert r01["valores"]["n_votacoes"] == m["n_votos_validos"]
            conferidos += 1
    assert conferidos == 14
