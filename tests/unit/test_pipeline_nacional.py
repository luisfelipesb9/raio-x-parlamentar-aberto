"""Modo nacional do pipeline (Onda 4): flags da CLI, repasse à fonte da Câmara e coerência.

Sem rede: a fonte da Câmara é um dublê que só registra o que recebeu.
"""
from __future__ import annotations

import pytest

from contracts import Fact
from ingest.pipeline import Opcoes, Pipeline, opcoes_da_cli
from repo.store import Store
from sources.base import Source


def _opcoes(*args: str) -> Opcoes:
    return opcoes_da_cli(list(args))[0]


# ---------- flags da CLI ----------

def test_padrao_da_cli_continua_o_do_modo_amostra():
    o = _opcoes("--fontes", "camara")
    assert (o.nacional, o.legislatura_completa, o.fonte_votos, o.reusar_dumps, o.retomar) == (
        False, False, "api", False, True)
    assert (o.max_votacoes, o.max_proposicoes) == (30, 300)


def test_flags_da_camara_chegam_nas_opcoes():
    o = _opcoes("--legislatura-completa", "--fonte-votos", "dump", "--reusar-dumps",
                "--sem-retomar")
    assert (o.legislatura_completa, o.fonte_votos, o.reusar_dumps, o.retomar) == (
        True, "dump", True, False)


def test_retomar_explicito_e_o_padrao():
    assert _opcoes("--retomar").retomar is True


def test_fonte_de_votos_desconhecida_e_recusada_na_cli():
    with pytest.raises(SystemExit):
        _opcoes("--fonte-votos", "csv")


def test_nacional_tira_os_tetos_do_modo_amostra_e_nao_restringe_deputados():
    o = _opcoes("--nacional", "--fontes", "camara,ceap,tse", "--anos-ceap", "2023,2024")
    assert o.nacional is True
    assert (o.uf, o.amostra) == (None, None)
    assert (o.max_votacoes, o.max_proposicoes) == (None, None)
    assert o.anos_ceap == (2023, 2024)


def test_nacional_respeita_teto_dado_explicitamente():
    o = _opcoes("--nacional", "--max-votacoes", "100", "--max-proposicoes", "500")
    assert (o.max_votacoes, o.max_proposicoes) == (100, 500)


@pytest.mark.parametrize("restricao", [["--amostra", "20"], ["--uf", "MG"]])
def test_nacional_com_amostra_ou_uf_e_contradicao(restricao):
    with pytest.raises(SystemExit):
        _opcoes("--nacional", *restricao)


def test_amostra_continua_respeitada_sem_nacional():
    o = _opcoes("--uf", "MG", "--amostra", "20", "--max-votacoes", "145")
    assert (o.nacional, o.uf, o.amostra, o.max_votacoes) == (False, "MG", 20, 145)


# ---------- a Pipeline recusa a contradição também fora da CLI ----------

def test_pipeline_recusa_nacional_com_escopo():
    with pytest.raises(ValueError, match="nacional"):
        Pipeline(Store(":memory:"), Opcoes(fontes=("camara",), nacional=True, amostra=20),
                 registry={}, log=lambda _: None).executar()


def test_pipeline_recusa_fonte_de_votos_desconhecida():
    with pytest.raises(ValueError, match="fonte_votos"):
        Pipeline(Store(":memory:"), Opcoes(fontes=("camara",), fonte_votos="csv"),
                 registry={}, log=lambda _: None).executar()
