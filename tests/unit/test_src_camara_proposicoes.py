"""CamaraSource — proposicao + autoria (autor / coautor / relator).

Fixtures REAIS (API v2 da Câmara, recortadas): PEC 2/2023, PL 719/2024 e PL 2338/2023.
Casos de borda sem equivalente real são derivados de uma entrada real, alterando só o campo
testado (indicado no teste).
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import httpx
import pytest

import sources.base
from sources.camara.source import FONTE, CamaraSource

FIX = Path(__file__).parent / "fixtures"
PEC, PL719, PL2338 = 2350490, 2420536, 2487262
RELATOR_2338 = "160527"  # Aguinaldo Ribas


def _fx(nome: str) -> dict:
    return json.loads((FIX / nome).read_text(encoding="utf-8"))


def _resp(corpo: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=corpo)


class FakeApi:
    """Serve as fixtures reais pelo transporte do httpx e registra o que foi pedido."""

    def __init__(self, erro_em: set[str] = frozenset()):
        self.pedidos: list[httpx.Request] = []
        self.erro_em = erro_em
        self.client = httpx.Client(transport=httpx.MockTransport(self._handler))

    def _handler(self, req: httpx.Request) -> httpx.Response:
        self.pedidos.append(req)
        path = req.url.path.removeprefix("/api/v2")
        if path == "/proposicoes":
            pag = req.url.params.get("pagina", "1")
            return _resp(_fx(f"camara_proposicoes_p{pag}.json"))
        m = re.fullmatch(r"/proposicoes/(\d+)/(autores|tramitacoes)", path)
        if m:
            pid, recurso = m.groups()
            if f"{pid}/{recurso}" in self.erro_em:
                return _resp({"status": 500}, 500)
            if recurso == "autores":
                return _resp(_fx(f"camara_autores_{pid}.json"))
            if pid == str(PL2338):
                return _resp(_fx("camara_tramitacoes_2487262.json"))
            return _resp({"dados": [], "links": []})
        if path == "/deputados":
            return _resp({"dados": [
                {"id": 62881, "nome": "Dalton Formoso", "siglaPartido": "PP", "siglaUf": "CE",
                 "uri": "u"},
                {"id": 66828, "nome": "Fausto Pinato", "siglaPartido": "PP", "siglaUf": "SP",
                 "uri": "u2"}], "links": []})
        m = re.fullmatch(r"/deputados/(\d+)", path)
        if m:
            if f"deputados/{m.group(1)}" in self.erro_em:
                return _resp({"status": 500}, 500)
            if m.group(1) == "62881":
                return _resp(_fx("camara_deputado_62881.json"))
            return _resp({"dados": {"id": int(m.group(1)), "nomeCivil": "SEM CPF"}, "links": []})
        if path == "/votacoes":
            return _resp({"dados": [], "links": []})
        return _resp({"erro": path}, 404)

    def paths(self, prefixo: str = "") -> list[str]:
        return [r.url.path.removeprefix("/api/v2") for r in self.pedidos
                if r.url.path.removeprefix("/api/v2").startswith(prefixo)]


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def _fonte(api: FakeApi) -> CamaraSource:
    # sem esperar de verdade: o FakeApi devolve 500 de propósito e a fonte tenta de novo
    return CamaraSource(client=api.client, pausa=0, dormir=lambda s: None)


@pytest.fixture
def raw_real(raw_dir) -> dict:
    """Bruto produzido pelo próprio fetch sobre as fixtures reais (fetch → normalize)."""
    api = FakeApi()
    return _fonte(api).fetch_proposicoes("2023-01-01", "2025-12-31", deputado_ids=["62881"])


def _fatos(raw: dict):
    return CamaraSource(client=object()).normalize(raw)


def _por(facts, tipo):
    return {f.chave: f for f in facts if f.tipo == tipo}


# ======================= fetch_proposicoes =======================

def test_fetch_descobre_por_deputado_pagina_e_deduplica(raw_dir):
    api = FakeApi()
    out = _fonte(api).fetch_proposicoes("2023-01-01", "2025-12-31",
                                        deputado_ids=["62881", "66828"])
    assert [p["id"] for p in out["proposicoes"]] == [PEC, PL719, PL2338]
    # autores/tramitações de cada proposição pedidos 1x, mesmo com 2 deputados e 2 páginas
    assert sorted(api.paths("/proposicoes/")) == sorted(
        f"/proposicoes/{i}/{r}" for i in (PEC, PL719, PL2338) for r in ("autores", "tramitacoes"))
    listas = [r for r in api.pedidos if r.url.path.endswith("/proposicoes")]
    assert {r.url.params.get("idDeputadoAutor") for r in listas} == {"62881", "66828"}
    p = listas[0].url.params
    assert p["dataApresentacaoInicio"] == "2023-01-01" and p["dataApresentacaoFim"] == "2025-12-31"
    assert p["itens"] == "100"  # limite da API
    assert out["erros"] == []


def test_fetch_sem_deputados_lista_a_janela_inteira_e_filtra_tipo(raw_dir):
    api = FakeApi()
    _fonte(api).fetch_proposicoes("2023-01-01", "2025-12-31", siglas_tipo=["PL", "PEC"])
    lista = next(r for r in api.pedidos if r.url.path.endswith("/proposicoes"))
    assert "idDeputadoAutor" not in lista.url.params
    assert lista.url.params.get_list("siglaTipo") == ["PL", "PEC"]


def test_fetch_guarda_so_o_necessario_das_tramitacoes(raw_real):
    p = {x["id"]: x for x in raw_real["proposicoes"]}
    assert p[PL719]["_relatores"] == []
    rel = p[PL2338]["_relatores"]
    assert [r["sequencia"] for r in rel] == [36, 39, 259, 364]  # só linhas com relator
    assert set(rel[0]) == {"sequencia", "siglaOrgao", "uriUltimoRelator"}
    assert rel[0]["siglaOrgao"] == "PL233823"
    assert p[PL2338]["_autores"][0]["nome"].startswith("Senado Federal")


def test_fetch_max_proposicoes_para_antes_de_buscar_autores_das_demais(raw_dir):
    api = FakeApi()
    out = _fonte(api).fetch_proposicoes("2023-01-01", "2025-12-31", deputado_ids=["62881"],
                                        max_proposicoes=2)
    assert [p["id"] for p in out["proposicoes"]] == [PEC, PL719]
    assert not any(str(PL2338) in p for p in api.paths("/proposicoes/"))


def test_fetch_erro_http_numa_proposicao_e_registrado_e_nao_derruba_o_resto(raw_dir):
    api = FakeApi(erro_em={f"{PL719}/autores"})
    out = _fonte(api).fetch_proposicoes("2023-01-01", "2025-12-31", deputado_ids=["62881"])
    assert [p["id"] for p in out["proposicoes"]] == [PEC, PL2338]  # sem dado parcial
    assert [e["id"] for e in out["erros"]] == [PL719]
    assert "500" in out["erros"][0]["erro"]


def test_fetch_salva_bruto_em_data_raw(raw_dir):
    _fonte(FakeApi()).fetch_proposicoes("2023-01-01", "2025-12-31", deputado_ids=["62881"])
    salvo = raw_dir / "camara" / "camara_proposicoes_2023-01-01_2025-12-31.json"
    assert json.loads(salvo.read_text(encoding="utf-8"))["proposicoes"]


def test_fetch_padrao_nao_chama_proposicoes_e_opt_in_acrescenta(raw_dir):
    api = FakeApi()
    base = _fonte(api).fetch(max_votacoes=0)
    assert set(base) == {"deputados", "votacoes", "_escopo"}  # comportamento anterior intacto
    assert api.paths("/proposicoes") == []

    api2 = FakeApi()
    comp = _fonte(api2).fetch(max_votacoes=0, incluir_proposicoes=True,
                              data_inicio="2023-01-01", data_fim="2025-12-31")
    assert set(comp) == {"deputados", "votacoes", "proposicoes", "_escopo"}
    assert [p["id"] for p in comp["proposicoes"]] == [PEC, PL719, PL2338]
    ids = {r.url.params.get("idDeputadoAutor") for r in api2.pedidos
           if r.url.path.endswith("/proposicoes")}
    assert ids == {"62881", "66828"}  # deputados vêm da lista da própria fetch


# ======================= normalize: proposicao =======================

def test_proposicao_tem_atributos_exatos_do_contrato(raw_real):
    f = _por(_fatos(raw_real), "proposicao")[str(PL719)]
    assert f.atributos == {
        "sigla_tipo": "PL", "numero": 719, "ano": 2024,
        "ementa": raw_real["proposicoes"][1]["ementa"], "data": "2024-03-12"}
    assert f.fonte == FONTE == "camara_api_v2"
    assert f.id_oficial == str(PL719)
    assert f.url == f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{PL719}"


def test_data_vem_da_apresentacao_nao_do_ano_da_numeracao(raw_real):
    # PL 2338/2023 chegou à Câmara em 2025
    f = _por(_fatos(raw_real), "proposicao")[str(PL2338)]
    assert (f.atributos["ano"], f.atributos["data"]) == (2023, "2025-03-17")


def test_data_ausente_vira_none(raw_real):
    p = copy.deepcopy(raw_real)  # derivado: remove dataApresentacao de uma proposição real
    del p["proposicoes"][0]["dataApresentacao"]
    assert _por(_fatos(p), "proposicao")[str(PEC)].atributos["data"] is None


# ======================= normalize: autoria =======================

def test_primeiro_assinante_proponente_e_autor_demais_sao_coautores(raw_real):
    aut = _por(_fatos(raw_real), "autoria")
    assert aut[f"{PL719}:178992:autor"].atributos == {
        "proposicao_id": str(PL719), "deputado_id": "178992", "papel": "autor"}
    for dep in ("204416", "204506", "220626"):
        assert aut[f"{PL719}:{dep}:coautor"].atributos["papel"] == "coautor"
    assert f"{PL719}:178992:coautor" not in aut


def test_autoria_rastreavel_para_a_proposicao(raw_real):
    f = _por(_fatos(raw_real), "autoria")[f"{PL719}:178992:autor"]
    assert f.fonte == "camara_api_v2"
    assert f.id_oficial == str(PL719)
    assert f.url == f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{PL719}"


def test_apoiadores_de_pec_proponente_zero_nao_viram_coautoria(raw_real):
    aut = _por(_fatos(raw_real), "autoria")
    da_pec = {k for k in aut if k.startswith(f"{PEC}:")}
    assert da_pec == {f"{PEC}:74856:autor", f"{PEC}:141450:coautor",
                      f"{PEC}:160512:coautor", f"{PEC}:204515:coautor"}
    assert not any(":204379:" in k for k in da_pec)  # Aníbal Fontoura: apoiador (proponente=0)


def test_autor_que_nao_e_deputado_nao_gera_autoria(raw_real):
    # PL 2338/2023: autor é "Senado Federal - Rogerio Pedrosa" (/orgaos/78)
    aut = [f for f in _fatos(raw_real)
           if f.tipo == "autoria" and f.atributos["proposicao_id"] == str(PL2338)
           and f.atributos["papel"] != "relator"]
    assert aut == []


def test_primeiro_assinante_sem_proponente_nao_e_autor(raw_real):
    p = copy.deepcopy(raw_real)  # derivado: PL 719/2024, autor 1 passa a proponente=0
    for a in p["proposicoes"][1]["_autores"]:
        if a["ordemAssinatura"] == 1:
            a["proponente"] = 0
    aut = _por(_fatos(p), "autoria")
    assert not any(k.startswith(f"{PL719}:178992:") for k in aut)


def test_deputado_repetido_nos_autores_gera_uma_so_autoria(raw_real):
    p = copy.deepcopy(raw_real)  # derivado: duplica a lista de autores
    prop = p["proposicoes"][1]
    prop["_autores"] = prop["_autores"] + prop["_autores"]
    chaves = [f.chave for f in _fatos(p) if f.tipo == "autoria"]
    assert len(chaves) == len(set(chaves))


def test_proposicao_sem_autores_no_bruto_gera_so_a_proposicao(raw_real):
    p = copy.deepcopy(raw_real)
    for prop in p["proposicoes"]:
        prop.pop("_autores")
        prop.pop("_relatores")
    tipos = {f.tipo for f in _fatos(p)}
    assert tipos == {"proposicao"}


# ======================= normalize: relator =======================

def test_relator_vem_de_uri_ultimo_relator_com_orgao_da_designacao(raw_real):
    rel = {k: f for k, f in _por(_fatos(raw_real), "autoria").items() if k.endswith(":relator")}
    assert list(rel) == [f"{PL2338}:{RELATOR_2338}:relator"]  # 4 tramitações, 1 fato
    f = rel[f"{PL2338}:{RELATOR_2338}:relator"]
    assert f.atributos == {"proposicao_id": str(PL2338), "deputado_id": RELATOR_2338,
                           "papel": "relator", "orgao": "PL233823"}  # 1ª aparição, não MESA/CE
    assert f.id_oficial == str(PL2338)


def test_dois_relatores_distintos_geram_dois_fatos(raw_real):
    p = copy.deepcopy(raw_real)  # derivado: a última tramitação passa a outro relator
    p["proposicoes"][2]["_relatores"][-1].update(
        siglaOrgao="CCJC", uriUltimoRelator="https://dadosabertos.camara.leg.br/api/v2/deputados/74856")
    rel = {f.chave: f for f in _fatos(p) if f.atributos.get("papel") == "relator"}
    assert set(rel) == {f"{PL2338}:{RELATOR_2338}:relator", f"{PL2338}:74856:relator"}
    assert rel[f"{PL2338}:74856:relator"].atributos["orgao"] == "CCJC"


def test_uri_de_relator_que_nao_e_deputado_e_ignorada(raw_real):
    p = copy.deepcopy(raw_real)  # derivado: URI sem /deputados/{id}
    for r in p["proposicoes"][2]["_relatores"]:
        r["uriUltimoRelator"] = "https://dadosabertos.camara.leg.br/api/v2/orgaos/78"
    assert [f for f in _fatos(p) if f.atributos.get("papel") == "relator"] == []


def test_autor_que_tambem_relata_tem_dois_fatos_distintos(raw_real):
    p = copy.deepcopy(raw_real)  # derivado: relator do PL 719 = seu próprio autor
    p["proposicoes"][1]["_relatores"] = [{
        "sequencia": 5, "siglaOrgao": "CCJC",
        "uriUltimoRelator": "https://dadosabertos.camara.leg.br/api/v2/deputados/178992"}]
    chaves = {f.chave for f in _fatos(p) if f.tipo == "autoria"}
    assert {f"{PL719}:178992:autor", f"{PL719}:178992:relator"} <= chaves


# ======================= regressão =======================

def test_normalize_sem_proposicoes_continua_igual():
    raw = {"deputados": [{"id": 1, "nome": "Fulana", "siglaPartido": "XX", "siglaUf": "MG",
                          "uri": "u"}], "votacoes": []}
    assert [f.tipo for f in _fatos(raw)] == ["deputado"]


# ======================= deputado: cpf e nome_civil (GET /deputados/{id}) =======================
# CPF da fixture camara_deputado_62881.json é SINTÉTICO (formato real da API, valor fictício).

CPF_SINTETICO = "11144477735"


def _detalhes(api: FakeApi) -> list[str]:
    return [p for p in api.paths("/deputados/")]


def test_detalhar_true_busca_cpf_e_nome_civil_de_todos_do_escopo(raw_dir):
    api = FakeApi()
    raw = _fonte(api).fetch(max_votacoes=0, detalhar_deputados=True)
    assert sorted(_detalhes(api)) == ["/deputados/62881", "/deputados/66828"]
    por_id = {d["id"]: d for d in raw["deputados"]}
    assert por_id[62881]["_detalhe"] == {"cpf": CPF_SINTETICO,
                                         "nomeCivil": "FRANCISCO DALTON BASTOS FORMOSO"}
    assert por_id[66828]["_detalhe"] == {"cpf": None, "nomeCivil": "SEM CPF"}


def test_detalhar_por_lista_so_chama_ids_pedidos_que_estao_no_escopo(raw_dir):
    api = FakeApi()
    raw = _fonte(api).fetch(max_votacoes=0, detalhar_deputados=[62881, "999"])
    assert _detalhes(api) == ["/deputados/62881"]  # 999 está fora do escopo: ignorado
    assert [("_detalhe" in d) for d in raw["deputados"]] == [True, False]


def test_padrao_nao_chama_detalhe_do_deputado(raw_dir):
    api = FakeApi()
    raw = _fonte(api).fetch(max_votacoes=0)
    assert _detalhes(api) == []
    assert all("_detalhe" not in d for d in raw["deputados"])


def test_detalhar_respeita_a_pausa_entre_chamadas(raw_dir, monkeypatch):
    dormiu: list[float] = []
    monkeypatch.setattr("sources.camara.source.time.sleep", dormiu.append)
    api = FakeApi()
    CamaraSource(client=api.client, pausa=0.7).fetch(max_votacoes=0, detalhar_deputados=[62881])
    # 1 da listagem de deputados + 1 do detalhe (sem votações pedidas, nem listagem delas)
    assert dormiu.count(0.7) == 2


def test_erro_http_no_detalhe_nao_derruba_e_fica_registrado(raw_dir):
    api = FakeApi(erro_em={"deputados/62881"})
    raw = _fonte(api).fetch(max_votacoes=0, detalhar_deputados=True)
    por_id = {d["id"]: d for d in raw["deputados"]}
    assert "_detalhe" not in por_id[62881] and "_detalhe" in por_id[66828]
    assert [e["id"] for e in raw["deputados_erros"]] == [62881]
    assert "500" in raw["deputados_erros"][0]["erro"]


def test_normalize_deputado_ganha_cpf_e_nome_civil(raw_dir):
    api = FakeApi()
    raw = _fonte(api).fetch(max_votacoes=0, detalhar_deputados=[62881])
    por = _por(_fatos(raw), "deputado")
    assert por["62881"].atributos == {
        "nome": "Dalton Formoso", "partido": "PP", "uf": "CE", "foto": None,
        "cpf": CPF_SINTETICO, "nome_civil": "FRANCISCO DALTON BASTOS FORMOSO"}
    assert set(por["66828"].atributos) == {"nome", "partido", "uf", "foto"}  # sem detalhe


@pytest.mark.parametrize("bruto,esperado", [
    ("111.444.777-35", CPF_SINTETICO),   # máscara some
    (CPF_SINTETICO, CPF_SINTETICO),
    ("***444777**", None),               # mascarado/incompleto não é CPF
    ("123", None),
    ("", None),
    (None, None),
])
def test_cpf_so_digitos_e_so_se_tiver_11(bruto, esperado):
    raw = {"deputados": [{"id": 1, "nome": "X", "siglaPartido": "P", "siglaUf": "MG", "uri": "u",
                          "_detalhe": {"cpf": bruto, "nomeCivil": "  FULANO DE TAL "}}]}
    at = _fatos(raw)[0].atributos
    assert at.get("cpf") == esperado
    assert ("cpf" in at) is (esperado is not None)
    assert at["nome_civil"] == "FULANO DE TAL"


def test_nome_civil_vazio_nao_gera_atributo():
    raw = {"deputados": [{"id": 1, "nome": "X", "_detalhe": {"cpf": None, "nomeCivil": ""}}]}
    assert "nome_civil" not in _fatos(raw)[0].atributos


def test_deputado_repetido_na_listagem_gera_uma_so_chamada_de_detalhe(raw_dir):
    # a API lista ~200 deputados 2x (mudança de partido/suplência): 877 linhas, 648 ids
    api = FakeApi()
    lista = [{"id": 62881, "nome": "Dalton Formoso"}, {"id": 62881, "nome": "Dalton Formoso"}]
    erros = _fonte(api)._detalhar_deputados(lista, True)
    assert erros == []
    assert _detalhes(api) == ["/deputados/62881"]
    assert all(d["_detalhe"]["cpf"] == CPF_SINTETICO for d in lista)
