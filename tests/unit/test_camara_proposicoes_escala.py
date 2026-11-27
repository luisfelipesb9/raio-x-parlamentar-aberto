"""Proposições na escala nacional: sem teto por padrão e checkpoint por proposição.

Com 513 autores consultados em ordem de id, um teto de 300 proposições vira amostra enviesada
pelos primeiros autores. O teto continua existindo só como opção de demonstração (e avisa).
Reaproveita o `FakeApi` (fixtures reais da API v2) de `test_src_camara_proposicoes`.
"""
from __future__ import annotations

import logging

import httpx
import pytest

import sources.base
from sources.camara.source import CamaraSource
from tests.unit.test_src_camara_proposicoes import PEC, PL719, PL2338, FakeApi

JANELA = ("2023-01-01", "2025-12-31")


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


class ApiQueExplode(FakeApi):
    """Levanta erro NÃO HTTP (Ctrl+C, queda do processo) ao pedir o caminho indicado."""

    def __init__(self, explodir_em: str | None):
        super().__init__()
        self.explodir_em = explodir_em

    def _handler(self, req: httpx.Request) -> httpx.Response:
        if self.explodir_em and req.url.path.endswith(self.explodir_em):
            self.pedidos.append(req)
            raise RuntimeError("interrompido")
        return super()._handler(req)


def _fonte(api: FakeApi) -> CamaraSource:
    return CamaraSource(client=api.client, pausa=0, max_tentativas=2, dormir=lambda s: None)


def _listagens(api: FakeApi) -> list[str]:
    """Chamadas à listagem `/proposicoes` (não às de autores/tramitações de cada uma)."""
    return [p for p in api.paths("/proposicoes") if p == "/proposicoes"]


def _pasta_parcial(raw_dir):
    return raw_dir / "camara" / "parcial"


# ---------- sem teto ----------

def test_sem_teto_por_padrao_traz_todas_as_proposicoes_dos_autores(raw_dir):
    out = _fonte(FakeApi()).fetch_proposicoes(*JANELA, deputado_ids=["62881", "66828"])
    assert [p["id"] for p in out["proposicoes"]] == [PEC, PL719, PL2338]


def test_fetch_com_proposicoes_nao_tem_teto_se_ninguem_pedir(raw_dir):
    raw = _fonte(FakeApi()).fetch(max_votacoes=0, incluir_proposicoes=True,
                                  data_inicio=JANELA[0], data_fim=JANELA[1])
    assert len(raw["proposicoes"]) == 3


# ---------- teto = demonstração, e avisa que é amostra enviesada ----------

def test_teto_atingido_avisa_que_e_amostra_de_demonstracao(raw_dir, caplog):
    with caplog.at_level(logging.WARNING, logger="sources.camara.source"):
        out = _fonte(FakeApi()).fetch_proposicoes(*JANELA, deputado_ids=["62881"],
                                                  max_proposicoes=2)
    assert len(out["proposicoes"]) == 2
    aviso = " ".join(r.getMessage() for r in caplog.records)
    assert "max_proposicoes=2" in aviso and "demonstração" in aviso and "enviesad" in aviso


def test_teto_que_nao_corta_nada_nao_avisa(raw_dir, caplog):
    with caplog.at_level(logging.WARNING, logger="sources.camara.source"):
        out = _fonte(FakeApi()).fetch_proposicoes(*JANELA, deputado_ids=["62881"],
                                                  max_proposicoes=50)
    assert len(out["proposicoes"]) == 3
    assert caplog.records == []


def test_teto_igual_ao_total_nao_avisa_nem_com_varios_autores(raw_dir, caplog):
    with caplog.at_level(logging.WARNING, logger="sources.camara.source"):
        out = _fonte(FakeApi()).fetch_proposicoes(*JANELA, deputado_ids=["62881", "66828"],
                                                  max_proposicoes=3)
    assert len(out["proposicoes"]) == 3
    assert caplog.records == []


def test_teto_menor_que_o_total_avisa_mesmo_com_varios_autores(raw_dir, caplog):
    with caplog.at_level(logging.WARNING, logger="sources.camara.source"):
        _fonte(FakeApi()).fetch_proposicoes(*JANELA, deputado_ids=["62881", "66828"],
                                            max_proposicoes=2)
    assert len(caplog.records) == 1


# ---------- checkpoint ----------

def test_interrupcao_guarda_as_proposicoes_prontas_e_a_retomada_nao_as_repete(raw_dir):
    api = ApiQueExplode(explodir_em=f"/proposicoes/{PL719}/autores")
    with pytest.raises(RuntimeError):
        _fonte(api).fetch_proposicoes(*JANELA, deputado_ids=["62881"])
    assert any(_pasta_parcial(raw_dir).glob("proposicoes_*.json.part"))

    api2 = FakeApi()
    out = _fonte(api2).fetch_proposicoes(*JANELA, deputado_ids=["62881"])
    pedidas = api2.paths("/proposicoes/")
    assert f"/proposicoes/{PEC}/autores" not in pedidas  # já estava pronta
    assert f"/proposicoes/{PL719}/autores" in pedidas
    assert _listagens(api2) == []  # a lista de proposições dos autores já estava guardada

    limpo = _fonte(FakeApi()).fetch_proposicoes(*JANELA, deputado_ids=["62881"])
    assert out == limpo  # retomar dá o mesmo resultado de uma coleta limpa


