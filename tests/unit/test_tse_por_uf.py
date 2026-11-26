"""TSE no modo nacional: uma UF por vez (baixar -> normalizar -> gravar -> liberar) e retomada.

O pipeline antes chamava `fetch(uf=None)`, que percorre as 27 UFs e devolve tudo em memória. Agora,
sem escopo, usa `fetch_por_uf`; `--reusar-raw` lê de `data/raw/tse/tse_{ano}_{UF}.json` a UF que já
foi baixada em vez de baixá-la de novo. Sem rede: zips e IBGE falsos (MockTransport) e UFs
fictícias.
"""
from __future__ import annotations

import json
from collections.abc import Iterator

import httpx
import pytest

import sources.base
from contracts import Fact
from ingest.pipeline import Opcoes, Pipeline
from repo.store import Store
from sources.base import Source
from sources.tse.source import TseSource
from tests.unit.test_src_tse import URL_IBGE, _servidor, _zips

CONJ = ("candidatos", "receitas", "votacao")


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


class ClienteQueFalha(httpx.Client):
    """Qualquer requisição é erro: prova que nada foi baixado."""

    def __init__(self):
        super().__init__(transport=httpx.MockTransport(self._falha))

    @staticmethod
    def _falha(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"requisição inesperada: {request.method} {request.url}")


def _contar_membros(monkeypatch) -> list[str]:
    """Registra o nome de cada CSV aberto para leitura (é o que custa download)."""
    abertos: list[str] = []
    original = TseSource._linhas

    def espiao(z, membro, colunas):
        abertos.append(membro)
        return original(z, membro, colunas)

    monkeypatch.setattr(TseSource, "_linhas", staticmethod(espiao))
    return abertos


# ---------- retomada no nível da fonte ----------

def test_reusar_raw_nao_le_de_novo_a_uf_ja_gravada(raw_dir, monkeypatch):
    primeira = list(TseSource(client=_servidor(_zips())).fetch_por_uf(conjuntos=CONJ))
    assert [p["uf"] for p in primeira] == ["AC", "MG"]
    (raw_dir / "tse" / "tse_2022_MG.json").unlink()  # a rodada caiu antes de gravar MG
    abertos = _contar_membros(monkeypatch)

    retomada = list(TseSource(client=_servidor(_zips())).fetch_por_uf(
        conjuntos=CONJ, reusar_raw=True))

    assert [p["uf"] for p in retomada] == ["AC", "MG"]
    assert retomada[0] == primeira[0]                       # AC veio do disco, igual
    assert all("_MG." in m for m in abertos) and abertos    # só os arquivos de MG foram lidos
    assert (raw_dir / "tse" / "tse_2022_MG.json").is_file()  # e MG foi regravada


def test_reusar_raw_com_todas_as_ufs_gravadas_nao_baixa_dados_nem_consulta_o_ibge(
        raw_dir, monkeypatch):
    list(TseSource(client=_servidor(_zips())).fetch_por_uf(conjuntos=CONJ))
    abertos = _contar_membros(monkeypatch)
    visto: list = []
    retomada = list(TseSource(client=_servidor(_zips(), visto)).fetch_por_uf(
        conjuntos=CONJ, reusar_raw=True))
    assert [p["uf"] for p in retomada] == ["AC", "MG"]
    assert abertos == []
    assert URL_IBGE not in [u for _, u, _ in visto]


def test_reusar_raw_com_uf_explicita_gravada_nao_abre_nenhum_zip(raw_dir):
    [primeira] = list(TseSource(client=_servidor(_zips())).fetch_por_uf("AC", conjuntos=CONJ))
    [de_novo] = list(TseSource(client=ClienteQueFalha()).fetch_por_uf(
        "AC", conjuntos=CONJ, reusar_raw=True))
    assert de_novo == primeira


def test_sem_reusar_raw_baixa_mesmo_com_bruto_em_disco(raw_dir, monkeypatch):
    list(TseSource(client=_servidor(_zips())).fetch_por_uf("AC", conjuntos=CONJ))
    abertos = _contar_membros(monkeypatch)
    list(TseSource(client=_servidor(_zips())).fetch_por_uf("AC", conjuntos=CONJ))
    assert any("_AC." in m for m in abertos)


@pytest.mark.parametrize("estraga", [
    lambda p: p.write_text("{não é json", encoding="utf-8"),
    lambda p: p.write_text(json.dumps({"ano": 2022, "uf": "AC", "candidatos": []}), "utf-8"),
    lambda p: p.write_text(json.dumps({"ano": 2021, "uf": "AC", "candidatos": [], "receitas": [],
                                       "votacao": [], "municipios_ibge": []}), "utf-8"),
    lambda p: p.write_text(json.dumps({"ano": 2022, "uf": "MG", "candidatos": [], "receitas": [],
                                       "votacao": [], "municipios_ibge": []}), "utf-8"),
    lambda p: p.write_text(json.dumps([1, 2]), "utf-8"),
], ids=["json-quebrado", "sem-conjuntos", "outro-ano", "outra-uf", "nao-e-objeto"])
def test_reusar_raw_ignora_bruto_ilegivel_ou_de_outra_coisa_e_baixa_de_novo(
        raw_dir, monkeypatch, estraga):
    [original] = list(TseSource(client=_servidor(_zips())).fetch_por_uf("AC", conjuntos=CONJ))
    estraga(raw_dir / "tse" / "tse_2022_AC.json")
    [de_novo] = list(TseSource(client=_servidor(_zips())).fetch_por_uf(
        "AC", conjuntos=CONJ, reusar_raw=True))
    assert de_novo == original


