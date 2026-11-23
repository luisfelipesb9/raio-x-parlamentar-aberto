"""RfbSource — empresas e quadro societário via BrasilAPI (https://brasilapi.com.br/api/cnpj/v1/).

Só consulta a lista de CNPJs recebida (a base completa da RFB, 17 GB, nunca é baixada).
Fixtures REAIS: respostas da BrasilAPI para o Banco do Brasil (00000000000191) e a Petrobras
(33000167000101) — são empresas públicas; o QSA foi recortado para as primeiras linhas e o
`regime_tributario`/`cnaes_secundarios` para 1 item, sem outra alteração — e o corpo real do 404
(`rfb_cnpj_404.json`, CNPJ válido inexistente). O CPF dos sócios já vem mascarado pela Receita
(`***101202**`). Casos de borda sem resposta real equivalente (sócio PJ, nome duplicado, CPF
inválido) são derivados de uma resposta real mudando só o campo testado.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import httpx
import pytest

import sources.base
from sources.rfb.source import FONTE, RfbSource

FIX = Path(__file__).parent / "fixtures"
BASE = "https://brasilapi.com.br/api/cnpj/v1"
BB, PETRO, INEXISTENTE = "00000000000191", "33000167000101", "99999999000191"


def _json(nome: str) -> dict:
    return json.loads((FIX / nome).read_text(encoding="utf-8"))


@pytest.fixture
def bb() -> dict:
    return _json("rfb_cnpj_00000000000191.json")


@pytest.fixture
def petro() -> dict:
    return _json("rfb_cnpj_33000167000101.json")


@pytest.fixture
def fonte() -> RfbSource:
    return RfbSource(client=object())  # normalize é puro: não usa o client


def _por_chave(facts, tipo: str | None = None):
    return {f.chave: f for f in facts if tipo is None or f.tipo == tipo}


# ---------- normalize: empresa ----------

def test_empresa_tem_atributos_exatos_do_contrato(fonte, bb):
    f = _por_chave(fonte.normalize({"cnpjs": [bb]}), "empresa")[BB]
    assert f.tipo == "empresa" and f.fonte == FONTE == "brasilapi_cnpj" and f.id_oficial == BB
    assert f.url == f"{BASE}/{BB}"
    assert f.atributos == {
        "razao_social": "BANCO DO BRASIL SA", "situacao": "ATIVA", "cnae": "6422100",
        "municipio_ibge": "5300108", "nome_fantasia": "DIRECAO GERAL", "uf": "DF",
        "abertura": "1966-08-01",
    }


def test_cnae_com_menos_de_7_digitos_e_completado_com_zeros(fonte, petro):
    a = _por_chave(fonte.normalize({"cnpjs": [petro]}), "empresa")[PETRO].atributos
    assert a["cnae"] == "0600001" and a["municipio_ibge"] == "3304557"


def test_empresa_sem_codigo_de_municipio_ibge_fica_com_none(fonte, bb):
    bb["codigo_municipio_ibge"] = None
    a = _por_chave(fonte.normalize({"cnpjs": [bb]}), "empresa")[BB].atributos
    assert a["municipio_ibge"] is None


def test_cnpj_invalido_na_resposta_e_descartado(fonte, bb):
    bb["cnpj"] = "123"
    assert fonte.normalize({"cnpjs": [bb]}) == []


# ---------- normalize: sócios ----------

def test_socio_preserva_cpf_mascarado_com_asteriscos(fonte, bb):
    socios = _por_chave(fonte.normalize({"cnpjs": [bb]}), "socio")
    f = socios[f"{BB}:ADRIANO CASSIO GUERRA DE OLIVEIRA"]
    assert f.fonte == FONTE and f.id_oficial == BB and f.url == f"{BASE}/{BB}"
    assert f.atributos == {
        "cnpj": BB, "nome": "ADRIANO CASSIO GUERRA DE OLIVEIRA", "cpf_cnpj": "***101202**",
        "qualificacao": "Diretor", "tipo_socio": "PF", "entrada": "2023-05-17",
    }
    assert len(socios) == 3


def test_socio_pessoa_juridica_traz_cnpj_inteiro_e_tipo_pj(fonte, bb):
    bb["qsa"][0].update(cnpj_cpf_do_socio="33000167000101", identificador_de_socio=1,
                        nome_socio="PETROLEO BRASILEIRO S A PETROBRAS")
    a = _por_chave(fonte.normalize({"cnpjs": [bb]}), "socio")[
        f"{BB}:PETROLEO BRASILEIRO S A PETROBRAS"].atributos
    assert a["cpf_cnpj"] == "33000167000101" and a["tipo_socio"] == "PJ"


def test_chave_do_socio_usa_nome_sem_acento_maiusculo_e_espacos_unicos(fonte, bb):
    bb["qsa"][0]["nome_socio"] = "  José   da Silva "
    socios = _por_chave(fonte.normalize({"cnpjs": [bb]}), "socio")
    assert f"{BB}:JOSE DA SILVA" in socios
    assert socios[f"{BB}:JOSE DA SILVA"].atributos["nome"] == "José da Silva"


def test_dois_socios_com_o_mesmo_nome_nao_colidem(fonte, bb):
    bb["qsa"][1]["nome_socio"] = bb["qsa"][0]["nome_socio"]
    socios = [f for f in fonte.normalize({"cnpjs": [bb]}) if f.tipo == "socio"]
    assert len(socios) == 3 and len({f.chave for f in socios}) == 3
    assert {f.chave for f in socios} >= {f"{BB}:ADRIANO CASSIO GUERRA DE OLIVEIRA",
                                         f"{BB}:ADRIANO CASSIO GUERRA DE OLIVEIRA#2"}


@pytest.mark.parametrize("lixo", ["abc", "***12**", "", None, "123456789012"])
def test_documento_de_socio_invalido_vira_none_e_o_socio_continua(fonte, bb, lixo):
    bb["qsa"][0]["cnpj_cpf_do_socio"] = lixo
    f = _por_chave(fonte.normalize({"cnpjs": [bb]}), "socio")[
        f"{BB}:ADRIANO CASSIO GUERRA DE OLIVEIRA"]
    assert f.atributos["cpf_cnpj"] is None


def test_socio_sem_nome_e_descartado(fonte, bb):
    bb["qsa"][0]["nome_socio"] = "  "
    assert len([f for f in fonte.normalize({"cnpjs": [bb]}) if f.tipo == "socio"]) == 2


@pytest.mark.parametrize("qsa", [[], None])
def test_empresa_sem_qsa_gera_so_a_empresa(fonte, bb, qsa):
    bb["qsa"] = qsa
    assert [f.tipo for f in fonte.normalize({"cnpjs": [bb]})] == ["empresa"]


def test_varias_empresas_e_raw_vazio(fonte, bb, petro):
    facts = fonte.normalize({"cnpjs": [bb, petro]})
    assert {f.chave for f in facts if f.tipo == "empresa"} == {BB, PETRO}
    assert all(f.fonte and f.id_oficial and f.url for f in facts)
    assert fonte.normalize({}) == []


# ---------- fetch ----------

@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


class Servidor:
    """Responde por CNPJ com uma fila de respostas (a última se repete)."""

    def __init__(self, respostas: dict[str, list[httpx.Response | Exception]]):
        self.respostas = {k: list(v) for k, v in respostas.items()}
        self.chamadas: list[str] = []

    def client(self) -> httpx.Client:
        def handler(request: httpx.Request) -> httpx.Response:
            self.chamadas.append(str(request.url))
            fila = self.respostas[str(request.url).rsplit("/", 1)[1]]
            r = fila.pop(0) if len(fila) > 1 else fila[0]
            if isinstance(r, Exception):
                raise r
            return r
        return httpx.Client(transport=httpx.MockTransport(handler))


def _ok(dados: dict) -> httpx.Response:
    return httpx.Response(200, json=dados)


def _rfb(servidor: Servidor, **kw) -> tuple[RfbSource, list[float]]:
    sono: list[float] = []
    return RfbSource(client=servidor.client(), dormir=sono.append, **kw), sono


def test_fetch_consulta_so_os_cnpjs_pedidos_normaliza_mascara_e_remove_repetidos(
        raw_dir, bb, petro):
    srv = Servidor({BB: [_ok(bb)], PETRO: [_ok(petro)]})
    rfb, _ = _rfb(srv)
    out = rfb.fetch(["00.000.000/0001-91", PETRO, BB])
    assert srv.chamadas == [f"{BASE}/{BB}", f"{BASE}/{PETRO}"]
    assert all(re.fullmatch(rf"{re.escape(BASE)}/\d{{14}}", u) for u in srv.chamadas)
    assert [e["cnpj"] for e in out["cnpjs"]] == [BB, PETRO]
    assert out["nao_encontrados"] == []
    assert json.loads((raw_dir / "rfb" / f"{BB}.json").read_text(encoding="utf-8"))["cnpj"] == BB


def test_fetch_e_normalize_ponta_a_ponta(raw_dir, bb, fonte):
    rfb, _ = _rfb(Servidor({BB: [_ok(bb)]}))
    facts = fonte.normalize(rfb.fetch([BB]))
    assert {f.tipo for f in facts} == {"empresa", "socio"} and len(facts) == 4


def test_fetch_cnpj_inexistente_vai_para_nao_encontrados_e_segue(raw_dir, bb):
    srv = Servidor({INEXISTENTE: [httpx.Response(404, json=_json("rfb_cnpj_404.json"))],
                    BB: [_ok(bb)]})
    rfb, _ = _rfb(srv)
    out = rfb.fetch([INEXISTENTE, BB])
    assert out["nao_encontrados"] == [INEXISTENTE]
    assert [e["cnpj"] for e in out["cnpjs"]] == [BB]


def test_fetch_pausa_entre_consultas_mas_nao_antes_da_primeira(raw_dir, bb, petro):
    rfb, sono = _rfb(Servidor({BB: [_ok(bb)], PETRO: [_ok(petro)]}), pausa=0.7)
    rfb.fetch([BB, PETRO])
    assert sono == [0.7]


def test_fetch_429_respeita_retry_after_e_tenta_de_novo(raw_dir, bb):
    limite = httpx.Response(429, headers={"retry-after": "3"}, json={"message": "limite"})
    srv = Servidor({BB: [limite, limite, _ok(bb)]})
    rfb, sono = _rfb(srv)
    out = rfb.fetch([BB])
    assert len(srv.chamadas) == 3 and sono == [3.0, 3.0]
    assert len(out["cnpjs"]) == 1


def test_fetch_429_sem_retry_after_usa_espera_exponencial(raw_dir, bb):
    limite = httpx.Response(429)
    rfb, sono = _rfb(Servidor({BB: [limite, limite, _ok(bb)]}), espera_base=2.0)
    rfb.fetch([BB])
    assert sono == [2.0, 4.0]


def test_fetch_429_persistente_desiste_com_erro_apos_max_tentativas(raw_dir):
    srv = Servidor({BB: [httpx.Response(429)]})
    rfb, sono = _rfb(srv, max_tentativas=3)
    with pytest.raises(httpx.HTTPStatusError) as exc:
        rfb.fetch([BB])
    assert exc.value.response.status_code == 429
    assert len(srv.chamadas) == 3 and len(sono) == 2
    assert list((raw_dir / "rfb").glob("*")) == []  # nada salvo


def test_fetch_erro_5xx_e_timeout_sao_retentados(raw_dir, bb, petro):
    srv = Servidor({BB: [httpx.Response(503), _ok(bb)],
                    PETRO: [httpx.ConnectTimeout("lento"), _ok(petro)]})
    rfb, _ = _rfb(srv)
    out = rfb.fetch([BB, PETRO])
    assert [e["cnpj"] for e in out["cnpjs"]] == [BB, PETRO]


def test_fetch_5xx_persistente_em_um_cnpj_vai_para_indisponiveis_e_o_lote_segue(
        raw_dir, bb, petro, caplog):
    srv = Servidor({BB: [httpx.Response(503)], PETRO: [_ok(petro)]})
    rfb, _ = _rfb(srv, max_tentativas=3)
    with caplog.at_level("WARNING", logger="sources.rfb.source"):
        out = rfb.fetch([BB, PETRO])
    assert out["indisponiveis"] == [BB]
    assert [e["cnpj"] for e in out["cnpjs"]] == [PETRO]
    assert out["nao_encontrados"] == []
    assert srv.chamadas.count(f"{BASE}/{BB}") == 3  # esgotou as tentativas antes de desistir
    assert not (raw_dir / "rfb" / f"{BB}.json").exists()  # nada salvo para o indisponível
    assert BB in caplog.text


def test_fetch_timeout_persistente_tambem_vai_para_indisponiveis(raw_dir, bb, petro):
    srv = Servidor({BB: [httpx.ConnectTimeout("lento")], PETRO: [_ok(petro)]})
    rfb, _ = _rfb(srv, max_tentativas=2)
    out = rfb.fetch([BB, PETRO])
    assert out["indisponiveis"] == [BB]
    assert [e["cnpj"] for e in out["cnpjs"]] == [PETRO]


def test_fetch_5xx_persistente_gera_so_os_fatos_dos_cnpjs_disponiveis(raw_dir, bb, petro, fonte):
    rfb, _ = _rfb(Servidor({BB: [httpx.Response(503)], PETRO: [_ok(petro)]}), max_tentativas=2)
    facts = fonte.normalize(rfb.fetch([BB, PETRO]))
    assert {f.chave for f in facts if f.tipo == "empresa"} == {PETRO}


@pytest.mark.parametrize("falha", [httpx.Response(503), httpx.ConnectError("sem rede")])
def test_fetch_falhas_seguidas_abortam_o_lote(raw_dir, falha):
    srv = Servidor({BB: [falha], PETRO: [falha], INEXISTENTE: [falha]})
    rfb, _ = _rfb(srv, max_tentativas=2, max_indisponiveis_seguidos=2)
    with pytest.raises(RuntimeError, match="2 CNPJs seguidos"):
        rfb.fetch([BB, PETRO, INEXISTENTE])
    assert f"{BASE}/{INEXISTENTE}" not in srv.chamadas  # parou sem insistir no resto


def test_fetch_resposta_entre_duas_falhas_zera_a_contagem(raw_dir, bb):
    falha = httpx.Response(503)
    srv = Servidor({PETRO: [falha], BB: [_ok(bb)], INEXISTENTE: [falha]})
    rfb, _ = _rfb(srv, max_tentativas=2, max_indisponiveis_seguidos=2)
    out = rfb.fetch([PETRO, BB, INEXISTENTE])
    assert out["indisponiveis"] == [PETRO, INEXISTENTE]
    assert [e["cnpj"] for e in out["cnpjs"]] == [BB]


def test_limite_padrao_de_falhas_seguidas_e_tres():
    assert RfbSource(client=object()).max_indisponiveis_seguidos == 3  # type: ignore[arg-type]


def test_fetch_400_nao_e_retentado(raw_dir):
    srv = Servidor({BB: [httpx.Response(400, json={"message": "inválido"})]})
    rfb, sono = _rfb(srv)
    with pytest.raises(httpx.HTTPStatusError):
        rfb.fetch([BB])
    assert len(srv.chamadas) == 1 and sono == []


@pytest.mark.parametrize("cnpj", ["123", "11111111111111", "abc", "0000000000019"])
def test_fetch_cnpj_invalido_vai_para_invalidos_sem_requisicao_e_o_lote_segue(
        raw_dir, bb, petro, cnpj):
    srv = Servidor({BB: [_ok(bb)], PETRO: [_ok(petro)]})
    rfb, _ = _rfb(srv)
    out = rfb.fetch([BB, cnpj, PETRO])
    assert srv.chamadas == [f"{BASE}/{BB}", f"{BASE}/{PETRO}"]
    assert [e["cnpj"] for e in out["cnpjs"]] == [BB, PETRO]
    assert out["invalidos"] == [cnpj]  # como recebido, para o chamador achar o erro


def test_fetch_so_cnpjs_invalidos_nao_consulta_nada_e_nao_levanta(raw_dir):
    srv = Servidor({})
    rfb, sono = _rfb(srv)
    out = rfb.fetch(["11111111111111", "x"])
    assert out == {"cnpjs": [], "nao_encontrados": [], "invalidos": ["11111111111111", "x"],
                   "indisponiveis": []}
    assert srv.chamadas == [] and sono == []


def test_fetch_com_lista_vazia_nao_consulta_nada(raw_dir):
    srv = Servidor({})
    rfb, _ = _rfb(srv)
    assert rfb.fetch([]) == {"cnpjs": [], "nao_encontrados": [], "invalidos": [],
                             "indisponiveis": []}
    assert srv.chamadas == []


def test_fetch_exige_a_lista_de_cnpjs():
    with pytest.raises(TypeError):
        RfbSource(client=object()).fetch()  # type: ignore[call-arg]


def test_fetch_devolve_a_resposta_da_api_sem_alterar(raw_dir, bb):
    original = copy.deepcopy(bb)
    rfb, _ = _rfb(Servidor({BB: [_ok(bb)]}))
    assert rfb.fetch([BB])["cnpjs"] == [original]
