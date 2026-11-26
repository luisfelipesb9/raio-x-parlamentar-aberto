"""Consultas de cobertura/métricas no Store e os endpoints /cobertura e /deputados/{id}/metricas.

Lógica nova do contrato v0.2.0 (ADR-007): JanelaVotos, FonteCobertura, CoberturaResposta,
MetricaRegra e MetricasDeputadoResposta passam a ser preenchidos com dados reais da base.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import create_app
from contracts import CONTRACT_VERSION, Fact
from engine import forward
from engine.factbase import FactBase
from engine.predicates.core import _votos_validos
from engine.rules import load_rules
from repo.store import Store

T1 = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
T2 = datetime(2026, 11, 21, 12, 30, tzinfo=UTC)
T3 = datetime(2026, 11, 22, 8, 0, tzinfo=UTC)


def F(tipo, chave, fonte="camara_api_v2", coletado_em=T1, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte=fonte, id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}", coletado_em=coletado_em)


def fatos_base() -> list[Fact]:
    fs = [F("deputado", "1", nome="Ana"), F("deputado", "2", nome="Beto"),
          F("deputado", "3", nome="Sem Voto")]
    # 12 votações nominais com orientação Sim (datas de fev/2025), dep 1 sempre Sim
    for i in range(12):
        fs.append(F("votacao", f"v{i}", data=f"2025-02-{i + 1:02d}", nominal=True,
                    orientacao_governo="Sim"))
        fs.append(F("voto", f"v{i}:1", votacao_id=f"v{i}", deputado_id="1", voto="Sim"))
        fs.append(F("voto", f"v{i}:2", votacao_id=f"v{i}", deputado_id="2",
                    voto="Não" if i % 2 else "Sim"))
    # nominal sem orientação utilizável (Liberado) e nominal com abstenção do dep 2
    fs.append(F("votacao", "nl", data="2025-03-10", nominal=True, orientacao_governo="Liberado"))
    fs.append(F("voto", "nl:1", votacao_id="nl", deputado_id="1", voto="Sim"))
    fs.append(F("votacao", "ab", data="2025-03-11", nominal=True, orientacao_governo="Não"))
    fs.append(F("voto", "ab:2", votacao_id="ab", deputado_id="2", voto="Abstenção"))
    # simbólica: sem voto individual; mesmo que exista um fato de voto, não conta
    fs.append(F("votacao", "sim1", data="2025-03-27", nominal=False, orientacao_governo="Sim"))
    fs.append(F("voto", "sim1:2", votacao_id="sim1", deputado_id="2", voto="Sim"))
    # votação sem data (não entra no min/max) e sem orientação
    fs.append(F("votacao", "sd", nominal=True, orientacao_governo=None))
    # despesas de outra fonte, coletadas depois
    fs.append(F("despesa_ceap", "d1", fonte="camara_ceap", coletado_em=T2, deputado_id="1",
                valor=10.0, categoria="c", data="2024-05-01"))
    fs.append(F("despesa_ceap", "d2", fonte="camara_ceap", coletado_em=T3, deputado_id="2",
                valor=20.0, categoria="c", data="2024-05-02"))
    return fs


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "c.duckdb")
    fatos = fatos_base()
    s.upsert_facts(fatos)
    res = forward.run(FactBase(fatos), load_rules())
    s.save_findings(res.findings, res.explanations)
    return s


@pytest.fixture
def client(store):
    with TestClient(create_app(store=store)) as c:
        yield c


# --------------------------------------------------------------------------- Store
def test_janela_votos_usa_datas_e_atributos_das_votacoes(store):
    j = store.janela_votos()
    assert (j.inicio, j.fim) == (date(2025, 2, 1), date(2025, 3, 27))
    assert j.n_votacoes == 12 + 4
    assert j.n_votacoes_nominais == 12 + 3  # v0..v11, nl, ab, sd (a simbólica fica de fora)
    assert j.n_votacoes_com_orientacao == 12 + 2  # Sim/Não: v0..v11, ab e sim1 ("Liberado"/vazio não)


def test_janela_votos_de_base_sem_votacoes(tmp_path):
    s = Store(tmp_path / "v.duckdb")
    s.upsert_facts([F("deputado", "1", nome="Ana")])
    j = s.janela_votos()
    assert (j.inicio, j.fim, j.n_votacoes, j.n_votacoes_nominais,
            j.n_votacoes_com_orientacao) == (None, None, 0, 0, 0)


def test_cobertura_por_fonte_agrega_tipos_contagem_e_datas(store):
    por_fonte = {f.fonte: f for f in store.cobertura_fontes()}
    assert sorted(por_fonte) == ["camara_api_v2", "camara_ceap"]
    ceap = por_fonte["camara_ceap"]
    assert ceap.tipos == ["despesa_ceap"] and ceap.n_fatos == 2
    assert (ceap.coletado_em_min, ceap.coletado_em_max) == (T2, T3)
    camara = por_fonte["camara_api_v2"]
    assert camara.tipos == ["deputado", "votacao", "voto"]
    assert camara.n_fatos == 3 + 16 + 27  # 3 deputados, 16 votações, 27 votos
    assert camara.coletado_em_min == camara.coletado_em_max == T1


def test_contagem_de_votos_do_deputado_segue_as_regras_do_predicado(store):
    assert store.contagem_votos("1") == (13, 12)   # 12 válidos + 1 em votação sem orientação
    assert store.contagem_votos("2") == (13, 12)   # 12 válidos + abstenção; simbólica não conta
    assert store.contagem_votos("3") == (0, 0)


def test_contagem_do_sql_bate_com_a_do_predicado_para_todos_os_deputados(store):
    fb = FactBase(fatos_base())
    forward.run(fb, load_rules())  # aplica o guardrail R02, como o motor
    esperado: dict[str, int] = {}
    for _, dep, _ in _votos_validos(fb):
        esperado[dep] = esperado.get(dep, 0) + 1
    for dep in ("1", "2", "3"):
        assert store.contagem_votos(dep)[1] == esperado.get(dep, 0)


def test_consultas_usam_parametros_e_nao_concatenam_o_id(store):
    assert store.contagem_votos("1' OR '1'='1") == (0, 0)


# --------------------------------------------------------------------------- /cobertura
def test_cobertura_resposta(client):
    r = client.get("/cobertura")
    assert r.status_code == 200
    c = r.json()
    assert c["contract_version"] == CONTRACT_VERSION == "0.2.0"
    assert c["janela_votos"] == {"inicio": "2025-02-01", "fim": "2025-03-27", "n_votacoes": 16,
                                 "n_votacoes_nominais": 15, "n_votacoes_com_orientacao": 14}
    assert [f["fonte"] for f in c["fontes"]] == ["camara_api_v2", "camara_ceap"]
    assert c["fontes"][1]["tipos"] == ["despesa_ceap"] and c["fontes"][1]["n_fatos"] == 2
    assert c["fontes"][1]["coletado_em_min"].startswith("2026-11-21T12:30:00")
    assert c["fontes"][1]["coletado_em_max"].startswith("2026-11-22T08:00:00")
    assert c["n_deputados"] == 3
    assert c["n_findings"] >= 1


def test_cobertura_com_banco_vazio_nao_quebra(tmp_path):
    s = Store(tmp_path / "vazio.duckdb")
    with TestClient(create_app(store=s)) as c:
        corpo = c.get("/cobertura").json()
    assert corpo["fontes"] == [] and corpo["n_deputados"] == 0
    assert corpo["janela_votos"]["inicio"] is None and corpo["janela_votos"]["n_votacoes"] == 0


# --------------------------------------------------------------------------- /metricas
def test_metricas_do_deputado_com_findings(client):
    r = client.get("/deputados/1/metricas")
    assert r.status_code == 200
    m = r.json()
    assert m["deputado_id"] == 1
    assert (m["n_votos"], m["n_votos_validos"]) == (13, 12)
    assert m["janela_votos"]["n_votacoes"] == 16
    por_regra = {x["regra"]: x for x in m["metricas_por_regra"]}
    r01 = por_regra["R01"]
    assert r01["finding_id"] == "R01:1"
    assert r01["valores"] == {"taxa_governismo": 1.0, "n_votacoes": 12, "taxa_pct": 100}
    assert r01["valores"]["n_votacoes"] == m["n_votos_validos"]  # mesma contagem do predicado


def test_metricas_traz_uma_entrada_por_regra_de_inferencia_com_finding_id_nulo(client):
    m = client.get("/deputados/3/metricas").json()
    regras = [r.id for r in load_rules() if r.tipo == "inferencia"]
    assert [x["regra"] for x in m["metricas_por_regra"]] == regras
    assert "R02" not in regras  # guardrail não é regra de inferência
    assert all(x["finding_id"] is None and x["valores"] == {} for x in m["metricas_por_regra"])
    assert (m["n_votos"], m["n_votos_validos"]) == (0, 0)


def test_metricas_achata_valores_nao_escalares(client, tmp_path):
    fs = fatos_base() + [
        F("despesa_ceap", "n3", fonte="camara_ceap", deputado_id="1", cnpj="00000000000003",
          fornecedor="Posto", valor=1030.0, categoria="combustivel", data="2025-02-10"),
        F("sancao", "ceis1", fonte="cgu_ceis", cnpj="00000000000003", cadastro="CEIS",
          inicio="2025-01-01", fim=None)]
    s = Store(tmp_path / "r03.duckdb")
    s.upsert_facts(fs)
    res = forward.run(FactBase(fs), load_rules())
    s.save_findings(res.findings, res.explanations)
    with TestClient(create_app(store=s)) as c:
        m = c.get("/deputados/1/metricas").json()
    r03 = next(x for x in m["metricas_por_regra"] if x["regra"] == "R03")
    assert r03["finding_id"] == "R03:1"
    assert r03["valores"] == {"n_despesas": 1, "valor_total": 1030.0, "n_cnpjs": 1}


def test_metricas_nao_expoe_booleanos_nem_nulos():
    from api import state
    valores = {"a": True, "b": None, "c": {"x": 1}, "d": [1, 2, 3], "e": "texto", "f": 0.5, "g": 7}
    assert state._escalares(valores) == {"n_d": 3, "e": "texto", "f": 0.5, "g": 7}


def test_metricas_404_para_deputado_inexistente_e_422_para_id_invalido(client):
    r = client.get("/deputados/999/metricas")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert client.get("/deputados/abc/metricas").status_code == 422
    assert client.get("/deputados/1;DROP/metricas").status_code == 422


def test_endpoints_novos_so_aceitam_get(client):
    assert client.post("/cobertura").status_code == 405
    assert client.post("/deputados/1/metricas").status_code == 405