def test_fetch_repassa_reusar_raw_e_nao_baixa_a_uf_gravada(raw_dir):
    TseSource(client=_servidor(_zips())).fetch(uf="AC")
    out = TseSource(client=ClienteQueFalha()).fetch(uf="AC", reusar_raw=True)
    assert len(out["candidatos"]) == 4


# ---------- pipeline: modo nacional uma UF por vez ----------

def _cand(sq: str, uf: str) -> dict:
    return {"ANO_ELEICAO": "2022", "SQ_CANDIDATO": sq, "NR_CPF_CANDIDATO": "99999000001",
            "NM_CANDIDATO": f"CANDIDATO {sq}", "NM_URNA_CANDIDATO": f"URNA {sq}",
            "DS_CARGO": "DEPUTADO FEDERAL", "SG_UF": uf, "SG_PARTIDO": "PX",
            "DS_SIT_TOT_TURNO": "ELEITO"}


def _parte(uf: str, n: int = 2) -> dict:
    return {"ano": 2022, "uf": uf, "candidatos": [_cand(f"{uf}{i}", uf) for i in range(n)],
            "receitas": [], "votacao": [], "municipios_ibge": []}


class TseUmaUfPorVez(TseSource):
    """`fetch_por_uf` falso. O gerador anota o que o banco já tem a cada vez que é retomado."""

    def __init__(self, ufs: list[str], store: Store | None = None):
        self.ufs, self.store = ufs, store
        self.pedidos: list[dict] = []
        self.gravadas_ao_retomar: list[set[str]] = []

    def fetch(self, *a, **k):
        raise AssertionError("o modo nacional não pode usar o fetch que acumula tudo em memória")

    def fetch_por_uf(self, uf=None, ano=2022, conjuntos=CONJ, reusar_raw=False) -> Iterator[dict]:
        self.pedidos.append({"uf": uf, "ano": ano, "conjuntos": conjuntos,
                             "reusar_raw": reusar_raw})
        for sigla in self.ufs:
            if self.store is not None:
                self.gravadas_ao_retomar.append(
                    {f.atributos["uf"] for f in self.store.facts_by_tipo("candidatura")})
            yield _parte(sigla)


def _nacional(src: TseSource, store: Store | None = None, **kw) -> tuple[Store, dict]:
    store = store or Store(":memory:")
    pipe = Pipeline(store, Opcoes(fontes=("tse",), **kw), registry={"tse": lambda: src},
                    log=lambda _: None)
    return store, pipe.executar()


def test_modo_nacional_usa_fetch_por_uf_com_ano_e_conjuntos():
    src = TseUmaUfPorVez(["AA", "AB", "AC"])
    store, rel = _nacional(src, ano_eleicao=2022)
    assert src.pedidos == [{"uf": None, "ano": 2022, "conjuntos": CONJ, "reusar_raw": False}]
    assert {f.atributos["uf"] for f in store.facts_by_tipo("candidatura")} == {"AA", "AB", "AC"}
    assert rel["tse"]["candidaturas_gravadas"] == 6


def test_cada_uf_ja_esta_no_banco_antes_de_a_proxima_ser_lida():
    store = Store(":memory:")
    src = TseUmaUfPorVez(["AA", "AB", "AC"], store)
    _nacional(src, store)
    assert src.gravadas_ao_retomar == [set(), {"AA"}, {"AA", "AB"}]


def test_reusar_raw_chega_ao_fetch_por_uf():
    src = TseUmaUfPorVez(["AA"])
    _nacional(src, reusar_raw=True)
    assert src.pedidos[0]["reusar_raw"] is True


def test_regravar_uma_uf_nao_apaga_as_candidaturas_das_outras():
    store = Store(":memory:")
    _nacional(TseUmaUfPorVez(["AA", "AB"]), store)
    _nacional(TseUmaUfPorVez(["AB"]), store)  # retomada que só refaz AB
    assert {f.atributos["uf"] for f in store.facts_by_tipo("candidatura")} == {"AA", "AB"}


def test_regravar_a_uf_remove_a_candidatura_que_sumiu_dela():
    store = Store(":memory:")
    _nacional(TseUmaUfPorVez(["AA"]), store)

    class UmaSo(TseUmaUfPorVez):
        def fetch_por_uf(self, *a, **k):
            yield _parte("AA", n=1)

    _nacional(UmaSo([]), store)
    assert {f.chave for f in store.facts_by_tipo("candidatura")} == {"AA0"}


