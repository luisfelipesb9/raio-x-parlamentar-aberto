"""Fatiamento da janela de datas da API de votações da Câmara.

A API recusa (HTTP 400, "A diferença entre as datas não pode ser maior que 3 meses") janela
maior que 3 meses: janelas longas viram uma lista de fatias contíguas de até 3 meses.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from sources.camara.janelas import fatiar_janela


def test_um_trimestre_exato_continua_uma_fatia_so():
    assert fatiar_janela("2025-01-01", "2025-03-31") == [("2025-01-01", "2025-03-31")]


def test_um_ano_vira_quatro_trimestres():
    assert fatiar_janela("2025-01-01", "2025-12-31") == [
        ("2025-01-01", "2025-03-31"), ("2025-04-01", "2025-06-30"),
        ("2025-07-01", "2025-09-30"), ("2025-10-01", "2025-12-31")]


def test_a_ultima_fatia_pode_ser_curta():
    assert fatiar_janela("2025-01-15", "2025-05-10") == [
        ("2025-01-15", "2025-04-14"), ("2025-04-15", "2025-05-10")]


def test_janela_menor_que_um_trimestre_fica_inteira():
    assert fatiar_janela("2025-02-03", "2025-02-20") == [("2025-02-03", "2025-02-20")]


def test_dia_unico():
    assert fatiar_janela("2025-02-03", "2025-02-03") == [("2025-02-03", "2025-02-03")]


def test_inicio_no_fim_do_mes_nao_pula_nem_repete_dia():
    # 30/11 + 3 meses cai em fevereiro, que não tem dia 30
    fatias = fatiar_janela("2025-11-30", "2026-08-31")
    antes = date.fromisoformat("2025-11-30") - timedelta(days=1)
    for a, b in fatias:
        assert date.fromisoformat(a) == antes + timedelta(days=1)  # contíguas, sem lacuna
        assert date.fromisoformat(b) >= date.fromisoformat(a)
        antes = date.fromisoformat(b)
    assert antes == date(2026, 8, 31)


@pytest.mark.parametrize("ini,fim", [("2025-01-01", "2025-12-31"), ("2023-02-01", "2026-11-26"),
                                      ("2025-01-31", "2025-10-31"), ("2024-02-29", "2025-02-28")])
def test_nenhuma_fatia_passa_de_tres_meses(ini, fim):
    for a, b in fatiar_janela(ini, fim):
        da, db = date.fromisoformat(a), date.fromisoformat(b)
        meses = (db.year - da.year) * 12 + db.month - da.month
        assert meses <= 3, (a, b)
        assert db - da <= timedelta(days=92)


def test_janela_invertida_e_erro():
    with pytest.raises(ValueError, match="início"):
        fatiar_janela("2025-04-01", "2025-03-31")


def test_data_invalida_e_erro():
    with pytest.raises(ValueError):
        fatiar_janela("2025-13-01", "2025-12-31")


@pytest.mark.parametrize("meses", [0, -1])
def test_meses_por_fatia_menor_que_um_e_erro_em_vez_de_laco_infinito(meses):
    with pytest.raises(ValueError, match="meses"):
        fatiar_janela("2025-01-01", "2025-12-31", meses=meses)
