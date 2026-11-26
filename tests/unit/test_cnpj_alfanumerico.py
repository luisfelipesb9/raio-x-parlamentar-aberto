"""CNPJ alfanumérico (Receita Federal, a partir de julho/2026).

Fonte oficial: "Perguntas & Respostas - Novo CNPJ Alfanumérico" (Receita Federal), pergunta 14:
14 posições, as 12 primeiras em A-Z/0-9 e as 2 últimas (DV) numéricas; DV por módulo 11 sobre o
código ASCII do caractere menos 48; os formatos numérico e alfanumérico coexistem.

Os CNPJs válidos abaixo vêm do próprio documento da Receita (o exemplo resolvido da pergunta 14,
12.ABC.345/01DE-35, e os exemplos das perguntas 17 e 23: 12.345.678/0001-95, AA345678/000A-29,
12.345.678/000A-08) ou foram calculados à mão, a partir da regra, FORA do código testado
(ZZ9Z0000AB12-77, 123456AB000C-81 e 1A345678000A-50). Nenhum é CNPJ real de empresa.
"""
from __future__ import annotations

import json

import httpx
import pytest

import sources.base
from contracts import Fact
from ingest.pipeline import Opcoes, Pipeline
from ingest.resolve import resolver_cnpj
from ingest.resolve.comum import cnpj_valido as cnpj_valido_ingest
from repo.store import Store
from sources.ceap.source import CeapSource, _documento_fornecedor
from sources.rfb.normalizacao import cnpj_valido, dv_cnpj, normalizar_cnpj
from sources.rfb.source import RfbSource
from sources.tse.source import TseSource

# (formato limpo, válido pela regra oficial)
ALFA = "12ABC34501DE35"          # exemplo resolvido da pergunta 14 do documento da Receita
ALFA_RAIZ_E_ORDEM = "AA345678000A29"  # pergunta 23, Ex2 (raiz alfanumérica, ordem alfanumérica)
ALFA_SO_ORDEM = "12345678000A08"      # pergunta 23, Ex3 (raiz numérica, ordem alfanumérica)
ALFA_TRES_LETRAS = "123456AB000C81"   # tirando as letras sobram 11 dígitos (parece CPF)
ALFA_ZZ = "ZZ9Z0000AB1277"
NUMERICO = "12345678000195"           # pergunta 17
BB = "00000000000191"
PETRO = "33000167000101"


# ---------- dígito verificador: algoritmo oficial ----------

def test_dv_do_exemplo_oficial_da_receita_e_35():
    assert dv_cnpj("12ABC34501DE") == "35"


def test_dv_do_primeiro_digito_e_do_segundo_do_exemplo_oficial():
    # o documento mostra os dois passos: soma 459 -> dv1 = 3; soma 424 -> dv2 = 5
    assert dv_cnpj("12ABC34501DE")[0] == "3"
    assert dv_cnpj("12ABC34501DE")[1] == "5"


@pytest.mark.parametrize("base, dv", [
    ("AA345678000A", "29"), ("12345678000A", "08"), ("123456AB000C", "81"),
    ("1A345678000A", "50"), ("ZZ9Z0000AB12", "77"),
    ("123456780001", "95"), ("000000000001", "91"), ("330001670001", "01"),  # numéricos
])
def test_dv_confere_com_o_calculo_feito_a_mao(base, dv):
    assert dv_cnpj(base) == dv


def test_dv_exige_exatamente_12_posicoes_alfanumericas():
    for ruim in ("12ABC34501D", "12ABC34501DE3", "12ABC3450-DE", "", "12abc34501de"):
        with pytest.raises(ValueError):
            dv_cnpj(ruim)


# ---------- validação ----------

@pytest.mark.parametrize("cnpj", [ALFA, ALFA_RAIZ_E_ORDEM, ALFA_SO_ORDEM, ALFA_TRES_LETRAS,
                                  ALFA_ZZ, NUMERICO, BB, PETRO])
def test_cnpj_valido_aceita_numerico_e_alfanumerico_com_dv_correto(cnpj):
    assert cnpj_valido(cnpj)


@pytest.mark.parametrize("cnpj", [
    "12ABC34501DE36",   # DV errado (alfanumérico)
    "12ABC34501DE30",
    "00000000000192",   # DV errado (numérico)
    NUMERICO[:-1] + "0",
    "11111111111111",   # todos iguais
    "00000000000000",
    "AAAAAAAAAAAAAA",
    "12ABC34501DEA5",   # letra no lugar do DV: o DV é sempre numérico
    "12ABC34501DE",     # curto
    "12ABC34501DE355",  # longo
    "12ABC34501D-35",   # caractere fora de A-Z/0-9
    "12ABC345 1DE35",
    "",
])
def test_cnpj_valido_recusa_dv_errado_formato_e_lixo(cnpj):
    assert not cnpj_valido(cnpj)


