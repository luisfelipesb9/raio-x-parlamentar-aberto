"""CEAP no pipeline: cada ano é baixado e lido UMA vez, não importa quantos deputados; e vários
anos (`--anos-ceap`) em sequência, um de cada vez. Sem rede: o zip do ano vem de um MockTransport.
"""
from __future__ import annotations

import io
import json
import zipfile

import httpx
import pytest

import ingest.pipeline as pipeline_mod
import sources.base
import sources.ceap.source as ceap_mod
from contracts import Fact
from ingest.pipeline import Opcoes, Pipeline, _lista_de_anos
from repo.store import Store
from sources.ceap.source import CeapSource

N_DEPUTADOS = 513
LINHAS_POR_DEPUTADO = 3


@pytest.fixture(autouse=True)
def _raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)


def _linha(dep: int, i: int, ano: int, *, mes: int = 3, data: str | None = "x") -> dict:
    return {"idDeputado": dep, "idDocumento": dep * 100 + i + ano, "cnpjCPF": "63356042000180",
            "fornecedor": "ALARES", "valorLiquido": "10.00", "descricao": "MANUTENÇÃO",
            "dataEmissao": f"{ano}-{mes:02d}-10T00:00:00" if data == "x" else data,
            "ano": ano, "mes": mes, "numero": f"N{dep}-{i}", "parcela": 0, "lote": 1}


def _zip(linhas: list[dict], ano: int) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"Ano-{ano}.json", json.dumps({"dados": linhas}))
    return buf.getvalue()


class Servidor:
    def __init__(self, por_ano: dict[int, list[dict]]):
        self.zips = {f"https://www.camara.leg.br/cotas/Ano-{a}.json.zip": _zip(ls, a)
                     for a, ls in por_ano.items()}
        self.gets: list[str] = []

    def fonte(self) -> CeapSource:
        def handler(request: httpx.Request) -> httpx.Response:
            self.gets.append(str(request.url))
            corpo = self.zips.get(str(request.url))
            return httpx.Response(200, content=corpo) if corpo else httpx.Response(404)
        return CeapSource(client=httpx.Client(transport=httpx.MockTransport(handler)))


def _deputados(n: int) -> list[Fact]:
    return [Fact(tipo="deputado", chave=str(i), fonte="t", id_oficial=str(i), url="https://x",
                 atributos={"nome": f"DEP {i}", "uf": "MG", "partido": "PX"})
            for i in range(1, n + 1)]


def _rodar(servidor: Servidor, store: Store | None = None, n_dep: int = N_DEPUTADOS, **kw):
    store = store or Store(":memory:")
    if not store.facts_by_tipo("deputado"):
        store.upsert_facts(_deputados(n_dep))
    pipe = Pipeline(store, Opcoes(fontes=("ceap",), amostra=n_dep, **kw),
                    registry={"ceap": servidor.fonte}, log=lambda _: None)
    return store, pipe.executar()


# ---------- o ano inteiro é lido uma vez, para qualquer número de deputados ----------

def test_ano_e_baixado_e_lido_uma_vez_para_513_deputados(monkeypatch):
    leituras: list[int] = []
    original = ceap_mod.iterar_dados

    def conta(*a, **k):
        leituras.append(1)
        yield from original(*a, **k)

    monkeypatch.setattr(ceap_mod, "iterar_dados", conta)
    srv = Servidor({2024: [_linha(d, i, 2024) for d in range(1, N_DEPUTADOS + 1)
                           for i in range(LINHAS_POR_DEPUTADO)]})

    store, rel = _rodar(srv, ano=2024)

    assert len(srv.gets) == 1 and len(leituras) == 1  # não 513
    assert len(store.facts_by_tipo("despesa_ceap")) == N_DEPUTADOS * LINHAS_POR_DEPUTADO
    assert rel["ceap"]["despesas"] == N_DEPUTADOS * LINHAS_POR_DEPUTADO


