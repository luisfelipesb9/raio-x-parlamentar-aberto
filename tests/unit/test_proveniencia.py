"""Proveniência nas evidências: coletado_em do fato de origem e sha256 do bruto (ADR-007).

sha256_bruto só aparece quando o manifesto tem UM arquivo para a fonte do fato; com vários
arquivos (ex.: Câmara, CGU, RFB) fica None, porque o fato não diz de qual deles veio.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from contracts import Evidence, Fact
from engine import forward, proveniencia
from engine.factbase import FactBase
from engine.rules import load_rules

T_VOTOS = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
T_CEAP = datetime(2026, 11, 21, 15, 30, tzinfo=UTC)
T_SANCAO = datetime(2026, 11, 22, 7, 45, tzinfo=UTC)


def F(tipo, chave, fonte="teste", coletado_em=T_VOTOS, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte=fonte, id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}", coletado_em=coletado_em)


def fatos():
    fs = []
    for i in range(12):
        fs.append(F("votacao", f"v{i}", fonte="camara_api_v2", nominal=True,
                    orientacao_governo="Sim"))
        fs.append(F("voto", f"v{i}:1", fonte="camara_api_v2", votacao_id=f"v{i}",
                    deputado_id="1", voto="Sim"))
    fs.append(F("despesa_ceap", "n3", fonte="camara_ceap", coletado_em=T_CEAP, deputado_id="3",
                cnpj="00000000000003", fornecedor="Posto", valor=1030.0, categoria="c",
                data="2025-02-10"))
    fs.append(F("sancao", "ceis1", fonte="cgu_ceis", coletado_em=T_SANCAO, cnpj="00000000000003",
                cadastro="CEIS", inicio="2025-01-01", fim=None))
    return fs


def evidencias(res, finding_id):
    return next(f for f in res.findings if f.id == finding_id).evidencias


# --------------------------------------------------------------------------- engine
def test_evidencias_recebem_coletado_em_do_fato_de_origem():
    res = forward.run(FactBase(fatos()), load_rules())
    assert {e.coletado_em for e in evidencias(res, "R01:1")} == {T_VOTOS}
    r03 = {e.tipo: e.coletado_em for e in evidencias(res, "R03:3")}
    assert r03 == {"despesa_ceap": T_CEAP, "sancao": T_SANCAO}


def test_sha256_so_aparece_quando_informado_para_a_fonte_do_fato():
    sem = forward.run(FactBase(fatos()), load_rules())
    assert all(e.sha256_bruto is None for f in sem.findings for e in f.evidencias)
    com = forward.run(FactBase(fatos()), load_rules(),
                      sha_por_fonte={"camara_ceap": "a" * 64})  # cgu_ceis e camara_api_v2: sem hash
    r03 = {e.tipo: e.sha256_bruto for e in evidencias(com, "R03:3")}
    assert r03 == {"despesa_ceap": "a" * 64, "sancao": None}
    assert all(e.sha256_bruto is None for e in evidencias(com, "R01:1"))


def test_proveniencia_nao_muda_cf_valores_nem_conclusao():
    base = forward.run(FactBase(fatos()), load_rules())
    com = forward.run(FactBase(fatos()), load_rules(), sha_por_fonte={"camara_ceap": "b" * 64})
    excluir = {"evidencias"}
    assert [f.model_dump(exclude=excluir) for f in base.findings] == \
        [f.model_dump(exclude=excluir) for f in com.findings]
    assert {k: v.model_dump() for k, v in base.explanations.items()} == \
        {k: v.model_dump() for k, v in com.explanations.items()}


def test_evidencia_sem_fato_correspondente_fica_como_veio():
    e = Evidence(tipo="despesa_ceap", id_oficial="nao-existe", url="https://x")
    [saida] = proveniencia.enriquecer([e], proveniencia.indexar(fatos()), {"camara_ceap": "c" * 64})
    assert saida == e and saida.coletado_em is None and saida.sha256_bruto is None


def test_enriquecer_nao_sobrescreve_valor_ja_preenchido():
    antigo = datetime(2020, 1, 1, tzinfo=UTC)
    e = Evidence(tipo="despesa_ceap", id_oficial="n3", coletado_em=antigo, sha256_bruto="d" * 64)
    [saida] = proveniencia.enriquecer([e], proveniencia.indexar(fatos()), {"camara_ceap": "c" * 64})
    assert (saida.coletado_em, saida.sha256_bruto) == (antigo, "d" * 64)


def test_id_oficial_repetido_usa_o_coletado_em_mais_antigo_de_forma_estavel():
    a = F("despesa_ceap", "x:1", coletado_em=T_CEAP)
    b = F("despesa_ceap", "x:2", coletado_em=T_VOTOS)
    a.id_oficial = b.id_oficial = "777"  # CEAP repete idDocumento (créditos/ajustes)
    idx1, idx2 = proveniencia.indexar([a, b]), proveniencia.indexar([b, a])
    assert idx1[("despesa_ceap", "777")].coletado_em == T_VOTOS
    assert idx2[("despesa_ceap", "777")].coletado_em == T_VOTOS


# --------------------------------------------------------------------------- API
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.main import create_app
from repo.store import Store
from sources import manifest


def banco_com_findings_antigos(tmp_path):
    """Findings gravados como o motor v0.1 fazia: evidências sem coletado_em/sha256_bruto."""
    s = Store(tmp_path / "t.duckdb")
    fs = fatos() + [F("deputado", d, nome=f"Dep {d}") for d in ("1", "3")]
    s.upsert_facts(fs)
    res = forward.run(FactBase(fs), load_rules())
    for f in res.findings:
        f.evidencias = [Evidence(tipo=e.tipo, id_oficial=e.id_oficial, url=e.url,
                                 descricao=e.descricao) for e in f.evidencias]
    s.save_findings(res.findings, res.explanations)
    return s


def test_api_preenche_a_proveniencia_de_findings_gravados_sem_ela(tmp_path):
    s = banco_com_findings_antigos(tmp_path)
    with TestClient(create_app(store=s, raw_dir=tmp_path / "sem_raw")) as c:
        evs = c.get("/deputados/3/findings").json()[0]["evidencias"]
    assert {e["tipo"]: e["coletado_em"][:19] for e in evs} == {
        "despesa_ceap": "2026-11-21T15:30:00", "sancao": "2026-11-22T07:45:00"}
    assert all(e["sha256_bruto"] is None for e in evs)


def test_api_usa_o_manifesto_so_para_fonte_com_um_arquivo(tmp_path, monkeypatch):
    s = banco_com_findings_antigos(tmp_path)
    raw = tmp_path / "raw"
    (raw / "ceap").mkdir(parents=True)
    (raw / "ceap" / "Ano-2024.json.zip").write_bytes(b"zip-ceap")
    (raw / "cgu").mkdir()
    (raw / "cgu" / "a.zip").write_bytes(b"a")
    (raw / "cgu" / "b.zip").write_bytes(b"b")
    manifest.gerar_retroativo(raw)
    monkeypatch.setattr(manifest, "_origens_por_fonte_fato",
                        lambda: {"camara_ceap": "ceap", "cgu_ceis": "cgu"})
    with TestClient(create_app(store=s, raw_dir=raw)) as c:
        evs = {e["tipo"]: e for e in c.get("/deputados/3/findings").json()[0]["evidencias"]}
    assert evs["despesa_ceap"]["sha256_bruto"] == manifest.sha256_arquivo(raw / "ceap" / "Ano-2024.json.zip")
    assert evs["sancao"]["sha256_bruto"] is None  # cgu tem 2 arquivos: não dá para saber qual


def test_api_nao_vaza_nada_novo_nas_evidencias(tmp_path):
    s = banco_com_findings_antigos(tmp_path)
    with TestClient(create_app(store=s, raw_dir=tmp_path / "sem_raw")) as c:
        corpo = json.dumps(c.get("/deputados/3/findings").json())
    assert "cpf" not in corpo.lower()


# --------------------------------------------------------------------------- CLI do motor
def test_engine_run_grava_findings_com_proveniencia(tmp_path, monkeypatch):
    from engine import run
    s = Store(tmp_path / "cli.duckdb")
    s.upsert_facts(fatos() + [F("deputado", "3", nome="Dep 3")])
    s.con.close()
    raw = tmp_path / "raw"
    (raw / "ceap").mkdir(parents=True)
    (raw / "ceap" / "Ano-2024.json.zip").write_bytes(b"zip-ceap")
    manifest.gerar_retroativo(raw)
    monkeypatch.setattr(manifest, "_origens_por_fonte_fato", lambda: {"camara_ceap": "ceap"})
    run.main(["--db", str(tmp_path / "cli.duckdb"), "--raw", str(raw)])
    lido = Store(tmp_path / "cli.duckdb", read_only=True).findings_of("3")
    evs = {e.tipo: e for e in lido[0].evidencias}
    assert evs["despesa_ceap"].coletado_em == T_CEAP
    assert evs["despesa_ceap"].sha256_bruto == manifest.sha256_arquivo(raw / "ceap" / "Ano-2024.json.zip")
    assert evs["sancao"].sha256_bruto is None
