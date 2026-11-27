"""CamaraSource.fetch: janela longa em trimestres e checkpoint por etapa.

Uma falha no meio da coleta não pode jogar fora o que já foi baixado: o bruto parcial fica em
`data/raw/camara/parcial/*.json.part` (o manifesto ignora `.part`) e a próxima chamada retoma dali.
O formato do bruto final (`camara_<início>_<fim>.json`) não muda.
"""
from __future__ import annotations

import json
import re

import httpx
import pytest

import sources.base
from sources import manifest
from sources.camara.source import CamaraSource


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


class Api:
    """API v2 falsa. Por fatia de data: 2 votações de PLEN (a 2ª só tem voto se for 'nominal') e
    1 de comissão. Registra cada pedido; `falhar` lista caminhos que respondem 500."""

    def __init__(self, falhar: set[str] | None = None, explodir_em: set[str] | None = None):
        self.pedidos: list[httpx.Request] = []
        self.falhar = falhar or set()
        self.explodir_em = explodir_em or set()  # caminhos que levantam erro NÃO HTTP (ex.: Ctrl+C)
        self.client = httpx.Client(transport=httpx.MockTransport(self._handler))

    def _handler(self, req: httpx.Request) -> httpx.Response:
        self.pedidos.append(req)
        path = req.url.path.removeprefix("/api/v2")
        if path in self.explodir_em:
            raise RuntimeError(f"interrompido em {path}")
        if path in self.falhar:
            return httpx.Response(500)
        if path == "/deputados":
            return self._ok([{"id": i, "nome": f"Dep {i}", "siglaPartido": "XX", "siglaUf": "MG",
                              "uri": f"u{i}"} for i in (1, 2, 3)])
        if m := re.fullmatch(r"/deputados/(\d+)", path):
            i = int(m[1])
            return self._ok({"id": i, "cpf": f"1234567890{i}", "nomeCivil": f"CIVIL {i}"})
        if path == "/votacoes":
            ini = req.url.params["dataInicio"]
            return self._ok([
                {"id": f"{ini}-A", "uri": f"v-{ini}-A", "data": ini, "siglaOrgao": "PLEN",
                 "descricao": "d"},
                {"id": f"{ini}-B", "uri": f"v-{ini}-B", "data": ini, "siglaOrgao": "PLEN",
                 "descricao": "d"},
                {"id": f"{ini}-C", "uri": f"v-{ini}-C", "data": ini, "siglaOrgao": "CCJC",
                 "descricao": "d"}])
        if m := re.fullmatch(r"/votacoes/(.+)/votos", path):
            nominal = m[1].endswith("-A")
            return self._ok([{"tipoVoto": "Sim", "deputado_": {"id": 1}}] if nominal else [])
        if re.fullmatch(r"/votacoes/(.+)/orientacoes", path):
            return self._ok([{"siglaPartidoBloco": "Governo", "orientacaoVoto": "Sim"}])
        return httpx.Response(404)

    @staticmethod
    def _ok(dados):
        return httpx.Response(200, json={"dados": dados, "links": []})

    def paths(self, padrao: str) -> list[str]:
        rx = re.compile(padrao)
        return [r.url.path.removeprefix("/api/v2") for r in self.pedidos
                if rx.fullmatch(r.url.path.removeprefix("/api/v2"))]

    def listagens(self) -> list[tuple[str, str]]:
        return [(r.url.params["dataInicio"], r.url.params["dataFim"]) for r in self.pedidos
                if r.url.path.endswith("/votacoes")]


def _fonte(api: Api, **kw) -> CamaraSource:
    return CamaraSource(client=api.client, pausa=0, max_tentativas=2, dormir=lambda s: None, **kw)


ANO = {"data_inicio": "2025-01-01", "data_fim": "2025-12-31"}
Q1 = "2025-01-01"


# ---------- janela longa ----------

def test_janela_de_um_ano_e_listada_em_quatro_fatias_de_ate_3_meses(raw_dir):
    api = Api()
    raw = _fonte(api).fetch(**ANO)
    assert api.listagens() == [("2025-01-01", "2025-03-31"), ("2025-04-01", "2025-06-30"),
                               ("2025-07-01", "2025-09-30"), ("2025-10-01", "2025-12-31")]
    # só Plenário, em ordem cronológica; comissão fica de fora
    assert [v["id"] for v in raw["votacoes"]] == [
        f"{d}-{x}" for d in ("2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01")
        for x in "AB"]


