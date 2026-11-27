"""Modo nacional do pipeline (Onda 4): flags da CLI, repasse à fonte da Câmara e coerência.

Sem rede: a fonte da Câmara é um dublê que só registra o que recebeu.
"""
from __future__ import annotations

from typing import ClassVar

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
    chamadas: ClassVar[list[tuple[str, dict]]] = []

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


# ---------- --reusar-raw confere o escopo gravado no bruto ----------

JANELA = ("2025-01-01", "2025-03-31")


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    import sources.base
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def _bruto_em_disco(raw_dir, escopo: dict | None) -> None:
    import json
    arq = raw_dir / "camara" / f"camara_{JANELA[0]}_{JANELA[1]}.json"
    arq.parent.mkdir(parents=True)
    bruto = {"deputados": [{"id": 1}], "votacoes": []}
    if escopo is not None:
        bruto["_escopo"] = escopo
    arq.write_text(json.dumps(bruto), encoding="utf-8")


def _escopo(**kw) -> dict:
    return {"legislatura": 57, "legislatura_completa": False, "janela": list(JANELA),
            "fonte_votos": "api", "max_votacoes": None, **kw}


def _rodar_com_log(**kw):
    linhas: list[str] = []
    Pipeline(Store(":memory:"), Opcoes(fontes=("camara",), reusar_raw=True, **kw),
             registry={"camara": CamaraFalsa}, log=linhas.append).executar()
    return linhas


def _buscou() -> bool:
    return any(n == "fetch" for n, _ in CamaraFalsa.chamadas)


def test_bruto_de_mesmo_escopo_e_reaproveitado(raw_dir):
    _bruto_em_disco(raw_dir, _escopo())
    linhas = _rodar_com_log(nacional=True, max_votacoes=None)
    assert not _buscou() and any("reaproveitando" in ln for ln in linhas)


def test_bruto_de_amostra_com_teto_nao_alimenta_rodada_nacional(raw_dir):
    _bruto_em_disco(raw_dir, _escopo(max_votacoes=145))
    linhas = _rodar_com_log(nacional=True, max_votacoes=None)
    assert _buscou()
    assert any("não reaproveitado" in ln and "145" in ln for ln in linhas)
    assert not any("reaproveitando" in ln for ln in linhas)


def test_bruto_de_outra_fonte_de_votos_nao_e_reaproveitado(raw_dir):
    _bruto_em_disco(raw_dir, _escopo(fonte_votos="api"))
    linhas = _rodar_com_log(nacional=True, max_votacoes=None, fonte_votos="dump")
    assert _buscou() and any("fonte de votos" in ln for ln in linhas)


def test_bruto_dos_513_nao_serve_a_pedido_de_legislatura_completa(raw_dir):
    _bruto_em_disco(raw_dir, _escopo())
    _rodar_com_log(nacional=True, max_votacoes=None, legislatura_completa=True)
    assert _buscou()


def test_bruto_antigo_sem_escopo_e_recusado_no_nacional_com_aviso(raw_dir):
    _bruto_em_disco(raw_dir, None)
    linhas = _rodar_com_log(nacional=True, max_votacoes=None)
    assert _buscou() and any("sem registro de escopo" in ln for ln in linhas)


def test_bruto_antigo_sem_escopo_continua_servindo_a_amostra_mas_avisa(raw_dir):
    _bruto_em_disco(raw_dir, None)
    linhas = _rodar_com_log(uf="MG", amostra=1)
    assert not _buscou()
    assert any("sem registro de escopo" in ln for ln in linhas)
    assert any("reaproveitando" in ln for ln in linhas)


def test_sem_reusar_raw_o_pipeline_baixa_mesmo_com_bruto_compativel(raw_dir):
    _bruto_em_disco(raw_dir, _escopo())
    Pipeline(Store(":memory:"), Opcoes(fontes=("camara",), nacional=True, max_votacoes=None),
             registry={"camara": CamaraFalsa}, log=lambda _: None).executar()
    assert _buscou()


# ---------- sem escopo, só quem é deputado conhecido (candidatura, emenda, CEAP) ----------

def _cand(sq: str, nome: str) -> Fact:
    return Fact(tipo="candidatura", chave=sq, fonte="tse", id_oficial=sq, url=f"https://x/{sq}",
                atributos={"ano": 2022, "cpf": None, "nome": nome, "nome_urna": nome,
                           "cargo": "Deputado Federal", "uf": "MG", "partido": "PL"})