@pytest.mark.parametrize("ruim", [None, 12345678000195, 3.5, [], {}])
def test_cnpj_valido_tolera_tipos_inesperados(ruim):
    assert cnpj_valido(ruim) is False


@pytest.mark.parametrize("mascarado", ["12.ABC.345/01DE-35", " 12.ABC.345/01DE-35 ",
                                       "00.000.000/0001-91", "12.345.678/000A-08"])
def test_cnpj_valido_aceita_mascara_oficial(mascarado):
    assert cnpj_valido(mascarado)


def test_cnpj_valido_aceita_letras_minusculas_como_maiusculas():
    assert cnpj_valido("12abc34501de35")
    assert normalizar_cnpj("12abc34501de35") == ALFA


def test_letra_a_mais_ou_a_menos_nao_passa_a_validar_so_porque_o_dv_bate_por_acaso():
    # trocar um caractere muda o resultado do módulo 11: não vale só "ter 14 posições"
    assert not cnpj_valido("12ABC34501DF35")


# ---------- normalização de forma (sem checar o DV) ----------

@pytest.mark.parametrize("texto, esperado", [
    ("12.ABC.345/01DE-35", ALFA),
    (ALFA, ALFA),
    ("00.000.000/0001-91", BB),
    ("00.000.000/0001-92", "00000000000192"),  # forma ok; o DV é assunto de cnpj_valido
    ("12345678901", None),                     # 11 posições: CPF, não CNPJ
    ("123.456.789-01", None),
    ("12ABC34501DE", None),
    ("12ABC34501DE35X", None),
    ("***456789**", None),
    ("hmac:0123456789abcdef0123456789abcdef", None),
    ("", None), (None, None),
])
def test_normalizar_cnpj_devolve_14_posicoes_limpas_ou_none(texto, esperado):
    assert normalizar_cnpj(texto) == esperado


def test_normalizar_cnpj_exige_dv_numerico():
    assert normalizar_cnpj("12ABC34501DEAB") is None


# ---------- ingest.resolve.comum.cnpj_valido usa a mesma regra ----------

def test_ingest_cnpj_valido_aceita_alfanumerico_e_continua_recusando_o_que_recusava():
    assert cnpj_valido_ingest(ALFA) and cnpj_valido_ingest(BB)
    assert not cnpj_valido_ingest("12ABC34501DE36")
    assert not cnpj_valido_ingest("00000000000192")
    assert not cnpj_valido_ingest("11111111111111")
    assert not cnpj_valido_ingest("123")


# ---------- CEAP: documento do fornecedor ----------

def _doc(texto):
    return _documento_fornecedor(texto)


def test_ceap_cnpj_numerico_continua_cnpj():
    assert _doc("63.356.042/0001-80") == {"cnpj": "63356042000180"}
    assert _doc("63356042000180") == {"cnpj": "63356042000180"}


@pytest.mark.parametrize("texto", ["12.ABC.345/01DE-35", "12ABC34501DE35", "12abc34501de35"])
def test_ceap_cnpj_alfanumerico_nao_fica_sem_documento(texto):
    assert _doc(texto) == {"cnpj": ALFA}


def test_ceap_cnpj_alfanumerico_com_tres_letras_nao_vira_cpf_por_engano():
    # sem as letras restam 11 dígitos; o código antigo leria isto como CPF
    assert _doc("12.345.6AB/000C-81") == {"cnpj": ALFA_TRES_LETRAS}
    assert "cpf" not in _doc("12.345.6AB/000C-81")


def test_ceap_cpf_de_11_digitos_continua_cpf():
    assert _doc("111.444.777-35") == {"cpf": "11144477735"}
    assert _doc("11144477735") == {"cpf": "11144477735"}
    assert _doc("111.444.777/35  -  ") == {"cpf": "11144477735"}  # sujeira real do arquivo


@pytest.mark.parametrize("texto", [
    "000.000.000/0000-1",  # placeholder real da Câmara (telefonia funcional)
    "00000000000000", "00000000000", "11111111111", "11111111111111",
    "", None, "   ", "abc", "123", "12ABC34501DE",
    "1A1.444.777-35",      # 11 posições com letra: nem CPF nem CNPJ
    "***456789**", "12ABC34501DE35X",
])
def test_ceap_placeholder_lixo_e_tamanho_errado_ficam_sem_documento(texto):
    assert _doc(texto) == {}


