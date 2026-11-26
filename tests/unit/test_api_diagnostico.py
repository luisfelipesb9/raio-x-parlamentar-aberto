"""/perguntar devolve o diagnóstico de cada passo inconclusivo (ADR-007)."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import create_app
from tests.unit.test_api import store  # noqa: F401  (fixture: base sintética com motor real)


@pytest.fixture
def client(store):  # noqa: F811
    with TestClient(create_app(store=store)) as c:
        yield c


def passo_r01(client, dep):
    r = client.get("/perguntar", params={"deputado": dep, "objetivo": "alinhado_governo"})
    assert r.status_code == 200
    corpo = r.json()
    return corpo, next(p for p in corpo["trilha"] if p["regra"] == "R01")


def test_deputado_sem_votos_recebe_dados_insuficientes(client):
    corpo, passo = passo_r01(client, "3")
    assert corpo["cf"] == 0.0 and corpo["nivel"] == "inconclusivo"
    assert passo["nota"] == "condições não satisfeitas"  # texto legado intacto
    assert passo["diagnostico"] == {"motivo": "dados_insuficientes",
                                    "detalhes": {"n_votos_validos": 0, "minimo_votos": 10}}


def test_taxa_baixa_recebe_abaixo_do_limiar(client):
    _, passo = passo_r01(client, "2")  # 6 de 12 votos iguais ao governo
    assert passo["diagnostico"] == {"motivo": "abaixo_do_limiar",
                                    "detalhes": {"n_votos_validos": 12, "minimo_votos": 10,
                                                 "taxa": 0.5, "limiar": 0.7}}


def test_quando_a_regra_dispara_o_diagnostico_e_nulo(client):
    corpo, passo = passo_r01(client, "1")
    assert corpo["cf"] > 0 and passo["diagnostico"] is None


def test_objetivo_composto_sem_prova_traz_sem_regra_aplicavel(client):
    r = client.get("/perguntar", params={"deputado": "4", "objetivo": "risco_integridade"})
    passos = r.json()["trilha"]
    assert passos and {p["diagnostico"]["motivo"] for p in passos} == {"sem_regra_aplicavel"}