class TseFalso(Source):
    nome = "tse"

    def fetch(self, uf=None, ano=2022, conjuntos=(), reusar_raw=False):
        return {"ano": ano, "candidatos": [{}], "receitas": [], "votacao": []}

    def normalize(self, raw):
        # um candidato é o deputado "Dep Um"; o outro nunca foi deputado
        return [_cand("10", "Dep Um"), _cand("20", "Fulano Que Nunca Foi Deputado")] \
            if raw.get("candidatos") else []


class CguFalsa(Source):
    nome = "cgu"

    def fetch(self):
        return {}

    def normalize(self, raw):
        return [Fact(tipo="emenda", chave=c, fonte="cgu", id_oficial=c, url="https://x",
                     atributos={"autor_nome": n, "valor": 1.0})
                for c, n in (("e1", "Dep Um"), ("e2", "Autor Desconhecido"))]


class CeapFalsa(Source):
    nome = "ceap"

    def fetch(self, ano):
        return {"ano": ano}

    def normalize(self, raw):
        return [Fact(tipo="despesa_ceap", chave=f"d{i}", fonte="ceap", id_oficial=f"d{i}",
                     url="https://x", atributos={"deputado_id": i, "valor": 10.0,
                                                 "data": "2024-03-01"})
                for i in ("1", "2", "999")]


REGISTRO = {"camara": CamaraFalsa, "tse": TseFalso, "cgu": CguFalsa, "ceap": CeapFalsa}


def _rodar_fontes(fontes: tuple[str, ...], store: Store | None = None, **kw) -> Store:
    store = store or Store(":memory:")
    Pipeline(store, Opcoes(fontes=fontes, ano=2024, **kw), registry=REGISTRO,
             log=lambda _: None).executar()
    return store


def _chaves(store: Store, tipo: str) -> set[str]:
    return {f.chave for f in store.facts_by_tipo(tipo)}


def test_candidatura_de_quem_nao_e_deputado_nao_e_gravada_sem_escopo():
    store = _rodar_fontes(("camara", "tse"), nacional=True)
    assert _chaves(store, "candidatura") == {"10"}


def test_candidatura_de_quem_nao_e_deputado_nao_e_gravada_na_rodada_sem_escopo_e_sem_nacional():
    assert _chaves(_rodar_fontes(("camara", "tse")), "candidatura") == {"10"}


def test_candidatura_com_banco_sem_deputados_grava_tudo():
    store = _rodar_fontes(("tse",), nacional=True)
    assert _chaves(store, "candidatura") == {"10", "20"}


def test_candidatura_com_deputados_no_banco_filtra_na_rodada_so_tse():
    store = _rodar_fontes(("camara",), nacional=True)
    _rodar_fontes(("tse",), store, nacional=True)
    assert _chaves(store, "candidatura") == {"10"}


def test_emenda_sem_autor_deputado_nao_e_gravada_sem_escopo():
    store = _rodar_fontes(("camara", "cgu"), nacional=True)
    assert _chaves(store, "emenda") == {"e1"}


def test_despesa_de_quem_nao_e_deputado_e_descartada_na_rodada_camara_mais_ceap():
    store = _rodar_fontes(("camara", "ceap"), nacional=True)
    assert _chaves(store, "despesa_ceap") == {"d1", "d2"}


def test_so_ceap_com_banco_vazio_grava_tudo():
    assert _chaves(_rodar_fontes(("ceap",), nacional=True), "despesa_ceap") == {"d1", "d2", "d999"}


def test_so_ceap_com_deputados_no_banco_filtra():
    store = _rodar_fontes(("camara",), nacional=True)
    _rodar_fontes(("ceap",), store, nacional=True)
    assert _chaves(store, "despesa_ceap") == {"d1", "d2"}


# ---------- aviso de bruto recusado só quando --reusar-raw foi pedido ----------

def test_sem_reusar_raw_bruto_incompativel_nao_gera_aviso(raw_dir):
    _bruto_em_disco(raw_dir, _escopo(max_votacoes=145))
    linhas: list[str] = []
    Pipeline(Store(":memory:"), Opcoes(fontes=("camara",), nacional=True, max_votacoes=None,
                                       detalhar_deputados=True),
             registry={"camara": CamaraFalsa}, log=linhas.append).executar()
    assert not any("não reaproveitado" in ln for ln in linhas)
