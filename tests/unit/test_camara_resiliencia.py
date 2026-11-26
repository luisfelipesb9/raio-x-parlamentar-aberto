"""CamaraSource: nova tentativa com espera, pausa entre chamadas e escopo dos deputados.

Nenhum teste toca a rede nem `data/raw`: o cliente é um `httpx.MockTransport` e os brutos vão
para uma pasta temporária.
"""
from __future__ import annotations

import httpx
import pytest

import sources.base
from sources.camara.source import BASE, CamaraSource


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


class Servidor:
    """Responde, em ordem, o que `respostas` manda (resposta, ou exceção para levantar)."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.pedidos: list[httpx.Request] = []
        self.client = httpx.Client(transport=httpx.MockTransport(self._handler))

    def _handler(self, req: httpx.Request) -> httpx.Response:
        self.pedidos.append(req)
        r = self.respostas.pop(0) if len(self.respostas) > 1 else self.respostas[0]
        if isinstance(r, Exception):
            raise r
        return r


def _ok(dados=None):
    return httpx.Response(200, json={"dados": dados if dados is not None else [{"id": 1}],
                                     "links": []})


def _fonte(servidor: Servidor, **kw) -> tuple[CamaraSource, list[float]]:
    dormidos: list[float] = []
    kw.setdefault("pausa", 0)
    return CamaraSource(client=servidor.client, dormir=dormidos.append, **kw), dormidos


# ---------- nova tentativa ----------

def test_429_respeita_retry_after_e_tenta_de_novo():
    s = Servidor(httpx.Response(429, headers={"Retry-After": "7"}), _ok())
    fonte, dormidos = _fonte(s)
    assert fonte._get_all("/deputados") == [{"id": 1}]
    assert len(s.pedidos) == 2
    assert 7.0 in dormidos


def test_5xx_espera_exponencial_ate_dar_certo():
    s = Servidor(httpx.Response(500), httpx.Response(502), httpx.Response(503), _ok())
    fonte, dormidos = _fonte(s, espera_base=2.0)
    assert fonte._get_all("/deputados") == [{"id": 1}]
    assert len(s.pedidos) == 4
    assert [d for d in dormidos if d > 0] == [2.0, 4.0, 8.0]


def test_timeout_e_erro_de_rede_tambem_sao_retentados():
    req = httpx.Request("GET", BASE)
    s = Servidor(httpx.ReadTimeout("lento", request=req),
                 httpx.ConnectError("caiu", request=req), _ok())
    fonte, _ = _fonte(s)
    assert fonte._get_all("/deputados") == [{"id": 1}]
    assert len(s.pedidos) == 3


def test_esgotadas_as_tentativas_o_erro_sobe_e_nao_ha_loop_infinito():
    s = Servidor(httpx.Response(503))
    fonte, _ = _fonte(s, max_tentativas=3)
    with pytest.raises(httpx.HTTPStatusError, match="503"):
        fonte._get_all("/deputados")
    assert len(s.pedidos) == 3


def test_timeout_persistente_sobe_o_erro_original():
    req = httpx.Request("GET", BASE)
    s = Servidor(httpx.ReadTimeout("lento", request=req))
    fonte, _ = _fonte(s, max_tentativas=2)
    with pytest.raises(httpx.ReadTimeout):
        fonte._get_all("/deputados")
    assert len(s.pedidos) == 2


@pytest.mark.parametrize("status", [400, 404])
def test_erro_de_cliente_nao_e_retentado(status):
    s = Servidor(httpx.Response(status))
    fonte, dormidos = _fonte(s)
    with pytest.raises(httpx.HTTPStatusError):
        fonte._get_all("/votacoes")
    assert len(s.pedidos) == 1
    assert [d for d in dormidos if d > 0] == []


def test_espera_nunca_passa_de_um_minuto():
    s = Servidor(httpx.Response(429, headers={"Retry-After": "9999"}), _ok())
    fonte, dormidos = _fonte(s)
    fonte._get_all("/deputados")
    assert max(dormidos) == 60.0


def test_retry_after_que_nao_e_numero_cai_na_espera_exponencial():
    s = Servidor(httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}), _ok())
    fonte, dormidos = _fonte(s, espera_base=3.0)
    fonte._get_all("/deputados")
    assert [d for d in dormidos if d > 0] == [3.0]


def test_paginacao_segue_o_link_next_com_nova_tentativa_em_cada_pagina():
    p2 = "https://dadosabertos.camara.leg.br/api/v2/deputados?pagina=2"
    s = Servidor(
        httpx.Response(200, json={"dados": [{"id": 1}], "links": [{"rel": "next", "href": p2}]}),
        httpx.Response(500),
        _ok([{"id": 2}]))
    fonte, _ = _fonte(s)
    assert fonte._get_all("/deputados") == [{"id": 1}, {"id": 2}]


# ---------- pausa entre chamadas ----------

def test_pausa_padrao_respeita_o_servidor():
    assert CamaraSource(client=httpx.Client()).pausa >= 0.2


def test_pausa_entre_chamadas_e_cumprida_apos_cada_resposta():
    s = Servidor(_ok())
    fonte, dormidos = _fonte(s, pausa=0.35)
    fonte._get_all("/deputados")
    fonte._get_all("/deputados")
    assert dormidos == [0.35, 0.35]


# ---------- escopo: em exercício (513) por padrão, legislatura inteira só por opção ----------

def _api_deputados():
    pedidos: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        pedidos.append(req)
        return httpx.Response(200, json={"dados": [], "links": []})

    return pedidos, httpx.Client(transport=httpx.MockTransport(handler))


def test_padrao_baixa_deputados_em_exercicio_sem_id_de_legislatura(raw_dir):
    pedidos, client = _api_deputados()
    CamaraSource(client=client, pausa=0).fetch(max_votacoes=0)
    lista = next(p for p in pedidos if p.url.path.endswith("/deputados"))
    assert "idLegislatura" not in lista.url.params


def test_legislatura_completa_so_por_opcao_explicita(raw_dir):
    pedidos, client = _api_deputados()
    CamaraSource(client=client, pausa=0).fetch(max_votacoes=0, legislatura_completa=True)
    lista = next(p for p in pedidos if p.url.path.endswith("/deputados"))
    assert lista.url.params["idLegislatura"] == "57"


def test_legislatura_completa_aceita_outra_legislatura(raw_dir):
    pedidos, client = _api_deputados()
    CamaraSource(client=client, pausa=0).fetch(max_votacoes=0, legislatura=56,
                                               legislatura_completa=True)
    lista = next(p for p in pedidos if p.url.path.endswith("/deputados"))
    assert lista.url.params["idLegislatura"] == "56"


def test_legislatura_sozinha_sem_a_opcao_nao_amplia_o_escopo(raw_dir):
    """`legislatura=57` é o valor padrão antigo: não pode reabrir o escopo de 878 sem querer."""
    pedidos, client = _api_deputados()
    CamaraSource(client=client, pausa=0).fetch(max_votacoes=0, legislatura=57)
    lista = next(p for p in pedidos if p.url.path.endswith("/deputados"))
    assert "idLegislatura" not in lista.url.params
