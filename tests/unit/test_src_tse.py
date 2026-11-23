"""TseSource — candidaturas, receitas de campanha e votação por município (Dados Abertos do TSE).

Fixtures REAIS recortadas dos arquivos oficiais de 2022 (cabeçalho e linhas originais, latin-1,
';', tudo entre aspas): `tse_consulta_cand_amostra.csv`, `tse_receitas_amostra.csv`,
`tse_votacao_munzona_amostra.csv`, `tse_ibge_municipios_amostra.json` (API de localidades do
IBGE). Única alteração (LGPD): CPFs de candidatos e CPF/nome de doadores pessoa física foram
trocados por valores sintéticos (99999000NNN / "DOADOR PF NNN"); CNPJs são os reais.
Casos de borda sem linha real equivalente são derivados de uma linha real mudando só o campo
testado.
"""
from __future__ import annotations

import csv
import io
import json
import random
import re
import zipfile
from collections import defaultdict
from pathlib import Path

import httpx
import pytest

import sources.base
from sources.tse.source import FONTE_CANDIDATURA, FONTE_DOACAO, FONTE_VOTOS, TseSource

FIX = Path(__file__).parent / "fixtures"
CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"
URL_CAND = f"{CDN}/consulta_cand/consulta_cand_2022.zip"
URL_PREST = f"{CDN}/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip"
URL_VOTOS = f"{CDN}/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip"
URL_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def _linhas(nome: str) -> list[dict]:
    with (FIX / nome).open(encoding="latin-1", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _ibge_api() -> list[dict]:
    return json.loads((FIX / "tse_ibge_municipios_amostra.json").read_text(encoding="utf-8"))


def _ibge_compacto() -> list[dict]:
    return [{"id": m["id"], "nome": m["nome"],
             "uf": m["microrregiao"]["mesorregiao"]["UF"]["sigla"]} for m in _ibge_api()]


@pytest.fixture
def raw() -> dict:
    return {"ano": 2022, "candidatos": _linhas("tse_consulta_cand_amostra.csv"),
            "receitas": _linhas("tse_receitas_amostra.csv"),
            "votacao": _linhas("tse_votacao_munzona_amostra.csv"),
            "municipios_ibge": _ibge_compacto()}


@pytest.fixture
def fonte() -> TseSource:
    return TseSource(client=object())  # normalize é puro: não usa o client


def _por_chave(facts, tipo: str | None = None):
    return {f.chave: f for f in facts if tipo is None or f.tipo == tipo}


def _votos(fonte: TseSource, raw: dict) -> list:
    return [f for f in fonte.normalize(raw) if f.tipo == "votos_municipio"]


def _linha(raw: dict, lista: str, coluna: str, valor: str) -> dict:
    return next(dict(r) for r in raw[lista] if r[coluna] == valor)


# ---------- normalize: candidatura ----------

def test_candidatura_de_deputado_federal_tem_atributos_exatos(fonte, raw):
    f = _por_chave(fonte.normalize(raw), "candidatura")["10001619990"]
    assert f.tipo == "candidatura" and f.fonte == FONTE_CANDIDATURA
    assert f.id_oficial == "10001619990" and f.url == URL_CAND
    assert f.atributos == {
        "ano": 2022, "cpf": "99999000001", "nome": "ALZIRA LINDALICE CRUZ RAMOS CAMARA",
        "nome_urna": "ALZIRA LINDA", "cargo": "Deputado Federal", "uf": "AC",
        "partido": "REPUBLICANOS", "situacao": "ELEITO POR QP",
    }


def test_so_deputado_federal_vira_candidatura(fonte, raw):
    cands = _por_chave(fonte.normalize(raw), "candidatura")
    assert set(cands) == {"10001619990", "10001716348", "10001655718", "70001611667"}
    assert "10001649312" not in cands  # deputado estadual


def test_cpf_invalido_do_tse_vira_none_e_a_candidatura_continua(fonte, raw):
    a = _por_chave(fonte.normalize(raw), "candidatura")["70001611667"].atributos
    assert a["cpf"] is None and a["uf"] == "DF" and a["partido"] == "NOVO"


def test_candidatura_sem_sq_candidato_e_descartada(fonte, raw):
    linha = _linha(raw, "candidatos", "SQ_CANDIDATO", "10001619990")
    linha["SQ_CANDIDATO"] = ""
    assert fonte.normalize({"ano": 2022, "candidatos": [linha]}) == []


# ---------- normalize: doação ----------

def test_doacao_de_pessoa_fisica_tem_atributos_exatos(fonte, raw):
    f = _por_chave(fonte.normalize(raw), "doacao")["32303315"]
    assert f.fonte == FONTE_DOACAO and f.id_oficial == "32303315" and f.url == URL_PREST
    assert f.atributos == {
        "ano": 2022, "sq_candidato": "10001619994", "doador_nome": "DOADOR PF 006",
        "doador_cpf_cnpj": "99999000006", "valor": 3000.0, "data": "2022-09-13",
        "tipo_doador": "PF", "origem": "Recursos de pessoas físicas",
    }
    assert isinstance(f.atributos["valor"], float)


def test_doacao_de_partido_usa_nome_da_receita_federal_e_tipo_partido(fonte, raw):
    a = _por_chave(fonte.normalize(raw), "doacao")["32303312"].atributos
    assert a["tipo_doador"] == "partido" and a["doador_cpf_cnpj"] == "07665132000181"
    assert a["doador_nome"] == "REPUBLICANOS - BRASIL - BR - NACIONAL"
    assert a["valor"] == 150000.0


def test_autofinanciamento_e_proprio_mesmo_com_cpf_de_pessoa_fisica(fonte, raw):
    a = _por_chave(fonte.normalize(raw), "doacao")["32303313"].atributos
    assert a["tipo_doador"] == "proprio" and len(a["doador_cpf_cnpj"]) == 11


def test_doador_pessoa_juridica_e_pj_e_pessoa_fisica_e_pf(fonte, raw):
    doacoes = _por_chave(fonte.normalize(raw), "doacao")
    assert doacoes["29317428"].atributos["tipo_doador"] == "PJ"  # CNPJ 35492333000160
    assert doacoes["29317428"].atributos["doador_cpf_cnpj"] == "35492333000160"
    assert doacoes["32303316"].atributos["tipo_doador"] == "PF"


def test_doacao_de_outro_candidato_com_cnpj_de_campanha_fica_pj_com_origem_preservada(fonte, raw):
    a = _por_chave(fonte.normalize(raw), "doacao")["29358280"].atributos
    assert a["tipo_doador"] == "PJ" and a["origem"] == "Recursos de outros candidatos"


def test_receita_sem_doador_identificado_fica_sem_documento_nem_tipo(fonte, raw):
    a = _por_chave(fonte.normalize(raw), "doacao")["32906131"].atributos
    assert a["doador_cpf_cnpj"] is None and a["tipo_doador"] is None
    assert a["doador_nome"] is None and a["valor"] == 38.54


def test_linha_placeholder_sem_receita_e_descartada(fonte, raw):
    assert raw["receitas"][7]["SQ_RECEITA"] == "-1"
    assert "-1" not in _por_chave(fonte.normalize(raw), "doacao")


def test_receita_de_deputado_estadual_e_descartada(fonte, raw):
    assert "31493344" not in _por_chave(fonte.normalize(raw), "doacao")


def test_sq_receita_repetido_gera_chaves_distintas_sem_perder_valor(fonte, raw):
    doacoes = [f for f in fonte.normalize(raw) if f.tipo == "doacao" and f.id_oficial == "32916114"]
    assert [(f.chave, f.atributos["valor"]) for f in doacoes] == [
        ("32916114", 900.0), ("32916114:2", 1500.0)]


def test_total_de_doacoes_da_amostra(fonte, raw):
    # 12 linhas − 1 placeholder (-1) − 1 deputado estadual
    assert len([f for f in fonte.normalize(raw) if f.tipo == "doacao"]) == 10


@pytest.mark.parametrize("campo,valor", [("VR_RECEITA", "abc"), ("VR_RECEITA", "")])
def test_receita_com_valor_invalido_e_descartada(fonte, raw, campo, valor):
    linha = _linha(raw, "receitas", "SQ_RECEITA", "32303315")
    linha[campo] = valor
    assert fonte.normalize({"ano": 2022, "receitas": [linha]}) == []


def test_receita_sem_data_fica_com_data_none(fonte, raw):
    linha = _linha(raw, "receitas", "SQ_RECEITA", "32303315")
    linha["DT_RECEITA"] = ""
    [f] = fonte.normalize({"ano": 2022, "receitas": [linha]})
    assert f.atributos["data"] is None


# ---------- normalize: votos por município ----------

def test_votos_somam_as_zonas_do_municipio_e_trazem_o_total_valido_do_cargo(fonte, raw):
    f = _por_chave(fonte.normalize(raw), "votos_municipio")["2022:10001619990:1200401"]
    assert f.fonte == FONTE_VOTOS and f.url == URL_VOTOS
    assert f.id_oficial == "10001619990:1392"
    assert f.atributos == {
        "ano": 2022, "sq_candidato": "10001619990", "municipio_ibge": "1200401", "uf": "AC",
        "votos": 6250, "votos_validos_municipio": 19852,
        "municipio_tse": "1392", "municipio_nome": "RIO BRANCO",
    }


def test_votos_denominador_ignora_outros_cargos(fonte, raw):
    votos = _por_chave(fonte.normalize(raw), "votos_municipio")
    manoel = votos["2022:10001619990:1200344"].atributos
    assert manoel["votos"] == 466
    assert manoel["votos_validos_municipio"] == 735  # sem a linha de deputado estadual


def test_votos_um_fato_por_candidato_e_municipio(fonte, raw):
    votos = _por_chave(fonte.normalize(raw), "votos_municipio")
    assert len(votos) == 10  # 5 candidatos × 2 municípios


def test_votos_ja_agregados_dao_o_mesmo_resultado_que_as_linhas_por_zona(fonte, raw):
    soma: dict[tuple, int] = defaultdict(int)
    primeira: dict[tuple, dict] = {}
    for r in raw["votacao"]:
        if r["DS_CARGO"] == "Deputado Federal":
            k = (r["SQ_CANDIDATO"], r["CD_MUNICIPIO"])
            primeira.setdefault(k, r)
            soma[k] += int(r["QT_VOTOS_NOMINAIS_VALIDOS"])
    agregadas = [dict(r, QT_VOTOS_NOMINAIS_VALIDOS=str(soma[k])) for k, r in primeira.items()]
    assert len(agregadas) < len(raw["votacao"])

    def votos(linhas):
        return {(f.chave, f.atributos["votos"], f.atributos["votos_validos_municipio"])
                for f in fonte.normalize({**raw, "votacao": linhas}) if f.tipo == "votos_municipio"}

    assert votos(agregadas) == votos(raw["votacao"])


def test_municipio_renomeado_resolve_por_alias_oficial(fonte, raw):
    linha = _linha(raw, "votacao", "CD_MUNICIPIO", "1554")
    linha.update(SG_UF="MG", CD_MUNICIPIO="44571", NM_MUNICIPIO="DONA EUSÉBIA")
    [f] = [f for f in fonte.normalize({**raw, "votacao": [linha]}) if f.tipo == "votos_municipio"]
    assert f.atributos["municipio_ibge"] == "3122900"  # IBGE grafa "Dona Euzébia"
    assert f.chave == f"2022:{linha['SQ_CANDIDATO']}:3122900"


def test_municipio_sem_correspondencia_no_ibge_fica_sem_codigo_e_chave_tse(fonte, raw):
    linha = _linha(raw, "votacao", "CD_MUNICIPIO", "1554")
    linha.update(NM_MUNICIPIO="MUNICIPIO INEXISTENTE")
    [f] = [f for f in fonte.normalize({**raw, "votacao": [linha]}) if f.tipo == "votos_municipio"]
    assert f.atributos["municipio_ibge"] is None
    assert f.chave == f"2022:{linha['SQ_CANDIDATO']}:tse1554"


def test_votos_no_exterior_sao_ignorados(fonte, raw):
    linha = _linha(raw, "votacao", "CD_MUNICIPIO", "1554")
    linha.update(SG_UF="ZZ", NM_MUNICIPIO="BANGKOK")
    assert _votos(fonte, {**raw, "votacao": [linha]}) == []


def test_votos_com_quantidade_invalida_sao_descartados(fonte, raw):
    linha = _linha(raw, "votacao", "CD_MUNICIPIO", "1554")
    linha["QT_VOTOS_NOMINAIS_VALIDOS"] = "x"
    assert _votos(fonte, {**raw, "votacao": [linha]}) == []


def test_todo_fato_tem_fonte_id_oficial_e_url(fonte, raw):
    facts = fonte.normalize(raw)
    assert {f.tipo for f in facts} == {"candidatura", "doacao", "votos_municipio"}
    assert all(f.fonte and f.id_oficial and f.url for f in facts)


def test_normalize_de_raw_vazio_devolve_lista_vazia(fonte):
    assert fonte.normalize({}) == []


# ---------- fetch (zips grandes lidos por HTTP Range, sem baixar o arquivo inteiro) ----------

def _zip(membros: dict[str, bytes], lixo: int = 0) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, corpo in membros.items():
            z.writestr(nome, corpo)
        if lixo:  # membro grande e incompressível (as despesas ocupam ~90% do zip real)
            z.writestr("despesas_pagas_candidatos_2022_AC.csv", random.Random(0).randbytes(lixo))
    return buf.getvalue()


def _so_cabecalho(nome: str) -> bytes:
    return (FIX / nome).read_bytes().split(b"\r\n")[0] + b"\r\n"


def _servidor(zips: dict[str, bytes], visto: list | None = None, ranges: bool = True,
              ibge: list[dict] | None = None, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        url, rng = str(request.url), request.headers.get("range")
        if visto is not None:
            visto.append((request.method, url, rng))
        if status != 200:
            return httpx.Response(status)
        if url == URL_IBGE:
            return httpx.Response(200, json=ibge if ibge is not None else _ibge_api())
        corpo = zips.get(url)
        if corpo is None:
            return httpx.Response(404)
        if request.method == "HEAD":
            return httpx.Response(200, headers={"content-length": str(len(corpo)),
                                                "accept-ranges": "bytes"})
        if not rng or not ranges:
            return httpx.Response(200, content=corpo)
        ini, fim = (int(x) for x in re.fullmatch(r"bytes=(\d+)-(\d+)", rng).groups())
        fim = min(fim, len(corpo) - 1)
        return httpx.Response(206, content=corpo[ini:fim + 1],
                              headers={"content-range": f"bytes {ini}-{fim}/{len(corpo)}"})
    return httpx.Client(transport=httpx.MockTransport(handler))


def _zips(lixo: int = 0) -> dict[str, bytes]:
    return {
        URL_CAND: _zip({
            "consulta_cand_2022_AC.csv": (FIX / "tse_consulta_cand_amostra.csv").read_bytes(),
            "consulta_cand_2022_MG.csv": _so_cabecalho("tse_consulta_cand_amostra.csv"),
            "consulta_cand_2022_BR.csv": (FIX / "tse_consulta_cand_amostra.csv").read_bytes(),
            "consulta_cand_2022_BRASIL.csv": b"nao deve ser lido",
        }, lixo),
        URL_PREST: _zip({
            "receitas_candidatos_2022_AC.csv": (FIX / "tse_receitas_amostra.csv").read_bytes(),
            "receitas_candidatos_2022_MG.csv": _so_cabecalho("tse_receitas_amostra.csv"),
            "receitas_candidatos_2022_BRASIL.csv": b"nao deve ser lido",
        }, lixo),
        URL_VOTOS: _zip({
            "votacao_candidato_munzona_2022_AC.csv":
                (FIX / "tse_votacao_munzona_amostra.csv").read_bytes(),
            "votacao_candidato_munzona_2022_MG.csv":
                _so_cabecalho("tse_votacao_munzona_amostra.csv"),
            "votacao_candidato_munzona_2022_BRASIL.csv": b"nao deve ser lido",
        }, lixo),
    }


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def test_fetch_filtra_deputado_federal_agrega_votos_e_traz_municipios(raw_dir):
    out = TseSource(client=_servidor(_zips())).fetch(uf="AC")
    assert out["ano"] == 2022 and out["uf"] == "AC"
    assert {r["SQ_CANDIDATO"] for r in out["candidatos"]} == {
        "10001619990", "10001716348", "10001655718", "70001611667"}
    assert len(out["receitas"]) == 11  # 12 linhas − 1 deputado estadual
    assert {r["DS_CARGO"] for r in out["receitas"]} == {"Deputado Federal"}
    assert len(out["votacao"]) == 10  # zonas agregadas por (candidato, município)
    soma = next(r for r in out["votacao"]
                if r["SQ_CANDIDATO"] == "10001619990" and r["CD_MUNICIPIO"] == "1392")
    assert soma["QT_VOTOS_NOMINAIS_VALIDOS"] == "6250"
    assert out["municipios_ibge"] == _ibge_compacto()


def test_fetch_e_normalize_ponta_a_ponta(raw_dir, raw, fonte):
    facts = fonte.normalize(TseSource(client=_servidor(_zips())).fetch(uf="AC"))
    por_tipo = {t: {f.chave for f in facts if f.tipo == t}
                for t in ("candidatura", "doacao", "votos_municipio")}
    esperado = fonte.normalize(raw)
    assert por_tipo["votos_municipio"] == {f.chave for f in esperado if f.tipo == "votos_municipio"}
    assert por_tipo["doacao"] == {f.chave for f in esperado if f.tipo == "doacao"}
    assert por_tipo["candidatura"] == {f.chave for f in esperado if f.tipo == "candidatura"}


def test_fetch_le_so_o_membro_da_uf_por_range_sem_baixar_o_zip_inteiro(raw_dir):
    zips = _zips(lixo=4_000_000)
    visto: list = []
    TseSource(client=_servidor(zips, visto)).fetch(uf="AC", conjuntos=("receitas",))
    gets = [(u, r) for m, u, r in visto if m == "GET" and u == URL_PREST]
    assert gets and all(r for _, r in gets)  # nenhum GET sem cabeçalho Range
    baixado = sum(int(b) - int(a) + 1 for a, b in
                  (re.fullmatch(r"bytes=(\d+)-(\d+)", r).groups() for _, r in gets))
    assert baixado < len(zips[URL_PREST]) * 0.5
    assert not any(u in (URL_CAND, URL_VOTOS) for _, u, _ in visto)  # conjuntos não pedidos


def test_fetch_sem_uf_percorre_todas_as_ufs_e_ignora_br_e_brasil(raw_dir):
    out = TseSource(client=_servidor(_zips())).fetch(conjuntos=("candidatos",))
    assert "municipios_ibge" not in out and "receitas" not in out
    assert len(out["candidatos"]) == 4  # AC (MG só tem cabeçalho; BR e BRASIL ignorados)


def test_fetch_salva_o_bruto_filtrado_em_data_raw(raw_dir):
    TseSource(client=_servidor(_zips())).fetch(uf="AC")
    salvos = list((raw_dir / "tse").glob("*.json"))
    assert len(salvos) == 1
    assert json.loads(salvos[0].read_text(encoding="utf-8"))["uf"] == "AC"


@pytest.mark.parametrize("uf", ["MGG", "1", "", "../AC"])
def test_fetch_recusa_uf_invalida(raw_dir, uf):
    with pytest.raises(ValueError, match="uf"):
        TseSource(client=_servidor(_zips())).fetch(uf=uf)


def test_fetch_uf_sem_arquivo_no_zip_da_erro_claro(raw_dir):
    with pytest.raises(ValueError, match="consulta_cand_2022_RJ.csv"):
        TseSource(client=_servidor(_zips())).fetch(uf="RJ", conjuntos=("candidatos",))


def test_fetch_servidor_sem_range_da_erro_claro(raw_dir):
    with pytest.raises(RuntimeError, match="Range"):
        TseSource(client=_servidor(_zips(), ranges=False)).fetch(uf="AC",
                                                                conjuntos=("candidatos",))


def test_fetch_http_erro_propaga(raw_dir):
    with pytest.raises(httpx.HTTPStatusError):
        TseSource(client=_servidor(_zips(), status=503)).fetch(uf="AC", conjuntos=("candidatos",))


def test_fetch_cabecalho_sem_coluna_esperada_da_erro_claro(raw_dir):
    zips = _zips()
    zips[URL_CAND] = _zip({"consulta_cand_2022_AC.csv": '"X";"Y"\r\n"1";"2"\r\n'.encode("latin-1")})
    with pytest.raises(ValueError, match="SQ_CANDIDATO"):
        TseSource(client=_servidor(zips)).fetch(uf="AC", conjuntos=("candidatos",))


def test_fetch_conjunto_desconhecido_e_recusado(raw_dir):
    with pytest.raises(ValueError, match="conjunto"):
        TseSource(client=_servidor(_zips())).fetch(uf="AC", conjuntos=("despesas",))


# ---------- fetch por UF (memória limitada) ----------

def test_fetch_por_uf_grava_cada_uf_antes_de_ler_a_proxima(raw_dir):
    gen = TseSource(client=_servidor(_zips())).fetch_por_uf(conjuntos=("candidatos",))
    primeira = next(gen)
    assert primeira["uf"] == "AC" and len(primeira["candidatos"]) == 4
    assert (raw_dir / "tse" / "tse_2022_AC.json").is_file()
    assert not (raw_dir / "tse" / "tse_2022_MG.json").exists()  # ainda não lida
    segunda = next(gen)
    assert segunda["uf"] == "MG" and segunda["candidatos"] == []
    with pytest.raises(StopIteration):
        next(gen)


def test_fetch_por_uf_cada_parte_e_normalizavel_sozinha(raw_dir, raw, fonte):
    [parte] = list(TseSource(client=_servidor(_zips())).fetch_por_uf(uf="AC"))
    assert {f.chave for f in fonte.normalize(parte)} == {f.chave for f in fonte.normalize(raw)}


def test_fetch_sem_uf_grava_um_arquivo_por_uf_e_nenhum_consolidado(raw_dir):
    out = TseSource(client=_servidor(_zips())).fetch()
    nomes = sorted(p.name for p in (raw_dir / "tse").glob("*.json"))
    assert nomes == ["tse_2022_AC.json", "tse_2022_MG.json"]
    assert out["uf"] is None and len(out["candidatos"]) == 4 and len(out["votacao"]) == 10


def test_fetch_sem_uf_consulta_o_ibge_uma_vez_so(raw_dir):
    visto: list = []
    TseSource(client=_servidor(_zips(), visto)).fetch(conjuntos=("votacao",))
    assert [u for _, u, _ in visto].count(URL_IBGE) == 1
