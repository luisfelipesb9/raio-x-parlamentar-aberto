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


# ---------- dublê da Câmara: registra o que a Pipeline passa ----------

def _fato(tipo: str, chave: str, **atributos) -> Fact:
    return Fact(tipo=tipo, chave=chave, fonte="camara_api_v2", id_oficial=chave,
                url=f"https://x/{tipo}/{chave}", atributos=atributos)


class CamaraFalsa(Source):
    nome = "camara"
    chamadas: list[tuple[str, dict]] = []

    def fetch(self, legislatura=57, data_inicio="x", data_fim="y", max_votacoes=None,
              detalhar_deputados=False, legislatura_completa=False, retomar=True,
              fonte_votos="api", reusar_dumps=False):
        self.chamadas.append(("fetch", {
            "max_votacoes": max_votacoes, "legislatura_completa": legislatura_completa,
            "retomar": retomar, "fonte_votos": fonte_votos, "reusar_dumps": reusar_dumps,
            "detalhar_deputados": detalhar_deputados}))
        return {"deputados": [{"id": 1}, {"id": 2}]}

    def fetch_proposicoes(self, data_inicio, data_fim, deputado_ids=None, siglas_tipo=None,
                          max_proposicoes=None, retomar=True):
        self.chamadas.append(("props", {"deputado_ids": deputado_ids, "retomar": retomar,
                                        "max_proposicoes": max_proposicoes}))
        return {"proposicoes": [], "erros": []}

    def normalize(self, raw):
        if "proposicoes" in raw:
            return []
        # 999 votou, mas não está entre os deputados da lista (ex-deputado / suplente que saiu)
        return ([_fato("deputado", "1", nome="Dep Um", uf="MG", partido="PL"),
                 _fato("deputado", "2", nome="Dep Dois", uf="SP", partido="PT"),
                 _fato("votacao", "v1", nominal=True)]
                + [_fato("voto", f"v1:{i}", votacao_id="v1", deputado_id=i, voto="Sim")
                   for i in ("1", "2", "999")]
                + [_fato("autoria", f"p1:{i}:autor", proposicao_id="p1", deputado_id=i,
                         papel="autor") for i in ("1", "999")])


@pytest.fixture(autouse=True)
def _limpa_chamadas():
    CamaraFalsa.chamadas = []


def _rodar(**kw):
    store = Store(":memory:")
    rel = Pipeline(store, Opcoes(fontes=("camara",), **kw), registry={"camara": CamaraFalsa},
                   log=lambda _: None).executar()
    return store, rel


def _chamada(nome: str) -> dict:
    return next(kw for n, kw in CamaraFalsa.chamadas if n == nome)


# ---------- as opções chegam à fonte ----------

def test_opcoes_da_camara_chegam_ao_fetch():
    _rodar(legislatura_completa=True, fonte_votos="dump", reusar_dumps=True, retomar=False)
    c = _chamada("fetch")
    assert (c["legislatura_completa"], c["fonte_votos"], c["reusar_dumps"], c["retomar"]) == (
        True, "dump", True, False)


def test_sem_opcoes_o_fetch_recebe_os_padroes():
    _rodar()
    c = _chamada("fetch")
    assert (c["legislatura_completa"], c["fonte_votos"], c["reusar_dumps"], c["retomar"]) == (
        False, "api", False, True)


def test_retomar_chega_a_coleta_de_proposicoes():
    _rodar(incluir_proposicoes=True, retomar=False)
    assert _chamada("props")["retomar"] is False


# ---------- modo nacional: proposições da janela toda e sem teto ----------

def test_nacional_pede_as_proposicoes_da_janela_sem_filtrar_autores_e_sem_teto():
    _rodar(nacional=True, incluir_proposicoes=True, max_proposicoes=None)
    c = _chamada("props")
    assert c["deputado_ids"] is None and c["max_proposicoes"] is None


def test_amostra_continua_pedindo_so_os_autores_do_escopo_com_teto():
    _rodar(uf="MG", amostra=1, incluir_proposicoes=True)
    c = _chamada("props")
    assert c["deputado_ids"] == ["1"] and c["max_proposicoes"] == 300


# ---------- amostra continua respeitada ----------

def test_amostra_de_um_deputado_grava_so_ele():
    store, rel = _rodar(uf="MG", amostra=1)
    assert {f.chave for f in store.facts_by_tipo("deputado")} == {"1"}
    assert rel["escopo_deputados"] == 1


# ---------- votos de quem não está entre os deputados do escopo ----------

def test_voto_e_autoria_de_quem_nao_esta_na_lista_de_deputados_nao_entram_sem_escopo():
    store, _ = _rodar(nacional=True)
    assert {f.atributos["deputado_id"] for f in store.facts_by_tipo("voto")} == {"1", "2"}
    assert {f.atributos["deputado_id"] for f in store.facts_by_tipo("autoria")} == {"1"}


def test_orfaos_tambem_ficam_de_fora_na_rodada_sem_escopo_e_sem_nacional():
    store, _ = _rodar()
    assert {f.atributos["deputado_id"] for f in store.facts_by_tipo("voto")} == {"1", "2"}


def test_rodada_nacional_apaga_o_voto_orfao_que_uma_rodada_antiga_deixou():
    store = Store(":memory:")
    store.upsert_facts([_fato("voto", "v1:999", votacao_id="v1", deputado_id="999", voto="Sim")])
    Pipeline(store, Opcoes(fontes=("camara",), nacional=True), registry={"camara": CamaraFalsa},
             log=lambda _: None).executar()
    assert {f.atributos["deputado_id"] for f in store.facts_by_tipo("voto")} == {"1", "2"}