def test_o_zip_do_ano_fica_guardado_uma_vez_em_data_raw(tmp_path):
    srv = Servidor({2024: [_linha(1, 0, 2024)]})
    _rodar(srv, ano=2024, n_dep=1)
    assert [p.name for p in (tmp_path / "ceap").glob("Ano-*.zip")] == ["Ano-2024.json.zip"]


# ---------- vários anos ----------

def test_anos_ceap_baixa_cada_ano_uma_vez_e_grava_todos():
    srv = Servidor({2023: [_linha(1, 0, 2023), _linha(2, 0, 2023)],
                    2024: [_linha(1, 0, 2024)]})
    store, rel = _rodar(srv, n_dep=2, anos_ceap=(2023, 2024))
    assert srv.gets == ["https://www.camara.leg.br/cotas/Ano-2023.json.zip",
                        "https://www.camara.leg.br/cotas/Ano-2024.json.zip"]
    anos = sorted(f.atributos["data"][:4] for f in store.facts_by_tipo("despesa_ceap"))
    assert anos == ["2023", "2023", "2024"]
    assert rel["ceap"]["despesas"] == 3 and rel["ceap"]["com_cnpj"] == 3
    assert rel["ceap"]["por_ano"] == {2023: 2, 2024: 1}


def test_anos_ceap_vale_no_lugar_de_ano():
    srv = Servidor({2022: [_linha(1, 0, 2022)], 2023: [_linha(1, 0, 2023)],
                    2024: [_linha(1, 0, 2024)]})
    store, _ = _rodar(srv, n_dep=1, ano=2024, anos_ceap=(2022, 2023))
    assert len(srv.gets) == 2 and not any("2024" in u for u in srv.gets)
    assert len(store.facts_by_tipo("despesa_ceap")) == 2


def test_anos_repetidos_sao_lidos_uma_vez():
    srv = Servidor({2024: [_linha(1, 0, 2024)]})
    _rodar(srv, n_dep=1, anos_ceap=(2024, 2024))
    assert len(srv.gets) == 1


def test_recarregar_o_ano_nao_apaga_o_outro_ano():
    srv = Servidor({2023: [_linha(1, 0, 2023)], 2024: [_linha(1, 0, 2024)]})
    store, _ = _rodar(srv, n_dep=1, anos_ceap=(2023, 2024))
    antes = {f.chave for f in store.facts_by_tipo("despesa_ceap")}
    _rodar(srv, store, n_dep=1, ano=2024)  # só refaz 2024
    assert {f.chave for f in store.facts_by_tipo("despesa_ceap")} == antes


def test_despesa_sem_data_de_um_ano_sobrevive_quando_o_outro_ano_e_carregado():
    # o delete por ano também apaga fatos sem data (não sabe de que carga são): numa rodada com
    # vários anos, todos os deletes vêm antes de qualquer gravação
    sem_data = {**_linha(1, 9, 2023), "dataEmissao": None}
    srv = Servidor({2023: [_linha(1, 0, 2023), sem_data], 2024: [_linha(1, 0, 2024)]})
    store, _ = _rodar(srv, n_dep=1, anos_ceap=(2023, 2024))
    datas = sorted(str(f.atributos["data"])[:4] for f in store.facts_by_tipo("despesa_ceap"))
    assert datas == ["2023", "2024", "None"]


def _zips_com_notas_de_outro_ano() -> Servidor:
    """O zip de um ano traz notas emitidas em outro ano: jan/2024 dentro do zip de 2023 e
    dez/2023 dentro do zip de 2024 (acontece: o arquivo é por ano de COMPETÊNCIA/lançamento)."""
    l23 = [_linha(1, 0, 2023), {**_linha(1, 1, 2023), "dataEmissao": "2024-01-05T00:00:00"}]
    l24 = [_linha(1, 0, 2024), {**_linha(1, 1, 2024), "dataEmissao": "2023-12-20T00:00:00"}]
    return Servidor({2023: l23, 2024: l24})


@pytest.mark.parametrize("ordem", [(2023, 2024), (2024, 2023)])
def test_nota_de_outro_ano_dentro_do_zip_nao_e_apagada_pelo_outro_ano(ordem):
    store, rel = _rodar(_zips_com_notas_de_outro_ano(), n_dep=1, anos_ceap=ordem)
    assert len(store.facts_by_tipo("despesa_ceap")) == 4 == rel["ceap"]["despesas"]


