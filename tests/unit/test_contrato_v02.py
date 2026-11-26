"""Contrato v0.2.0: campos novos são opcionais, o que já existia continua válido (ADR-007)."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from api.schemas import (
    CoberturaResposta,
    Diagnostico,
    FonteCobertura,
    GrafoResposta,
    JanelaVotos,
    MetricaRegra,
    MetricasDeputadoResposta,
    OcultoResumo,
    PassoProva,
)
from contracts import CONTRACT_VERSION, Evidence, GraphEdge, GraphNode
from scripts.export_schemas import export


def test_versao_do_contrato_e_0_2_0():
    assert CONTRACT_VERSION == "0.2.0"


# --------------------------------------------------------------------------- grafo
GRAFO_ANTIGO = {
    "centro": "deputado:1",
    "profundidade": 1,
    "nodes": [{"id": "deputado:1", "tipo": "deputado", "rotulo": "Ana", "atributos": {}}],
    "edges": [],
    "truncado": False,
}


def test_grafo_antigo_sem_campos_novos_continua_valido():
    g = GrafoResposta.model_validate(GRAFO_ANTIGO)
    assert g.total_nos is None
    assert g.total_arestas is None
    assert g.ocultos == []


def test_grafo_aceita_totais_e_ocultos():
    g = GrafoResposta(
        centro="deputado:1", profundidade=2,
        nodes=[GraphNode(id="deputado:1", tipo="deputado", rotulo="Ana")],
        edges=[GraphEdge(origem="deputado:1", destino="empresa:9", relacao="recebeu")],
        truncado=True, total_nos=120, total_arestas=300,
        ocultos=[OcultoResumo(tipo="empresa", relacao="recebeu", quantidade=40),
                 OcultoResumo(tipo="municipio", relacao=None, quantidade=7)],
    )
    assert g.total_nos == 120 and g.total_arestas == 300
    assert [(o.tipo, o.relacao, o.quantidade) for o in g.ocultos] == [
        ("empresa", "recebeu", 40), ("municipio", None, 7)]


def test_ocultos_default_nao_e_compartilhado_entre_instancias():
    a = GrafoResposta.model_validate(GRAFO_ANTIGO)
    b = GrafoResposta.model_validate(GRAFO_ANTIGO)
    a.ocultos.append(OcultoResumo(tipo="x", relacao=None, quantidade=1))
    assert b.ocultos == []


def test_oculto_exige_tipo_e_quantidade():
    with pytest.raises(ValidationError):
        OcultoResumo.model_validate({"relacao": "recebeu", "quantidade": 1})
    with pytest.raises(ValidationError):
        OcultoResumo.model_validate({"tipo": "empresa", "relacao": None})


# --------------------------------------------------------------------------- diagnóstico do /perguntar
PASSO_ANTIGO = {"profundidade": 0, "objetivo": "alinhado_governo", "regra": "R01", "cf": 0.0,
                "nota": "sem votos suficientes"}


def test_passo_antigo_sem_diagnostico_continua_valido():
    passo = PassoProva.model_validate(PASSO_ANTIGO)
    assert passo.diagnostico is None


@pytest.mark.parametrize("motivo", ["dados_insuficientes", "abaixo_do_limiar",
                                    "sem_regra_aplicavel"])
def test_diagnostico_aceita_os_tres_motivos(motivo):
    d = Diagnostico(motivo=motivo)
    assert d.motivo == motivo
    assert d.detalhes == {}


def test_diagnostico_rejeita_motivo_desconhecido():
    with pytest.raises(ValidationError):
        Diagnostico(motivo="outro_motivo")


def test_diagnostico_detalhes_da_r01():
    d = Diagnostico(motivo="dados_insuficientes",
                    detalhes={"n_votos_validos": 3, "minimo_votos": 10, "taxa": 0.66,
                              "limiar": 0.7})
    assert d.detalhes["n_votos_validos"] == 3
    assert d.detalhes["limiar"] == 0.7


def test_diagnostico_detalhes_rejeita_valor_fora_de_numero_ou_texto():
    with pytest.raises(ValidationError):
        Diagnostico(motivo="abaixo_do_limiar", detalhes={"lista": [1, 2]})


def test_passo_com_diagnostico_e_serializa_aninhado():
    passo = PassoProva(**PASSO_ANTIGO,
                       diagnostico=Diagnostico(motivo="abaixo_do_limiar", detalhes={"taxa": 0.4}))
    assert passo.model_dump()["diagnostico"] == {"motivo": "abaixo_do_limiar",
                                                 "detalhes": {"taxa": 0.4}}


# --------------------------------------------------------------------------- proveniência
def test_evidence_antiga_continua_valida_e_proveniencia_e_opcional():
    e = Evidence(tipo="voto", id_oficial="v1")
    assert e.coletado_em is None
    assert e.sha256_bruto is None


def test_evidence_guarda_coleta_e_hash_do_bruto():
    quando = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    e = Evidence(tipo="voto", id_oficial="v1", coletado_em=quando, sha256_bruto="ab" * 32)
    assert e.coletado_em == quando
    assert e.sha256_bruto == "ab" * 32


def test_fact_continua_com_coletado_em_automatico():
    from contracts import Fact

    f = Fact(tipo="deputado", chave="1", fonte="camara_api_v2", id_oficial="1")
    assert f.coletado_em.tzinfo is not None


# --------------------------------------------------------------------------- cobertura e métricas
def _janela() -> JanelaVotos:
    return JanelaVotos(inicio=date(2023, 2, 1), fim=date(2026, 10, 31), n_votacoes=900,
                       n_votacoes_nominais=400, n_votacoes_com_orientacao=350)


def test_janela_de_votos_aceita_periodo_vazio():
    j = JanelaVotos(inicio=None, fim=None, n_votacoes=0, n_votacoes_nominais=0,
                    n_votacoes_com_orientacao=0)
    assert j.inicio is None and j.fim is None


def test_cobertura_resposta_valida_e_serializa():
    c = CoberturaResposta(
        contract_version=CONTRACT_VERSION, janela_votos=_janela(),
        fontes=[FonteCobertura(fonte="camara_api_v2", tipos=["deputado", "voto"], n_fatos=1000,
                               coletado_em_min=datetime(2026, 11, 1, tzinfo=UTC),
                               coletado_em_max=None)],
        n_deputados=20, n_findings=85)
    dados = json.loads(c.model_dump_json())
    assert dados["fontes"][0]["tipos"] == ["deputado", "voto"]
    assert dados["fontes"][0]["coletado_em_max"] is None
    assert dados["janela_votos"]["inicio"] == "2023-02-01"
    assert dados["contract_version"] == "0.2.0"


def test_fonte_cobertura_exige_n_fatos():
    with pytest.raises(ValidationError):
        FonteCobertura.model_validate({"fonte": "x", "tipos": [], "coletado_em_min": None,
                                       "coletado_em_max": None})


def test_metricas_do_deputado_com_metricas_por_regra():
    m = MetricasDeputadoResposta(
        deputado_id=204554, n_votos=300, n_votos_validos=280, janela_votos=_janela(),
        metricas_por_regra=[
            MetricaRegra(regra="R01", finding_id="f-1",
                         valores={"taxa": 0.82, "n_votos_validos": 280, "orientacao": "governo"}),
            MetricaRegra(regra="R02", finding_id=None, valores={})])
    assert m.metricas_por_regra[0].valores["taxa"] == 0.82
    assert m.metricas_por_regra[1].finding_id is None


def test_metrica_regra_rejeita_valor_composto():
    with pytest.raises(ValidationError):
        MetricaRegra(regra="R01", finding_id=None, valores={"x": {"a": 1}})


# --------------------------------------------------------------------------- JSON Schema exportado
@pytest.fixture(scope="module")
def schemas(tmp_path_factory):
    destino = tmp_path_factory.mktemp("schemas")
    export(destino)
    return destino


def _carrega(destino, nome: str) -> dict:
    return json.loads((destino / f"{nome}.json").read_text(encoding="utf-8"))


def test_schema_exportado_do_grafo_tem_campos_novos(schemas):
    s = _carrega(schemas, "GrafoResposta")
    assert {"total_nos", "total_arestas", "ocultos"} <= set(s["properties"])
    assert "OcultoResumo" in s["$defs"]
    assert set(s["$defs"]["OcultoResumo"]["properties"]) == {"tipo", "relacao", "quantidade"}


def test_schema_exportado_do_passo_tem_diagnostico_com_motivos_fechados(schemas):
    s = _carrega(schemas, "PassoProva")
    assert "diagnostico" in s["properties"]
    assert s["$defs"]["Diagnostico"]["properties"]["motivo"]["enum"] == [
        "dados_insuficientes", "abaixo_do_limiar", "sem_regra_aplicavel"]


def test_schema_exportado_da_evidencia_tem_proveniencia(schemas):
    s = _carrega(schemas, "Evidence")
    assert {"coletado_em", "sha256_bruto"} <= set(s["properties"])


def test_schemas_novos_de_cobertura_e_metricas_sao_exportados(schemas):
    for nome in ("CoberturaResposta", "FonteCobertura", "JanelaVotos", "MetricasDeputadoResposta",
                 "MetricaRegra", "Diagnostico", "OcultoResumo"):
        assert (schemas / f"{nome}.json").exists(), nome
    manifesto = _carrega(schemas, "index")
    assert manifesto["contract_version"] == "0.2.0"
    assert {"CoberturaResposta", "MetricasDeputadoResposta", "Diagnostico"} <= set(
        manifesto["schemas"])