def test_ceap_normalize_grava_cnpj_alfanumerico_na_despesa():
    linha = {"idDeputado": 1, "idDocumento": 99, "cnpjCPF": "12.ABC.345/01DE-35",
             "fornecedor": "EMPRESA NOVA LTDA", "valorLiquido": "10.5", "descricao": "X",
             "dataEmissao": "2026-08-01T00:00:00", "ano": 2026, "mes": 8}
    [f] = CeapSource(client=object()).normalize({"dados": [linha]})
    assert f.atributos["cnpj"] == ALFA and "cpf" not in f.atributos


# ---------- RFB (BrasilAPI) ----------

def _resposta(cnpj: str, **extra) -> dict:
    return {"cnpj": cnpj, "razao_social": "EMPRESA NOVA LTDA",
            "descricao_situacao_cadastral": "ATIVA", "cnae_fiscal": 4711302,
            "codigo_municipio_ibge": 3106200, "uf": "MG", "qsa": [], **extra}


def test_rfb_normalize_empresa_alfanumerica_vira_empresa_com_chave_de_14_posicoes():
    [e] = RfbSource(client=object()).normalize({"cnpjs": [_resposta(ALFA)]})
    assert e.tipo == "empresa" and e.chave == ALFA and e.id_oficial == ALFA
    assert e.url.endswith(f"/{ALFA}")


def test_rfb_normalize_aceita_a_resposta_com_mascara():
    [e] = RfbSource(client=object()).normalize({"cnpjs": [_resposta("12.ABC.345/01DE-35")]})
    assert e.chave == ALFA


def test_rfb_normalize_socio_pessoa_juridica_alfanumerica_traz_o_cnpj_inteiro():
    qsa = [{"nome_socio": "HOLDING NOVA SA", "cnpj_cpf_do_socio": "12ABC34501DE35",
            "identificador_de_socio": 1, "qualificacao_socio": "Sócio"},
           {"nome_socio": "FULANO", "cnpj_cpf_do_socio": "***101202**",
            "identificador_de_socio": 2, "qualificacao_socio": "Diretor"}]
    fatos = RfbSource(client=object()).normalize({"cnpjs": [_resposta(PETRO, qsa=qsa)]})
    socios = {f.atributos["nome"]: f.atributos for f in fatos if f.tipo == "socio"}
    assert socios["HOLDING NOVA SA"]["cpf_cnpj"] == ALFA
    assert socios["FULANO"]["cpf_cnpj"] == "***101202**"  # CPF mascarado: intacto


@pytest.mark.parametrize("lixo", ["12ABC34501DE", "12ABC34501DE35X", "ABCDEFGHIJKLMN"])
def test_rfb_normalize_documento_de_socio_malformado_continua_none(lixo):
    qsa = [{"nome_socio": "FULANO", "cnpj_cpf_do_socio": lixo, "identificador_de_socio": 1}]
    fatos = RfbSource(client=object()).normalize({"cnpjs": [_resposta(PETRO, qsa=qsa)]})
    assert next(f for f in fatos if f.tipo == "socio").atributos["cpf_cnpj"] is None


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def _servidor(respostas: dict[str, dict]):
    chamadas: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas.append(str(request.url))
        corpo = respostas.get(str(request.url).rsplit("/", 1)[1])
        return httpx.Response(200, json=corpo) if corpo else httpx.Response(404, json={})

    return chamadas, httpx.Client(transport=httpx.MockTransport(handler))


def test_rfb_fetch_consulta_cnpj_alfanumerico_limpo_e_em_maiusculas(raw_dir):
    chamadas, client = _servidor({ALFA: _resposta(ALFA)})
    rfb = RfbSource(client=client, dormir=lambda _s: None)
    out = rfb.fetch(["12.abc.345/01de-35", ALFA])  # mascarado/minúsculo e repetido
    assert chamadas == [f"https://brasilapi.com.br/api/cnpj/v1/{ALFA}"]
    assert out["invalidos"] == [] and [e["cnpj"] for e in out["cnpjs"]] == [ALFA]
    assert (raw_dir / "rfb" / f"{ALFA}.json").exists()