def test_um_trimestre_continua_sendo_uma_listagem_so(raw_dir):
    api = Api()
    _fonte(api).fetch(data_inicio="2025-01-01", data_fim="2025-03-31")
    assert api.listagens() == [("2025-01-01", "2025-03-31")]


def test_max_votacoes_vale_para_a_janela_toda_e_para_de_listar_o_que_nao_precisa(raw_dir):
    api = Api()
    raw = _fonte(api).fetch(max_votacoes=3, **ANO)
    assert [v["id"] for v in raw["votacoes"]] == [f"{Q1}-A", f"{Q1}-B", "2025-04-01-A"]
    assert len(api.listagens()) == 2  # a 3ª e a 4ª fatia nem são listadas
    assert api.paths(r"/votacoes/2025-07-01.*") == []


def test_max_votacoes_zero_nao_lista_nem_busca_votos(raw_dir):
    api = Api()
    raw = _fonte(api).fetch(max_votacoes=0, **ANO)
    assert raw["votacoes"] == [] and api.listagens() == []


def test_formato_do_bruto_nao_mudou(raw_dir):
    api = Api()
    raw = _fonte(api).fetch(data_inicio=Q1, data_fim="2025-03-31")
    assert set(raw) == {"deputados", "votacoes", "_escopo"}
    a = raw["votacoes"][0]
    assert a["siglaOrgao"] == "PLEN" and a["uri"] == f"v-{Q1}-A"
    assert a["_votos"] == [{"tipoVoto": "Sim", "deputado_": {"id": 1}}]
    assert a["_orientacoes"] == [{"siglaPartidoBloco": "Governo", "orientacaoVoto": "Sim"}]
    salvo = raw_dir / "camara" / "camara_2025-01-01_2025-03-31.json"
    assert json.loads(salvo.read_text(encoding="utf-8")) == raw
    fatos = CamaraSource(client=object()).normalize(raw)
    assert {(f.tipo, f.chave) for f in fatos if f.tipo in ("votacao", "voto")} == {
        ("votacao", f"{Q1}-A"), ("votacao", f"{Q1}-B"), ("voto", f"{Q1}-A:1")}


# ---------- checkpoint ----------

def _parciais(raw_dir):
    pasta = raw_dir / "camara" / "parcial"
    return sorted(p.name for p in pasta.glob("*")) if pasta.exists() else []


def test_falha_no_meio_guarda_o_que_ja_veio_e_nao_grava_o_bruto_final(raw_dir):
    api = Api(falhar={"/votacoes/2025-04-01-A/votos"})
    with pytest.raises(httpx.HTTPStatusError):
        _fonte(api).fetch(**ANO)
    assert not (raw_dir / "camara" / "camara_2025-01-01_2025-12-31.json").exists()
    assert _parciais(raw_dir)  # deputados + o 1º trimestre (+ a listagem do 2º) ficaram
    assert all(n.endswith(".part") for n in _parciais(raw_dir))


def test_retomada_nao_repete_o_que_ja_foi_baixado(raw_dir):
    api = Api(falhar={"/votacoes/2025-04-01-A/votos"})
    with pytest.raises(httpx.HTTPStatusError):
        _fonte(api).fetch(**ANO)

    api2 = Api()  # o servidor voltou
    raw = _fonte(api2).fetch(**ANO)
    assert api2.paths("/deputados") == []  # lista de deputados já estava guardada
    assert api2.listagens() == [("2025-07-01", "2025-09-30"), ("2025-10-01", "2025-12-31")]
    votos_pedidos = api2.paths(r"/votacoes/.+/votos")
    assert f"/votacoes/{Q1}-A/votos" not in votos_pedidos  # 1º trimestre: não repete
    assert "/votacoes/2025-04-01-A/votos" in votos_pedidos  # o que falhou, sim
    assert len(raw["votacoes"]) == 8

    limpo = _fonte(Api()).fetch(**ANO)
    assert raw == limpo  # retomar dá exatamente o mesmo bruto de uma coleta limpa


def test_retomada_no_meio_do_trimestre_so_busca_as_votacoes_que_faltam(raw_dir):
    api = Api(falhar={f"/votacoes/{Q1}-B/votos"})
    with pytest.raises(httpx.HTTPStatusError):
        _fonte(api).fetch(data_inicio=Q1, data_fim="2025-03-31")
    api2 = Api()
    _fonte(api2).fetch(data_inicio=Q1, data_fim="2025-03-31")
    assert api2.listagens() == []  # a listagem do trimestre estava guardada
    assert api2.paths(r"/votacoes/.+/votos") == [f"/votacoes/{Q1}-B/votos"]
    assert api2.paths(r"/votacoes/.+/orientacoes") == [f"/votacoes/{Q1}-B/orientacoes"]


