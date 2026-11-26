"""Pico de memória do TSE: uma UF por vez x as UFs acumuladas (tracemalloc, fixture sintética).

As UFs são fictícias (AA...AH) e os zips, falsos (MockTransport), com o mesmo formato do TSE
(latin-1, ';', tudo entre aspas, só as colunas que o normalize usa). O volume por UF é pequeno de
propósito (rápido em CI); o que o teste prova é a PROPORÇÃO: o pico do modo por UF não cresce com
o número de UFs, o do modo acumulado cresce. O pico real de uma UF grande (SP) NÃO é medido aqui:
extrapole pelos bytes por linha impressos (rode com `pytest -s tests/unit/test_tse_memoria.py`).
"""
from __future__ import annotations

import csv
import io
import tracemalloc
import zipfile
from collections.abc import Callable

import pytest

import sources.base
from ingest.pipeline import Opcoes, Pipeline
from repo.store import Store
from sources.tse.source import _CONJUNTOS, TseSource
from tests.unit.test_src_tse import URL_CAND, URL_PREST, URL_VOTOS, _servidor

UFS = [f"A{c}" for c in "ABCDEFGH"]  # 8 UFs fictícias
CANDIDATOS_POR_UF, MUNICIPIOS_POR_UF, ZONAS = 120, 40, 2
RECEITAS_POR_CANDIDATO = 6


def _csv(conjunto: str, linhas: list[dict]) -> bytes:
    colunas = _CONJUNTOS[conjunto][2]
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    w.writerow(colunas)
    for r in linhas:
        w.writerow([r.get(c, "") for c in colunas])
    return buf.getvalue().encode("latin-1")


def _zip(membros: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, corpo in membros.items():
            z.writestr(nome, corpo)
    return buf.getvalue()


def _zips_sinteticos() -> dict[str, bytes]:
    cand, rec, vot = {}, {}, {}
    for uf in UFS:
        sqs = [f"{uf}{i:04d}" for i in range(CANDIDATOS_POR_UF)]
        cand[f"consulta_cand_2022_{uf}.csv"] = _csv("candidatos", [
            {"ANO_ELEICAO": "2022", "SQ_CANDIDATO": sq, "NR_CPF_CANDIDATO": f"99999{n:06d}",
             "NM_CANDIDATO": f"CANDIDATO NUMERO {sq} DA SILVA", "NM_URNA_CANDIDATO": f"URNA {sq}",
             "DS_CARGO": "DEPUTADO FEDERAL", "SG_UF": uf, "SG_PARTIDO": "PX",
             "DS_SIT_TOT_TURNO": "NÃO ELEITO"} for n, sq in enumerate(sqs)])
        rec[f"receitas_candidatos_2022_{uf}.csv"] = _csv("receitas", [
            {"AA_ELEICAO": "2022", "SQ_CANDIDATO": sq, "DS_CARGO": "Deputado Federal",
             "SQ_RECEITA": f"{sq}{j}", "NM_DOADOR": f"DOADOR {j} DE {sq}",
             "NM_DOADOR_RFB": f"DOADOR {j} DE {sq} LTDA", "NR_CPF_CNPJ_DOADOR": "35492333000160",
             "DS_ORIGEM_RECEITA": "Recursos de pessoas juridicas", "DT_RECEITA": "01/09/2022",
             "VR_RECEITA": "100,50"} for sq in sqs for j in range(RECEITAS_POR_CANDIDATO)])
        vot[f"votacao_candidato_munzona_2022_{uf}.csv"] = _csv("votacao", [
            {"ANO_ELEICAO": "2022", "SG_UF": uf, "CD_MUNICIPIO": str(10000 + m),
             "NM_MUNICIPIO": f"MUNICIPIO {m} DE {uf}", "DS_CARGO": "Deputado Federal",
             "SQ_CANDIDATO": sq, "QT_VOTOS_NOMINAIS_VALIDOS": str(7 + z)}
            for sq in sqs for m in range(MUNICIPIOS_POR_UF) for z in range(ZONAS)])
    return {URL_CAND: _zip(cand), URL_PREST: _zip(rec), URL_VOTOS: _zip(vot)}


@pytest.fixture(scope="module")
def zips() -> dict[str, bytes]:
    return _zips_sinteticos()


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def _pico(rodar: Callable[[], object]) -> int:
    """Pico, em bytes, de memória Python alocada durante `rodar` (tracemalloc)."""
    tracemalloc.start()
    try:
        rodar()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def _pico_pipeline(zips: dict[str, bytes], n_ufs: int, monkeypatch) -> tuple[int, Store]:
    """Pico do pipeline nacional (uma UF por vez) limitado às `n_ufs` primeiras UFs."""
    original = TseSource._ufs_do_zip
    with monkeypatch.context() as m:
        m.setattr(TseSource, "_ufs_do_zip",
                  staticmethod(lambda z, c, a: original(z, c, a)[:n_ufs]))
        store = Store(":memory:")
        pipe = Pipeline(store, Opcoes(fontes=("tse",)),
                        registry={"tse": lambda: TseSource(client=_servidor(zips))},
                        log=lambda _: None)
        return _pico(pipe.executar), store


def test_pico_por_uf_e_menor_que_o_acumulado_e_nao_cresce_com_o_numero_de_ufs(
        zips, raw_dir, capsys, monkeypatch):
    # modo antigo: fetch(uf=None) devolve as 8 UFs juntas em memória (e o pipeline as normalizava)
    acumulado = _pico(lambda: TseSource(client=_servidor(zips)).fetch())
    pico4, _ = _pico_pipeline(zips, 4, monkeypatch)
    pico8, store = _pico_pipeline(zips, 8, monkeypatch)

    linhas_votacao = CANDIDATOS_POR_UF * MUNICIPIOS_POR_UF  # linhas agregadas por UF
    with capsys.disabled():
        print(f"\n[tse memória, fixture sintética, {len(UFS)} UFs de {linhas_votacao} linhas de "
              f"votação agregadas] acumulado={acumulado / 1024:.0f} KiB; "
              f"pipeline por UF: 4 UFs={pico4 / 1024:.0f} KiB, 8 UFs={pico8 / 1024:.0f} KiB "
              f"(razão ao acumulado {pico8 / acumulado:.2f}); "
              f"acumulado/UF ~{acumulado / len(UFS) / 1024:.0f} KiB "
              f"(~{acumulado / (len(UFS) * linhas_votacao):.0f} B por linha de votação agregada, "
              f"contando candidatos e receitas da UF)")
    assert len(store.facts_by_tipo("candidatura")) == len(UFS) * CANDIDATOS_POR_UF
    assert pico8 < acumulado * 0.5   # solta cada UF: o pico não é a soma das 8
    assert pico8 < pico4 * 1.5       # dobrar as UFs não dobra o pico
