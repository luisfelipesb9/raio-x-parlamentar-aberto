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