def test_relatorio_soma_as_ufs():
    _, rel = _nacional(TseUmaUfPorVez(["AA", "AB"]))
    assert rel["tse"]["candidaturas"]["total"] == 4


def test_fonte_sem_fetch_por_uf_continua_funcionando_pelo_fetch():
    class Antiga(Source):  # só `fetch` (como as fontes falsas e as antigas), sem fetch_por_uf
        nome = "tse"

        def fetch(self, uf=None, ano=2022, conjuntos=CONJ):
            return _parte("AA")

        def normalize(self, raw):
            return TseSource(client=object()).normalize(raw)

    store, _ = _nacional(Antiga())
    assert {f.chave for f in store.facts_by_tipo("candidatura")} == {"AA0", "AA1"}


def test_com_escopo_de_uf_continua_chamando_fetch_da_uf():
    chamadas: list[dict] = []

    class Escopo(TseUmaUfPorVez):
        def fetch(self, uf=None, ano=2022, conjuntos=CONJ):
            chamadas.append({"uf": uf})
            return _parte(uf)

    store = Store(":memory:")
    store.upsert_facts([Fact(tipo="deputado", chave="1", fonte="t", id_oficial="1",
                             url="https://x", atributos={"nome": "A", "uf": "AB",
                                                         "partido": "PX"})])
    pipe = Pipeline(store, Opcoes(fontes=("tse",), uf="AB"), registry={"tse": lambda: Escopo([])},
                    log=lambda _: None)
    pipe.executar()
    assert chamadas == [{"uf": "AB"}]


# ---------- ponta a ponta com a fonte real e zips falsos ----------

def test_pipeline_nacional_com_zips_falsos_grava_por_uf_e_deixa_bruto_por_uf(raw_dir):
    src = TseSource(client=_servidor(_zips()))
    store, rel = _nacional(src)
    nomes = sorted(p.name for p in (raw_dir / "tse").glob("*.json"))
    assert nomes == ["tse_2022_AC.json", "tse_2022_MG.json"]
    assert len(store.facts_by_tipo("candidatura")) == rel["tse"]["candidaturas_gravadas"] == 4


def test_pipeline_nacional_retomado_nao_baixa_de_novo_a_uf_gravada(raw_dir):
    _nacional(TseSource(client=_servidor(_zips())))
    store, rel = _nacional(TseSource(client=_servidor(_zips())), reusar_raw=True)
    assert len(store.facts_by_tipo("candidatura")) == 4 and rel["tse"]["candidaturas"]["total"] == 4


# ---------- --reusar-raw também com escopo (make sample) ----------

def _dep_ac() -> Fact:
    return Fact(tipo="deputado", chave="1", fonte="t", id_oficial="1", url="https://x",
                atributos={"nome": "A", "uf": "AC", "partido": "PX"})


def _escopo_ac(src: TseSource, **kw) -> tuple[Store, dict]:
    store = Store(":memory:")
    store.upsert_facts([_dep_ac()])
    pipe = Pipeline(store, Opcoes(fontes=("tse",), uf="AC", **kw), registry={"tse": lambda: src},
                    log=lambda _: None)
    return store, pipe.executar()


def test_com_escopo_reusar_raw_le_o_bruto_da_uf_do_disco_e_da_o_mesmo_resultado(raw_dir):
    s1, rel1 = _escopo_ac(TseSource(client=_servidor(_zips())))
    s2, rel2 = _escopo_ac(TseSource(client=ClienteQueFalha()), reusar_raw=True)  # nada de rede
    assert rel1["tse"] == rel2["tse"]
    assert ({(f.tipo, f.chave) for f in s1.load_facts()}
            == {(f.tipo, f.chave) for f in s2.load_facts()})
    assert rel1["tse"]["candidaturas"]["total"] == 4  # as 4 candidaturas da UF foram lidas


def test_com_escopo_sem_reusar_raw_baixa_mesmo_com_bruto_em_disco(raw_dir, monkeypatch):
    _escopo_ac(TseSource(client=_servidor(_zips())))
    abertos = _contar_membros(monkeypatch)
    _escopo_ac(TseSource(client=_servidor(_zips())))
    assert any("_AC." in m for m in abertos)


def test_bruto_de_disco_e_lido_uma_vez_por_uf(raw_dir, monkeypatch):
    list(TseSource(client=_servidor(_zips())).fetch_por_uf("AC", conjuntos=CONJ))
    lidos: list[str] = []
    original = TseSource._parte_em_disco

    def conta(self, uf, ano, conjuntos):
        lidos.append(uf)
        return original(self, uf, ano, conjuntos)

    monkeypatch.setattr(TseSource, "_parte_em_disco", conta)
    list(TseSource(client=ClienteQueFalha()).fetch_por_uf("AC", conjuntos=CONJ, reusar_raw=True))
    list(TseSource(client=_servidor(_zips())).fetch_por_uf(conjuntos=CONJ, reusar_raw=True))
    assert lidos == ["AC", "AC", "MG"]  # 1 leitura por UF em cada chamada