def test_coleta_concluida_apaga_o_parcial_e_o_manifesto_so_conhece_o_bruto_final(raw_dir):
    _fonte(Api()).fetch(**ANO)
    assert _parciais(raw_dir) == []
    arquivos = {i["arquivo"] for i in manifest.carregar(raw_dir)["arquivos"]}
    assert arquivos == {"camara_2025-01-01_2025-12-31.json"}


def test_manifesto_ignora_parcial_de_coleta_interrompida(raw_dir):
    api = Api(falhar={"/votacoes/2025-04-01-A/votos"})
    with pytest.raises(httpx.HTTPStatusError):
        _fonte(api).fetch(**ANO)
    assert manifest.verificar(raw_dir) == [manifest.Problema(
        "manifest.json", "manifesto_ausente", "manifesto ausente: rode com --gerar-manifesto")]
    assert not any("parcial" in a for _, a in manifest._arquivos_em_disco(raw_dir))


def test_retomar_falso_refaz_tudo(raw_dir):
    api = Api(falhar={"/votacoes/2025-04-01-A/votos"})
    with pytest.raises(httpx.HTTPStatusError):
        _fonte(api).fetch(**ANO)
    api2 = Api()
    _fonte(api2).fetch(retomar=False, **ANO)
    assert len(api2.paths("/deputados")) == 1
    assert len(api2.listagens()) == 4
    assert f"/votacoes/{Q1}-A/votos" in api2.paths(r"/votacoes/.+/votos")


def test_parcial_de_outra_janela_ou_escopo_nao_contamina(raw_dir):
    api = Api(falhar={"/votacoes/2025-04-01-A/votos"})
    with pytest.raises(httpx.HTTPStatusError):
        _fonte(api).fetch(**ANO)
    api2 = Api()
    _fonte(api2).fetch(data_inicio="2024-01-01", data_fim="2024-03-31", legislatura_completa=True)
    assert len(api2.paths("/deputados")) == 1  # outro escopo de deputados: baixa de novo
    assert api2.listagens() == [("2024-01-01", "2024-03-31")]


def test_interrupcao_nao_http_tambem_preserva_o_progresso(raw_dir):
    """Ctrl+C / erro inesperado no meio de uma votação: o que já veio fica guardado."""
    api = Api(explodir_em={f"/votacoes/{Q1}-B/votos"})
    with pytest.raises(RuntimeError, match="interrompido"):
        _fonte(api).fetch(data_inicio=Q1, data_fim="2025-03-31")
    api2 = Api()
    _fonte(api2).fetch(data_inicio=Q1, data_fim="2025-03-31")
    assert f"/votacoes/{Q1}-A/votos" not in api2.paths(r"/votacoes/.+/votos")


# ---------- detalhe dos deputados (CPF só do que a API pública devolve) ----------

def test_detalhe_retoma_do_que_ja_foi_buscado(raw_dir):
    api = Api(explodir_em={"/deputados/3"})
    with pytest.raises(RuntimeError):
        _fonte(api).fetch(max_votacoes=0, detalhar_deputados=True)
    api2 = Api()
    raw = _fonte(api2).fetch(max_votacoes=0, detalhar_deputados=True)
    assert api2.paths(r"/deputados/\d+") == ["/deputados/3"]  # 1 e 2 já estavam guardados
    assert [d["_detalhe"]["nomeCivil"] for d in raw["deputados"]] == ["CIVIL 1", "CIVIL 2",
                                                                      "CIVIL 3"]


def test_detalhe_com_erro_http_nao_vira_dado_guardado_e_e_tentado_de_novo(raw_dir):
    api = Api(falhar={"/deputados/2"})
    raw = _fonte(api).fetch(max_votacoes=0, detalhar_deputados=True)
    assert [e["id"] for e in raw["deputados_erros"]] == [2]
    # coleta concluída apaga o parcial; uma nova coleta tenta o 2 de novo
    api2 = Api()
    raw2 = _fonte(api2).fetch(max_votacoes=0, detalhar_deputados=True)
    assert "deputados_erros" not in raw2
    assert api2.paths(r"/deputados/\d+") == ["/deputados/1", "/deputados/2", "/deputados/3"]


def test_detalhe_so_guarda_cpf_e_nome_civil(raw_dir):
    api = Api()
    raw = _fonte(api).fetch(max_votacoes=0, detalhar_deputados=[1])
    assert set(raw["deputados"][0]["_detalhe"]) == {"cpf", "nomeCivil"}
    assert "_detalhe" not in raw["deputados"][1]
