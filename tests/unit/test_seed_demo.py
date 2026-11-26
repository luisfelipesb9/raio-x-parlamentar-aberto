"""scripts/seed_demo.py: banco de demonstração 100% fictício, gerado sem rede."""
from collections import Counter

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import create_app
from ingest.varredura import varrer_banco
from repo.store import Store
from scripts import seed_demo


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    db = tmp_path_factory.mktemp("demo") / "demo.duckdb"
    resumo = seed_demo.gerar(db)
    return db, resumo


@pytest.fixture(scope="module")
def store(demo):
    s = Store(demo[0], read_only=True)
    yield s
    s.con.close()


def test_gera_seis_deputados_ficticios_com_ids_fora_da_faixa_real(store):
    deps = store.facts_by_tipo("deputado")
    assert len(deps) == 6
    assert all(int(d.chave) >= 9_900_000 for d in deps)  # a Câmara não chega perto disso
    assert all("(demo)" in d.atributos["nome"] for d in deps)
    assert all(d.atributos["partido"].startswith("FICT-") for d in deps)


def test_todo_fato_e_rotulado_como_demonstracao_e_nao_aponta_para_fonte_real(store):
    fatos = store.load_facts()
    assert {f.fonte for f in fatos} == {"demo_ficticio"}
    assert all(f.url and ".invalid/" in f.url for f in fatos)


def test_cobre_todos_os_tipos_de_fato_do_contrato(store):
    tipos = Counter(f.tipo for f in store.load_facts())
    esperados = {"deputado", "votacao", "voto", "proposicao", "autoria", "despesa_ceap", "sancao",
                 "empresa", "socio", "candidatura", "doacao", "emenda", "votos_municipio"}
    assert esperados <= set(tipos)
    assert tipos["deputado"] == 6
    assert tipos["voto"] > 100 and tipos["despesa_ceap"] > 30


def test_tem_votacoes_nominais_e_simbolicas_com_orientacao(store):
    votacoes = store.facts_by_tipo("votacao")
    nominais = [v for v in votacoes if v.atributos["nominal"]]
    simbolicas = [v for v in votacoes if not v.atributos["nominal"]]
    assert len(nominais) >= 30 and len(simbolicas) >= 2
    assert all(v.atributos["orientacao_governo"] in ("Sim", "Não") for v in simbolicas)
    assert "FICTÍCIOS PARA DEMONSTRAÇÃO" in votacoes[0].atributos["descricao"]
    com_voto = {v.atributos["votacao_id"] for v in store.facts_by_tipo("voto")}
    assert not com_voto & {v.chave for v in simbolicas}  # simbólica não tem voto individual


def test_motor_produz_os_findings_esperados(store):
    por_regra: dict[str, set[str]] = {}
    for dep in store.facts_by_tipo("deputado"):
        for f in store.findings_of(dep.chave):
            por_regra.setdefault(f.regra, set()).add(dep.chave)
    for regra in ("R01", "R03", "R04", "R05", "R07"):
        assert por_regra.get(regra), f"nenhum finding de {regra}"
    assert len(por_regra["R01"]) >= 2 and len(por_regra["R05"]) >= 3
    assert len(por_regra["R03"]) == 2  # sanção vigente; a expirada não conta
    assert len(por_regra["R04"]) == 1 and len(por_regra["R07"]) >= 2


def test_nao_ha_cpf_integro_de_terceiro_no_banco(store):
    assert varrer_banco(store) == []


def test_resumo_devolve_as_contagens(demo):
    _, resumo = demo
    assert resumo["deputados"] == 6
    assert resumo["findings"] >= 8
    assert {"R01", "R03", "R04", "R05", "R07"} <= set(resumo["regras"])


def test_gerar_de_novo_substitui_o_banco_sem_duplicar(tmp_path):
    db = tmp_path / "d.duckdb"
    primeiro = seed_demo.gerar(db)
    segundo = seed_demo.gerar(db)
    assert primeiro == segundo


# ---- pela API: casos de "dados insuficientes" e "abaixo do limiar" da R01 ----

@pytest.fixture(scope="module")
def cliente(demo):
    with TestClient(create_app(demo[0])) as c:
        yield c


def _motivo_r01(cliente, dep_id):
    r = cliente.get("/perguntar", params={"deputado": dep_id, "objetivo": "alinhado_governo"})
    assert r.status_code == 200
    passos = [p for p in r.json()["trilha"] if p["regra"] == "R01"]
    return (passos[0].get("diagnostico") or {}).get("motivo") if passos else None


def test_r01_tem_casos_de_dados_insuficientes_e_abaixo_do_limiar(cliente, store):
    motivos = {_motivo_r01(cliente, d.chave) for d in store.facts_by_tipo("deputado")}
    assert {"dados_insuficientes", "abaixo_do_limiar", None} <= motivos


def test_saude_informa_base_pseudonimizada(cliente):
    corpo = cliente.get("/saude").json()
    assert corpo["status"] == "ok" and corpo["pseudonimizado"] is True
    assert corpo["n_deputados"] == 6
