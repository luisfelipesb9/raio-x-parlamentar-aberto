"""Escopo gravado no bruto da Câmara (`_escopo`) e a regra de reaproveitamento (`--reusar-raw`).

Um bruto de amostra (teto de votações, outra fonte de votos, outra legislatura) não pode alimentar
uma rodada nacional em silêncio. Sem rede: o fetch usa httpx.MockTransport.
"""
from __future__ import annotations

import json

import httpx
import pytest

import sources.base
from sources.camara.escopo import avaliar_reuso, escopo_da_coleta
from sources.camara.source import CamaraSource

JANELA = ("2025-01-01", "2025-03-31")


def _esc(**kw):
    base = {"legislatura_completa": False, "janela_inicio": JANELA[0], "janela_fim": JANELA[1],
            "fonte_votos": "api", "max_votacoes": None}
    return escopo_da_coleta(**{**base, **kw})


# ---------- função pura ----------

def test_escopo_da_coleta_guarda_o_que_muda_o_conteudo_do_bruto():
    assert _esc(legislatura=57, max_votacoes=145) == {
        "legislatura": 57, "legislatura_completa": False, "janela": list(JANELA),
        "fonte_votos": "api", "max_votacoes": 145}


def test_mesmo_escopo_serve():
    assert avaliar_reuso(_esc(), _esc(), estrito=True) == (True, "")


def test_bruto_sem_teto_serve_a_um_pedido_com_teto_menor_ou_igual():
    assert avaliar_reuso(_esc(max_votacoes=None), _esc(max_votacoes=145), estrito=True)[0]
    assert avaliar_reuso(_esc(max_votacoes=145), _esc(max_votacoes=100), estrito=True)[0]
    assert avaliar_reuso(_esc(max_votacoes=145), _esc(max_votacoes=145), estrito=True)[0]


def test_bruto_com_teto_nao_serve_a_pedido_com_teto_maior_ou_sem_teto():
    for pedido in (_esc(max_votacoes=None), _esc(max_votacoes=300)):
        ok, motivo = avaliar_reuso(_esc(max_votacoes=145), pedido, estrito=False)
        assert not ok and "145" in motivo and "votações" in motivo


@pytest.mark.parametrize("campo,valor,palavra", [
    ("legislatura_completa", True, "legislatura"),
    ("fonte_votos", "dump", "fonte de votos"),
    ("janela_inicio", "2025-02-01", "janela"),
    ("janela_fim", "2025-12-31", "janela"),
])
def test_escopo_diferente_nao_serve_e_diz_por_que(campo, valor, palavra):
    ok, motivo = avaliar_reuso(_esc(), _esc(**{campo: valor}), estrito=False)
    assert not ok and palavra in motivo


def test_bruto_antigo_sem_escopo_so_serve_a_rodada_de_amostra_e_avisa():
    ok, aviso = avaliar_reuso(None, _esc(), estrito=False)
    assert ok and "sem registro de escopo" in aviso
    ok, motivo = avaliar_reuso(None, _esc(), estrito=True)
    assert not ok and "sem registro de escopo" in motivo


def test_escopo_ilegivel_e_tratado_como_ausente():
    assert avaliar_reuso("lixo", _esc(), estrito=True)[0] is False  # type: ignore[arg-type]


# ---------- o fetch grava o escopo no bruto ----------

@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def _fonte() -> CamaraSource:
    client = httpx.Client(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={"dados": [], "links": []})))
    return CamaraSource(client=client, pausa=0, dormir=lambda s: None)


def test_fetch_grava_o_escopo_no_bruto_devolvido_e_no_arquivo(raw_dir):
    raw = _fonte().fetch(data_inicio=JANELA[0], data_fim=JANELA[1], max_votacoes=0)
    esperado = _esc(legislatura=57, max_votacoes=0)
    assert raw["_escopo"] == esperado
    em_disco = json.loads((raw_dir / "camara" / "camara_2025-01-01_2025-03-31.json")
                          .read_text(encoding="utf-8"))
    assert em_disco["_escopo"] == esperado


def test_fetch_com_legislatura_completa_e_dump_registra_isso(raw_dir):
    raw = _fonte().fetch(data_inicio=JANELA[0], data_fim=JANELA[1], max_votacoes=0,
                         legislatura_completa=True, fonte_votos="api")
    assert raw["_escopo"]["legislatura_completa"] is True


def test_normalize_ignora_o_escopo_gravado(raw_dir):
    raw = {"deputados": [{"id": 1, "nome": "A", "siglaUf": "MG"}], "votacoes": [],
           "_escopo": _esc()}
    assert [f.chave for f in CamaraSource().normalize(raw)] == ["1"]