def test_retomada_nao_refaz_a_listagem_por_autor(raw_dir):
    api = ApiQueExplode(explodir_em=f"/proposicoes/{PL719}/autores")
    with pytest.raises(RuntimeError):
        _fonte(api).fetch_proposicoes(*JANELA, deputado_ids=["62881", "66828"])
    api2 = FakeApi()
    _fonte(api2).fetch_proposicoes(*JANELA, deputado_ids=["62881", "66828"])
    assert _listagens(api2) == []


def test_proposicao_com_erro_http_continua_sendo_registrada_e_tentada_de_novo(raw_dir):
    api = FakeApi(erro_em={f"{PL719}/autores"})
    out = _fonte(api).fetch_proposicoes(*JANELA, deputado_ids=["62881"])
    assert [e["id"] for e in out["erros"]] == [PL719]
    api2 = FakeApi()
    out2 = _fonte(api2).fetch_proposicoes(*JANELA, deputado_ids=["62881"])
    assert out2["erros"] == [] and [p["id"] for p in out2["proposicoes"]] == [PEC, PL719, PL2338]


def test_coleta_concluida_apaga_so_o_parcial_das_proposicoes(raw_dir):
    parcial = _pasta_parcial(raw_dir)
    parcial.mkdir(parents=True)
    (parcial / "deputados_exercicio.json.part").write_text("[]", encoding="utf-8")
    _fonte(FakeApi()).fetch_proposicoes(*JANELA, deputado_ids=["62881"])
    assert [p.name for p in parcial.iterdir()] == ["deputados_exercicio.json.part"]


def test_parcial_de_outros_autores_ou_teto_nao_contamina(raw_dir):
    api = ApiQueExplode(explodir_em=f"/proposicoes/{PL719}/autores")
    with pytest.raises(RuntimeError):
        _fonte(api).fetch_proposicoes(*JANELA, deputado_ids=["62881"])
    api2 = FakeApi()
    _fonte(api2).fetch_proposicoes(*JANELA, deputado_ids=["66828"])
    assert f"/proposicoes/{PEC}/autores" in api2.paths("/proposicoes/")  # recomeçou
    api3 = FakeApi()
    _fonte(api3).fetch_proposicoes(*JANELA, deputado_ids=["62881"], max_proposicoes=2)
    assert f"/proposicoes/{PEC}/autores" in api3.paths("/proposicoes/")


def test_fetch_completo_com_proposicoes_apaga_todo_o_parcial(raw_dir):
    _fonte(FakeApi()).fetch(max_votacoes=0, incluir_proposicoes=True,
                            data_inicio=JANELA[0], data_fim=JANELA[1])
    assert not _pasta_parcial(raw_dir).exists()


def test_fetch_concluido_nao_apaga_o_parcial_de_proposicoes_pendente(raw_dir):
    """O pipeline roda `fetch` e depois `fetch_proposicoes`: o parcial deste último, deixado por
    uma coleta que caiu, tem de sobreviver ao fim do `fetch` e ser retomado."""
    api = ApiQueExplode(explodir_em=f"/proposicoes/{PL719}/autores")
    with pytest.raises(RuntimeError):
        _fonte(api).fetch_proposicoes(*JANELA, deputado_ids=["62881"])

    _fonte(FakeApi()).fetch(max_votacoes=0, data_inicio=JANELA[0], data_fim=JANELA[1])
    assert any(_pasta_parcial(raw_dir).glob("proposicoes_*.json.part"))

    api2 = FakeApi()
    _fonte(api2).fetch_proposicoes(*JANELA, deputado_ids=["62881"])
    assert f"/proposicoes/{PEC}/autores" not in api2.paths("/proposicoes/")


def test_fetch_nao_apaga_arquivo_de_parcial_que_nao_e_dele(raw_dir):
    estranho = _pasta_parcial(raw_dir) / "outra_etapa.json.part"
    estranho.parent.mkdir(parents=True)
    estranho.write_text("[]", encoding="utf-8")
    _fonte(FakeApi()).fetch(max_votacoes=0)
    assert estranho.exists()


def test_gerador_em_siglas_tipo_e_ids_nao_deixa_parcial_para_tras(raw_dir):
    """Um gerador é consumido na coleta; o nome do parcial a apagar tem de ser o mesmo."""
    parcial = _pasta_parcial(raw_dir)
    out = _fonte(FakeApi()).fetch_proposicoes(
        *JANELA, deputado_ids=(i for i in ["62881"]), siglas_tipo=(s for s in ["PL", "PEC"]))
    assert out["proposicoes"]
    assert not parcial.exists() or list(parcial.iterdir()) == []
