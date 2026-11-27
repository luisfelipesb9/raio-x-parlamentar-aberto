"""CamaraSource.fetch(fonte_votos="dump"): baixa o dump anual oficial e o lê em streaming.

O cliente é um `httpx.MockTransport` que serve as fixtures `camara_dump_*_2025.csv`; nada toca a
rede nem a pasta real de brutos.
"""
from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest

import sources.base
from sources import manifest
from sources.camara.source import CamaraSource

FIX = Path(__file__).parent / "fixtures"
Q1 = {"data_inicio": "2025-01-01", "data_fim": "2025-03-31"}


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


class Site:
    """API de deputados (vazia) + servidor dos arquivos de dump. Registra os pedidos."""

    def __init__(self, status_dump: list[int] | None = None, anos: tuple[int, ...] = (2025,)):
        self.pedidos: list[httpx.Request] = []
        self.status_dump = status_dump or []  # códigos a devolver antes de servir de verdade
        self.anos = anos
        self.client = httpx.Client(transport=httpx.MockTransport(self._handler))

    def _handler(self, req: httpx.Request) -> httpx.Response:
        self.pedidos.append(req)
        if req.url.path.startswith("/api/v2/"):  # deputados e listagem de votações: vazias
            return httpx.Response(200, json={"dados": [], "links": []})
        m = re.fullmatch(r"/arquivos/(\w+)/csv/(\w+)-(\d{4})\.csv", req.url.path)
        if not m or m[1] != m[2]:
            return httpx.Response(404)
        if self.status_dump:
            return httpx.Response(self.status_dump.pop(0))
        if int(m[3]) not in self.anos:
            return httpx.Response(404)
        nome = {"votacoes": "votacoes", "votacoesVotos": "votos",
                "votacoesOrientacoes": "orientacoes"}[m[1]]
        return httpx.Response(200, content=(FIX / f"camara_dump_{nome}_2025.csv").read_bytes())

    def baixados(self) -> list[str]:
        return [r.url.path for r in self.pedidos if r.url.path.startswith("/arquivos")]

    def listagens_api(self) -> list[httpx.Request]:
        return [r for r in self.pedidos if r.url.path.endswith("/votacoes")]


def _fonte(site: Site, **kw) -> CamaraSource:
    return CamaraSource(client=site.client, pausa=0, max_tentativas=3, dormir=lambda s: None, **kw)


def test_baixa_os_tres_arquivos_do_ano_e_nao_usa_a_api_de_votacoes(raw_dir):
    site = Site()
    raw = _fonte(site).fetch(fonte_votos="dump", **Q1)
    assert sorted(site.baixados()) == [
        "/arquivos/votacoes/csv/votacoes-2025.csv",
        "/arquivos/votacoesOrientacoes/csv/votacoesOrientacoes-2025.csv",
        "/arquivos/votacoesVotos/csv/votacoesVotos-2025.csv"]
    assert site.listagens_api() == []
    assert set(raw) == {"deputados", "votacoes"}  # mesmo formato do bruto da API
    assert [v["id"] for v in raw["votacoes"]] == ["2458405-38", "2458405-40", "2442848-52"]
    assert len(raw["votacoes"][2]["_votos"]) == 3


def test_janela_longa_funciona_sem_fatiar_porque_o_dump_e_anual(raw_dir):
    site = Site()
    raw = _fonte(site).fetch(fonte_votos="dump", data_inicio="2025-01-01", data_fim="2025-12-31")
    assert len(raw["votacoes"]) == 4
    assert len(site.baixados()) == 3  # 3 arquivos para o ano, não centenas de chamadas


def test_janela_que_cruza_o_ano_baixa_os_dois_anos(raw_dir):
    site = Site(anos=(2024, 2025))
    _fonte(site).fetch(fonte_votos="dump", data_inicio="2024-11-01", data_fim="2025-02-28")
    assert {re.search(r"-(\d{4})\.csv", p)[1] for p in site.baixados()} == {"2024", "2025"}


def test_votacao_simbolica_nao_vira_voto_individual_no_fluxo_completo(raw_dir):
    raw = _fonte(Site()).fetch(fonte_votos="dump", **Q1)
    fatos = CamaraSource(client=object()).normalize(raw)
    simbolicas = {f.chave for f in fatos if f.tipo == "votacao" and not f.atributos["nominal"]}
    assert simbolicas == {"2458405-38", "2458405-40"}
    assert not any(f.tipo == "voto" and f.atributos["votacao_id"] in simbolicas for f in fatos)


def test_max_votacoes_vale_no_dump(raw_dir):
    raw = _fonte(Site()).fetch(fonte_votos="dump", max_votacoes=1, **Q1)
    assert [v["id"] for v in raw["votacoes"]] == ["2458405-38"]


def test_arquivos_ficam_em_raw_camara_dumps_e_entram_no_manifesto(raw_dir):
    _fonte(Site()).fetch(fonte_votos="dump", **Q1)
    pasta = raw_dir / "camara" / "dumps"
    assert sorted(p.name for p in pasta.iterdir()) == [
        "votacoes-2025.csv", "votacoesOrientacoes-2025.csv", "votacoesVotos-2025.csv"]
    assert (pasta / "votacoesVotos-2025.csv").read_bytes() == (
        FIX / "camara_dump_votos_2025.csv").read_bytes()
    arquivos = {i["arquivo"] for i in manifest.carregar(raw_dir)["arquivos"]}
    assert "dumps/votacoesVotos-2025.csv" in arquivos
    assert "camara_2025-01-01_2025-03-31.json" in arquivos
    assert manifest.verificar(raw_dir) == []


def test_reusar_dumps_nao_baixa_de_novo(raw_dir):
    _fonte(Site()).fetch(fonte_votos="dump", **Q1)
    site = Site()
    raw = _fonte(site).fetch(fonte_votos="dump", reusar_dumps=True, **Q1)
    assert site.baixados() == []
    assert len(raw["votacoes"]) == 3


def test_sem_reusar_dumps_baixa_de_novo_porque_o_arquivo_muda_todo_dia(raw_dir):
    _fonte(Site()).fetch(fonte_votos="dump", **Q1)
    site = Site()
    _fonte(site).fetch(fonte_votos="dump", **Q1)
    assert len(site.baixados()) == 3


def test_download_com_5xx_e_retentado(raw_dir):
    site = Site(status_dump=[503, 429])
    raw = _fonte(site).fetch(fonte_votos="dump", **Q1)
    assert len(raw["votacoes"]) == 3
    assert len(site.baixados()) == 3 + 2


def test_ano_sem_arquivo_da_erro_claro_e_nao_deixa_arquivo_incompleto(raw_dir):
    site = Site(anos=(2024,))  # 2025 devolve 404
    with pytest.raises(httpx.HTTPStatusError, match="404"):
        _fonte(site).fetch(fonte_votos="dump", **Q1)
    pasta = raw_dir / "camara" / "dumps"
    assert not list(pasta.glob("*")) if pasta.exists() else True
    assert not (raw_dir / "camara" / "camara_2025-01-01_2025-03-31.json").exists()


def test_fonte_de_votos_desconhecida_e_erro_antes_de_qualquer_chamada(raw_dir):
    site = Site()
    with pytest.raises(ValueError, match="fonte_votos"):
        _fonte(site).fetch(fonte_votos="xml", **Q1)
    assert site.pedidos == []


def test_padrao_continua_sendo_a_api(raw_dir):
    site = Site()
    _fonte(site).fetch(**Q1)
    assert site.baixados() == [] and len(site.listagens_api()) == 1