def test_rfb_fetch_registra_como_invalido_o_alfanumerico_com_dv_errado(raw_dir):
    chamadas, client = _servidor({})
    rfb = RfbSource(client=client, dormir=lambda _s: None)
    out = rfb.fetch(["12ABC34501DE36"])
    assert chamadas == [] and out["invalidos"] == ["12ABC34501DE36"]


def test_rfb_fetch_reusar_raw_le_do_disco_o_alfanumerico_ja_consultado(raw_dir):
    (raw_dir / "rfb").mkdir()
    (raw_dir / "rfb" / f"{ALFA}.json").write_text(json.dumps(_resposta(ALFA)), encoding="utf-8")
    chamadas, client = _servidor({})
    rfb = RfbSource(client=client, dormir=lambda _s: None)
    out = rfb.fetch([ALFA], reusar_raw=True)
    assert chamadas == [] and [e["cnpj"] for e in out["cnpjs"]] == [ALFA]


# ---------- TSE: doador PJ com CNPJ alfanumérico ----------

def _receita(doc: str, origem="Recursos de pessoas juridicas") -> dict:
    return {"AA_ELEICAO": "2026", "SQ_CANDIDATO": "10", "DS_CARGO": "Deputado Federal",
            "SQ_RECEITA": "r1", "NM_DOADOR": "EMPRESA NOVA", "NM_DOADOR_RFB": "EMPRESA NOVA LTDA",
            "NR_CPF_CNPJ_DOADOR": doc, "DS_ORIGEM_RECEITA": origem, "DT_RECEITA": "01/09/2026",
            "VR_RECEITA": "100,00"}


@pytest.mark.parametrize("doc", [ALFA, "12.ABC.345/01DE-35"])
def test_tse_doador_com_cnpj_alfanumerico_e_pj_e_guarda_o_documento(doc):
    [f] = TseSource(client=object()).normalize({"ano": 2026, "receitas": [_receita(doc)]})
    assert f.atributos["doador_cpf_cnpj"] == ALFA and f.atributos["tipo_doador"] == "PJ"


def test_tse_doador_cpf_e_cnpj_numerico_continuam_iguais():
    fonte = TseSource(client=object())
    [pf] = fonte.normalize({"ano": 2022, "receitas": [_receita("11144477735")]})
    [pj] = fonte.normalize({"ano": 2022, "receitas": [_receita("35492333000160")]})
    assert (pf.atributos["doador_cpf_cnpj"], pf.atributos["tipo_doador"]) == ("11144477735", "PF")
    assert (pj.atributos["doador_cpf_cnpj"], pj.atributos["tipo_doador"]) == (
        "35492333000160", "PJ")


# ---------- pipeline: ranking dos CNPJs que vão para a Receita ----------

def _fato(tipo, chave, fonte="teste", **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte=fonte, id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def test_cnpjs_para_rfb_inclui_fornecedor_e_doador_alfanumericos_por_valor():
    store = Store(":memory:")
    store.upsert_facts([
        _fato("despesa_ceap", "d1", deputado_id="1", cnpj=ALFA, valor=500.0),
        _fato("despesa_ceap", "d2", deputado_id="1", cnpj=BB, valor=100.0),
        _fato("despesa_ceap", "d3", deputado_id="1", cnpj="12ABC34501DE36", valor=9999.0),  # DV
        _fato("doacao", "r1", doador_cpf_cnpj=ALFA_ZZ, valor=900.0, tipo_doador="PJ"),
        _fato("doacao", "r2", doador_cpf_cnpj="hmac:" + "a" * 32, valor=5000.0),  # CPF pseudonimizado
        _fato("doacao", "r3", doador_cpf_cnpj="11144477735", valor=7000.0),  # CPF
    ])
    pipe = Pipeline(store, Opcoes(fontes=("rfb",)), log=lambda _: None)
    assert pipe._cnpjs_para_rfb(10) == [ALFA_ZZ, ALFA, BB]


# ---------- resolução: link por CNPJ alfanumérico ----------

def test_resolver_cnpj_liga_despesa_alfanumerica_a_empresa_e_a_sancao():
    d = _fato("despesa_ceap", "d1", deputado_id="1", cnpj=ALFA, valor=1.0)
    e = _fato("empresa", ALFA, razao_social="EMPRESA NOVA")
    s = _fato("sancao", "CEIS:1", cnpj=ALFA, cadastro="CEIS")
    res = resolver_cnpj([d], [e], [s])
    assert {(lk.origem, lk.destino) for lk in res.links} == {
        ("despesa_ceap:d1", f"empresa:{ALFA}"), ("despesa_ceap:d1", "sancao:CEIS:1")}
