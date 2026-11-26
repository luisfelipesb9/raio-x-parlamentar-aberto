"""Dump anual oficial da Câmara (votacoes, votacoesVotos, votacoesOrientacoes) -> bruto da fonte.

As fixtures `camara_dump_*_2025.csv` têm o cabeçalho REAL dos arquivos de 2025 (baixado com
`curl -r 0-3500` em 2026-11-26): UTF-8 com BOM, separador `;`, tudo entre aspas. As linhas são
poucas e de valores construídos (ids reais do formato, placares e votos inventados) para cobrir:
votação nominal e simbólica de Plenário, votação de comissão com votos (não pode entrar), voto
de votação que não está no arquivo de votações e data fora da janela.

Princípio ético: votação simbólica NÃO vira voto individual.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sources.camara.dumps import ler_csv, url_dump, votacoes_do_dump
from sources.camara.source import CamaraSource

FIX = Path(__file__).parent / "fixtures"
VOTACOES, VOTOS, ORIENTACOES = (FIX / f"camara_dump_{n}_2025.csv"
                                for n in ("votacoes", "votos", "orientacoes"))
Q1 = ("2025-01-01", "2025-03-31")


def _dump(ini="2025-01-01", fim="2025-12-31", **kw):
    return votacoes_do_dump([VOTACOES], [VOTOS], [ORIENTACOES], ini, fim, **kw)


def _por_id(votacoes):
    return {v["id"]: v for v in votacoes}


# ---------- leitura do CSV ----------

def test_url_do_dump_segue_o_padrao_oficial():
    assert url_dump("votacoesVotos", 2025) == (
        "https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/votacoesVotos-2025.csv")


def test_ler_csv_tira_o_bom_e_respeita_aspas_e_quebra_de_linha_no_campo():
    linhas = list(ler_csv(VOTACOES))
    assert next(iter(linhas[0])) == "id"  # o BOM não pode ficar grudado no nome da 1ª coluna
    assert linhas[0]["id"] == "2458405-38"
    assert "\n" in linhas[0]["descricao"] and '"de líderes"' in linhas[0]["descricao"]
    assert len(linhas) == 5


def test_ler_csv_e_um_gerador_nao_carrega_o_arquivo_inteiro():
    import types
    assert isinstance(ler_csv(VOTACOES), types.GeneratorType)


# ---------- filtros: só Plenário, só a janela ----------

def test_so_plenario_dentro_da_janela_em_ordem_de_registro():
    assert [v["id"] for v in _dump(*Q1)] == ["2458405-38", "2458405-40", "2442848-52"]


def test_janela_do_ano_inclui_a_votacao_de_novembro_e_continua_sem_comissao():
    assert [v["id"] for v in _dump()] == ["2458405-38", "2458405-40", "2442848-52", "106701-223"]


def test_max_votacoes_corta_depois_de_ordenar():
    assert [v["id"] for v in _dump(max_votacoes=2)] == ["2458405-38", "2458405-40"]


def test_max_votacoes_zero_nao_devolve_nada():
    assert _dump(max_votacoes=0) == []


def test_limites_da_janela_sao_inclusivos():
    assert [v["id"] for v in _dump("2025-03-27", "2025-03-27")] == ["2442848-52"]


# ---------- votos: só votação nominal de Plenário ----------

def test_votacao_nominal_traz_os_votos_no_formato_da_api():
    v = _por_id(_dump(*Q1))["2442848-52"]
    assert v["_votos"] == [{"tipoVoto": "Sim", "deputado_": {"id": 204379}},
                           {"tipoVoto": "Não", "deputado_": {"id": 220714}},
                           {"tipoVoto": "Abstenção", "deputado_": {"id": 221328}}]


def test_votacao_simbolica_nao_tem_voto_individual():
    v = _por_id(_dump(*Q1))
    assert v["2458405-40"]["_votos"] == []
    assert v["2458405-38"]["_votos"] == []


def test_voto_de_comissao_nao_entra_em_lugar_nenhum():
    todas = _dump()
    assert "2440085-41" not in _por_id(todas)
    assert not any(vt["deputado_"]["id"] == 220714 and v["id"] == "2440085-41"
                   for v in todas for vt in v["_votos"])


def test_voto_de_votacao_ausente_do_arquivo_de_votacoes_e_ignorado():
    assert all(v["id"] != "9999999-1" for v in _dump())
    assert sum(len(v["_votos"]) for v in _dump()) == 3 + 2  # as duas nominais de Plenário


# ---------- orientações ----------

def test_orientacoes_ganham_os_nomes_da_api_e_o_governo_e_achado_pelo_normalize():
    v = _por_id(_dump(*Q1))
    assert v["2442848-52"]["_orientacoes"] == [
        {"siglaPartidoBloco": "Governo", "orientacaoVoto": "Sim"},
        {"siglaPartidoBloco": "PL", "orientacaoVoto": "Não"}]
    assert v["2458405-40"]["_orientacoes"] == []
    fatos = {(f.tipo, f.chave): f for f in
             CamaraSource(client=object()).normalize({"votacoes": _dump(*Q1)})}
    assert fatos[("votacao", "2442848-52")].atributos["orientacao_governo"] == "Sim"
    assert fatos[("votacao", "2458405-38")].atributos["orientacao_governo"] == "Liberado"


def test_orientacao_de_comissao_nao_vaza_para_o_plenario():
    assert all(o["siglaPartidoBloco"] != "Governo" or v["id"] != "2440085-41"
               for v in _dump() for o in v["_orientacoes"])


# ---------- equivalência com o caminho da API ----------

def test_mesmos_fatos_que_a_api_produziria_para_a_mesma_votacao():
    """O dump mapeia para os mesmos `Fact` (tipos votacao e voto), sem mudar o contrato."""
    pela_api = {"votacoes": [{
        "id": "2442848-52", "uri": "https://dadosabertos.camara.leg.br/api/v2/votacoes/2442848-52",
        "data": "2025-03-27", "descricao": "Aprovada a Emenda nº 3. Sim: 3; Não: 1.",
        "siglaOrgao": "PLEN",
        "_votos": [{"tipoVoto": "Sim", "deputado_": {"id": 204379}},
                   {"tipoVoto": "Não", "deputado_": {"id": 220714}},
                   {"tipoVoto": "Abstenção", "deputado_": {"id": 221328}}],
        "_orientacoes": [{"siglaPartidoBloco": "Governo", "orientacaoVoto": "Sim"},
                         {"siglaPartidoBloco": "PL", "orientacaoVoto": "Não"}]}]}
    pelo_dump = {"votacoes": [v for v in _dump(*Q1) if v["id"] == "2442848-52"]}
    src = CamaraSource(client=object())

    def sem_hora(raw):  # `coletado_em` é a hora da execução
        return [f.model_dump(exclude={"coletado_em"}) for f in src.normalize(raw)]

    assert sem_hora(pelo_dump) == sem_hora(pela_api)


def test_normalize_do_dump_marca_simbolica_como_nao_nominal_e_sem_voto():
    fatos = CamaraSource(client=object()).normalize({"votacoes": _dump(*Q1)})
    votacoes = {f.chave: f for f in fatos if f.tipo == "votacao"}
    assert votacoes["2458405-40"].atributos["nominal"] is False
    assert votacoes["2442848-52"].atributos["nominal"] is True
    votos = [f for f in fatos if f.tipo == "voto"]
    assert {f.atributos["votacao_id"] for f in votos} == {"2442848-52"}
    assert {f.atributos["deputado_id"] for f in votos} == {"204379", "220714", "221328"}


# ---------- vários arquivos (ano que vira) ----------

def test_aceita_mais_de_um_arquivo_por_conjunto(tmp_path):
    outra = tmp_path / "votacoes2.csv"
    texto = VOTACOES.read_text(encoding="utf-8-sig").splitlines()
    outra.write_text("﻿" + "\n".join([texto[0], texto[0].replace("id", "x")[:0]]),
                     encoding="utf-8")  # só o cabeçalho: ano sem votações
    v = votacoes_do_dump([VOTACOES, outra], [VOTOS], [ORIENTACOES], *Q1)
    assert [x["id"] for x in v] == ["2458405-38", "2458405-40", "2442848-52"]


def test_janela_invertida_e_erro():
    with pytest.raises(ValueError, match="início"):
        _dump("2025-04-01", "2025-03-31")
