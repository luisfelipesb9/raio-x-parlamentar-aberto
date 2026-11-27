"""Ponto de extensão da Receita no pipeline: `ProvedorCnpj`.

Hoje o único provedor é a BrasilAPI (um CNPJ por consulta, limitado por `--limite-rfb`). O ponto
de extensão existe para um futuro provedor "arquivo mensal filtrado" (varre o cadastro aberto da
Receita em streaming, sem chamar a BrasilAPI em massa). Aqui só há provedores falsos.
"""
from __future__ import annotations

import pytest

from contracts import Fact
from ingest.pipeline import Opcoes, Pipeline, ProvedorBrasilApi, ResultadoCnpj
from repo.store import Store
from sources.base import Source

A, B, C = "00000000000191", "33000167000101", "12ABC34501DE35"  # válidos: BB, Petrobras, alfa


def _fato(tipo, chave, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def _loja() -> Store:
    s = Store(":memory:")
    s.upsert_facts([
        _fato("despesa_ceap", "d1", deputado_id="1", cnpj=A, valor=300.0),
        _fato("despesa_ceap", "d2", deputado_id="1", cnpj=B, valor=200.0),
        _fato("despesa_ceap", "d3", deputado_id="1", cnpj=C, valor=100.0),
        _fato("despesa_ceap", "d4", deputado_id="1", cnpj="00000000000192", valor=9e9),  # DV ruim
    ])
    return s


class ProvedorFalso:
    def __init__(self, em_massa: bool, indisponiveis: list[str] | None = None):
        self.em_massa = em_massa
        self.pedidos: list[tuple[list[str], bool]] = []
        self._indisp = indisponiveis or []

    def buscar(self, cnpjs, reusar_raw):
        self.pedidos.append((list(cnpjs), reusar_raw))
        return ResultadoCnpj(
            fatos=[_fato("empresa", c, razao_social=f"EMPRESA {c}") for c in cnpjs
                   if c not in self._indisp],
            indisponiveis=[c for c in cnpjs if c in self._indisp])


def _rodar(provedor, **kw):
    store = _loja()
    log: list[str] = []
    pipe = Pipeline(store, Opcoes(fontes=("rfb",), **kw), provedor_rfb=provedor, log=log.append)
    return store, pipe.executar(), log


def test_provedor_limitado_recebe_so_os_n_cnpjs_de_maior_valor():
    prov = ProvedorFalso(em_massa=False)
    store, rel, _ = _rodar(prov, limite_rfb=2)
    assert prov.pedidos == [([A, B], False)]
    assert {f.chave for f in store.facts_by_tipo("empresa")} == {A, B}
    assert rel["rfb"]["consultados"] == 2 and rel["rfb"]["empresas"] == 2


def test_provedor_em_massa_recebe_todos_os_cnpjs_validos_sem_o_limite():
    prov = ProvedorFalso(em_massa=True)
    store, rel, _ = _rodar(prov, limite_rfb=1)
    assert prov.pedidos == [([A, B, C], False)]  # o de DV ruim fica de fora; o limite não vale
    assert {f.chave for f in store.facts_by_tipo("empresa")} == {A, B, C}
    assert rel["rfb"]["consultados"] == 3


def test_limite_zero_desliga_a_receita_inclusive_para_provedor_em_massa():
    prov = ProvedorFalso(em_massa=True)
    _, rel, _ = _rodar(prov, limite_rfb=0)
    assert prov.pedidos == [] and rel["rfb"] == {"consultados": 0}


def test_reusar_raw_chega_ao_provedor():
    prov = ProvedorFalso(em_massa=False)
    _rodar(prov, limite_rfb=1, reusar_raw=True)
    assert prov.pedidos == [([A], True)]


def test_empresa_ja_gravada_nao_e_pedida_de_novo_ao_provedor():
    prov = ProvedorFalso(em_massa=False)
    store = _loja()
    store.upsert_facts([_fato("empresa", A, razao_social="JÁ TEM")])
    Pipeline(store, Opcoes(fontes=("rfb",), limite_rfb=3), provedor_rfb=prov,
             log=lambda _: None).executar()
    assert prov.pedidos == [([B, C], False)]


def test_indisponiveis_do_provedor_vao_para_o_relatorio_e_o_log():
    prov = ProvedorFalso(em_massa=False, indisponiveis=[B])
    _, rel, log = _rodar(prov, limite_rfb=2)
    assert rel["rfb"]["indisponiveis"] == [B] and rel["rfb"]["empresas"] == 1
    assert any("ATENÇÃO" in linha and B in linha for linha in log)


def test_sem_provedor_explicito_o_padrao_e_a_brasilapi_da_fonte_registrada():
    chamadas: list[dict] = []

    class FakeRfb(Source):
        nome = "rfb"

        def fetch(self, cnpjs, reusar_raw=False):
            chamadas.append({"cnpjs": list(cnpjs), "reusar_raw": reusar_raw})
            return {"cnpjs": list(cnpjs), "indisponiveis": [B]}

        def normalize(self, raw):
            return [_fato("empresa", c, razao_social=c) for c in raw["cnpjs"]]

    store = _loja()
    rel = Pipeline(store, Opcoes(fontes=("rfb",), limite_rfb=2), registry={"rfb": FakeRfb},
                   log=lambda _: None).executar()
    assert chamadas == [{"cnpjs": [A, B], "reusar_raw": False}]
    assert rel["rfb"]["indisponiveis"] == [B]


def test_provedor_brasilapi_nao_e_em_massa():
    class Fonte(Source):
        nome = "rfb"

        def fetch(self, cnpjs):
            return {"cnpjs": []}

        def normalize(self, raw):
            return []

    assert ProvedorBrasilApi(Fonte()).em_massa is False


def test_provedor_brasilapi_respeita_a_assinatura_do_fetch_da_fonte():
    # fonte antiga sem `reusar_raw`: o argumento não é passado (montar_kwargs)
    vistos: list[list[str]] = []

    class Antiga(Source):
        nome = "rfb"

        def fetch(self, cnpjs):
            vistos.append(list(cnpjs))
            return {"cnpjs": list(cnpjs)}

        def normalize(self, raw):
            return [_fato("empresa", c) for c in raw["cnpjs"]]

    r = ProvedorBrasilApi(Antiga()).buscar([A], reusar_raw=True)
    assert vistos == [[A]] and [f.chave for f in r.fatos] == [A] and r.indisponiveis == []


@pytest.mark.parametrize("campo", ["fatos", "indisponiveis"])
def test_resultado_cnpj_tem_padroes_independentes(campo):
    a, b = ResultadoCnpj(fatos=[]), ResultadoCnpj(fatos=[])
    getattr(a, campo).append("x")
    assert getattr(b, campo) == []