@pytest.mark.parametrize("ordem", [(2023, 2024), (2024, 2023)])
def test_recarregar_com_notas_de_outro_ano_nao_duplica_nem_perde(ordem):
    srv = _zips_com_notas_de_outro_ano()
    store, _ = _rodar(srv, n_dep=1, anos_ceap=ordem)
    antes = {f.chave for f in store.facts_by_tipo("despesa_ceap")}
    _rodar(srv, store, n_dep=1, anos_ceap=ordem)
    assert {f.chave for f in store.facts_by_tipo("despesa_ceap")} == antes


def test_nota_que_sumiu_do_zip_e_removida_na_recarga():
    srv = _zips_com_notas_de_outro_ano()
    store, _ = _rodar(srv, n_dep=1, anos_ceap=(2023, 2024))
    menos = Servidor({2023: [_linha(1, 0, 2023)],
                      2024: [_linha(1, 0, 2024), {**_linha(1, 1, 2024),
                                                  "dataEmissao": "2023-12-20T00:00:00"}]})
    _rodar(menos, store, n_dep=1, anos_ceap=(2023, 2024))
    assert len(store.facts_by_tipo("despesa_ceap")) == 3  # a de jan/2024 do zip de 2023 saiu


def test_nada_e_apagado_antes_de_o_primeiro_ano_ser_baixado():
    store = Store(":memory:")
    _rodar(Servidor({2023: [_linha(1, 0, 2023)]}), store, n_dep=1, anos_ceap=(2023,))
    with pytest.raises(httpx.HTTPStatusError):  # 2022 não existe: 404 no primeiro ano
        _rodar(Servidor({2023: [_linha(1, 0, 2023)]}), store, n_dep=1, anos_ceap=(2022, 2023))
    assert len(store.facts_by_tipo("despesa_ceap")) == 1


def test_ano_que_falha_interrompe_e_o_que_ja_foi_gravado_fica():
    srv = Servidor({2023: [_linha(1, 0, 2023)]})  # 2024 devolve 404
    store = Store(":memory:")
    with pytest.raises(httpx.HTTPStatusError):
        _rodar(srv, store, n_dep=1, anos_ceap=(2023, 2024))
    assert len(store.facts_by_tipo("despesa_ceap")) == 1


def test_ceap_sem_ano_nem_anos_falha_cedo():
    with pytest.raises(ValueError, match="--ano"):
        Pipeline(Store(":memory:"), Opcoes(fontes=("ceap",)), log=lambda _: None).executar()


# ---------- linha de comando ----------

@pytest.mark.parametrize("texto, esperado", [
    ("2024", (2024,)), ("2023,2024", (2023, 2024)), (" 2023 , 2024 ", (2023, 2024)),
    ("2024,2023,2024", (2024, 2023)),
])
def test_lista_de_anos_aceita_virgulas_e_tira_repeticao(texto, esperado):
    assert _lista_de_anos(texto) == esperado


@pytest.mark.parametrize("texto", ["", "abc", "2023,", "2023-2024", "1999", "20240"])
def test_lista_de_anos_recusa_lixo(texto):
    import argparse
    with pytest.raises(argparse.ArgumentTypeError):
        _lista_de_anos(texto)


def test_cli_anos_ceap_vira_opcao(monkeypatch, capsys):
    vistos: list[Opcoes] = []

    class PipelineFalso:
        def __init__(self, store, opcoes, **_):
            vistos.append(opcoes)

        def executar(self):
            return {}

    monkeypatch.setattr(pipeline_mod, "Pipeline", PipelineFalso)
    monkeypatch.setattr(pipeline_mod, "Store", lambda _db=None: None)
    pipeline_mod.main(["--fontes", "ceap", "--anos-ceap", "2023,2024", "--db", ":memory:"])
    assert vistos[0].anos_ceap == (2023, 2024) and vistos[0].ano is None
