"""CguSource — CEIS, CNEP e emendas parlamentares (downloads abertos do Portal da Transparência).

Fixtures REAIS recortadas dos zips oficiais (cabeçalho e linhas originais, latin-1, ';'):
`cgu_ceis_amostra.csv`, `cgu_cnep_amostra.csv`, `cgu_emendas_amostra.csv`.
Única alteração (LGPD): nas linhas de pessoa física, nome e CPF foram trocados por valores
sintéticos. A linha "malformada" é uma linha real truncada no 4º campo. Casos de borda sem linha
real equivalente são derivados de uma linha real mudando só o campo testado.
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import httpx
import pytest

import sources.base
from sources import manifest
from sources.cgu.source import FONTE_CEIS, FONTE_CNEP, FONTE_EMENDAS, CguSource

FIX = Path(__file__).parent / "fixtures"
PAGINA = "https://portaldatransparencia.gov.br/download-de-dados"


def _linhas(nome: str) -> list[dict]:
    """Lê a fixture como o contrato do raw: lista de dicts com os nomes originais de coluna."""
    with (FIX / nome).open(encoding="latin-1", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


@pytest.fixture
def raw() -> dict:
    return {"ceis": _linhas("cgu_ceis_amostra.csv"), "cnep": _linhas("cgu_cnep_amostra.csv"),
            "emendas": _linhas("cgu_emendas_amostra.csv")}


@pytest.fixture
def fonte() -> CguSource:
    return CguSource(client=object())  # normalize é puro: não usa o client


def _por_chave(facts):
    return {f.chave: f for f in facts}


def _linha(raw: dict, lista: str, coluna: str, valor: str) -> dict:
    return next(dict(r) for r in raw[lista] if r.get(coluna) == valor)


# ---------- normalize: sanções (CEIS/CNEP) ----------

def test_sancao_sem_data_fim_tem_fim_none_e_atributos_exatos(fonte, raw):
    f = _por_chave(fonte.normalize(raw))["CEIS:90944"]
    assert f.tipo == "sancao" and f.fonte == FONTE_CEIS and f.id_oficial == "90944"
    assert f.url == f"{PAGINA}/ceis"
    assert f.atributos == {
        "cnpj": "09550793000197", "cpf": None, "cadastro": "CEIS", "inicio": "2018-02-02",
        "fim": None, "orgao": "Governo do Estado da Bahia (BA)",
        "nome": "TRIPLICE REPRESENTANTES DE ALIMENTOS LTDA", "tipo_pessoa": "J",
        "categoria": "Declaração de Inidoneidade com prazo determinado", "valor_multa": None,
    }


def test_sancao_com_data_fim_converte_datas_para_iso(fonte, raw):
    a = _por_chave(fonte.normalize(raw))["CEIS:343509"].atributos
    assert (a["inicio"], a["fim"]) == ("2025-03-20", "2025-06-20")
    assert a["cnpj"] == "15121210000105"


def test_sancao_de_pessoa_fisica_guarda_cpf_e_nao_cnpj(fonte, raw):
    a = _por_chave(fonte.normalize(raw))["CEIS:407707"].atributos
    assert a["cpf"] == "11144477735" and a["cnpj"] is None and a["tipo_pessoa"] == "F"


def test_sancionado_estrangeiro_sem_cpf_cnpj_vira_fato_sem_documento(fonte, raw):
    f = _por_chave(fonte.normalize(raw))["CEIS:308881"]
    assert f.atributos["cnpj"] is None and f.atributos["cpf"] is None
    assert f.atributos["tipo_pessoa"] is None and f.atributos["fim"] is None


def test_linha_malformada_truncada_e_descartada_sem_duplicar_chave(fonte, raw):
    assert len(raw["ceis"]) == 5  # 4 reais + 1 truncada
    ceis = [f for f in fonte.normalize(raw) if f.fonte == FONTE_CEIS]
    assert len(ceis) == 4
    assert len({f.chave for f in ceis}) == 4


@pytest.mark.parametrize("texto", ["Sem Informação", "31/02/2025", "2025-03-20", "  "])
def test_data_invalida_vira_none_sem_derrubar_a_linha(fonte, raw, texto):
    linha = _linha(raw, "ceis", "CÓDIGO DA SANÇÃO", "343509")
    linha["DATA FINAL SANÇÃO"] = texto
    [f] = fonte.normalize({"ceis": [linha]})
    assert f.atributos["fim"] is None and f.atributos["inicio"] == "2025-03-20"


def test_cnep_traz_valor_da_multa_como_float_e_cadastro_cnep(fonte, raw):
    facts = _por_chave(fonte.normalize(raw))
    f = facts["CNEP:327542"]
    assert f.fonte == FONTE_CNEP and f.url == f"{PAGINA}/cnep"
    assert f.atributos["cadastro"] == "CNEP"
    assert f.atributos["valor_multa"] == 0.0 and isinstance(f.atributos["valor_multa"], float)
    assert f.atributos["fim"] is None
    assert facts["CNEP:336271"].atributos["fim"] == "2029-05-08"
    assert facts["CNEP:108789"].atributos["cpf"] == "11144477735"


def test_cnep_multa_com_virgula_decimal(fonte, raw):
    linha = _linha(raw, "cnep", "CÓDIGO DA SANÇÃO", "327542")
    linha["VALOR DA MULTA"] = "377157,39"
    [f] = fonte.normalize({"cnep": [linha]})
    assert f.atributos["valor_multa"] == 377157.39


def test_todo_fato_tem_fonte_id_oficial_e_url(fonte, raw):
    facts = fonte.normalize(raw)
    assert facts
    assert all(f.fonte and f.id_oficial and f.url for f in facts)
    assert {f.tipo for f in facts} == {"sancao", "emenda"}


# ---------- normalize: emendas ----------

def test_emenda_pix_transferencia_especial_tem_atributos_exatos(fonte, raw):
    f = _por_chave(fonte.normalize(raw))["202338950009"]
    assert f.tipo == "emenda" and f.fonte == FONTE_EMENDAS and f.id_oficial == "202338950009"
    assert f.url == f"{PAGINA}/emendas-parlamentares"
    assert f.atributos == {
        "autor_nome": "AMANCIO SANTANA", "autor_codigo": "3895", "ano": 2023,
        "valor_empenhado": 4000000.0, "valor_pago": 4000000.0, "municipio_ibge": "2908903",
        "tipo": "pix", "tipo_emenda": "Emenda Individual - Transferências Especiais",
    }


def test_emenda_individual_finalidade_definida_tem_tipo_individual(fonte, raw):
    a = _por_chave(fonte.normalize(raw))["202442900008"].atributos
    assert a["tipo"] == "individual" and a["municipio_ibge"] == "5103403"
    assert a["valor_empenhado"] == 500000.0 and a["ano"] == 2024


def test_emenda_de_bancada_comissao_e_relator_mapeiam_tipo(fonte, raw):
    facts = _por_chave(fonte.normalize(raw))
    assert facts["201771060001"].atributos["tipo"] == "bancada"
    assert facts["201771060001"].atributos["autor_nome"] == "BANCADA DA BAHIA"
    assert facts["202050080002"].atributos["tipo"] == "comissao"
    assert facts["202081000179"].atributos["tipo"] == "relator"


def test_emenda_multiplos_municipios_fica_sem_ibge(fonte, raw):
    a = _por_chave(fonte.normalize(raw))["202081000179"].atributos
    assert a["municipio_ibge"] is None


def test_linhas_do_mesmo_codigo_e_municipio_somam_valores_em_um_fato(fonte, raw):
    emendas = [f for f in fonte.normalize(raw) if f.tipo == "emenda"]
    assert [f.chave for f in emendas].count("202030410010") == 1
    a = _por_chave(emendas)["202030410010"].atributos
    assert a["valor_empenhado"] == 740000.0 + 2950000.0
    assert a["valor_pago"] == 740000.0 + 2950000.0


def test_emenda_sem_codigo_oficial_e_descartada(fonte, raw):
    emendas = [f for f in fonte.normalize(raw) if f.tipo == "emenda"]
    assert len(raw["emendas"]) == 9
    # 9 linhas − 2 "Sem informação" (RELATOR GERAL 2016 e 2014) − 1 linha somada (202030410010)
    assert len(emendas) == 6
    assert all(f.chave[:2] == "20" for f in emendas)


def test_mesmo_codigo_em_municipios_diferentes_nao_colide(fonte, raw):
    base = _linha(raw, "emendas", "Código da Emenda", "202442900008")
    outra = dict(base, **{"Código Município IBGE": "5300108"})
    facts = fonte.normalize({"emendas": [base, outra]})
    assert sorted(f.chave for f in facts) == ["202442900008:5103403", "202442900008:5300108"]
    assert {f.id_oficial for f in facts} == {"202442900008"}


@pytest.mark.parametrize("campo", ["Valor Empenhado", "Valor Pago"])
def test_emenda_com_valor_invalido_e_descartada(fonte, raw, campo):
    linha = _linha(raw, "emendas", "Código da Emenda", "202442900008")
    linha[campo] = "n/d"
    assert fonte.normalize({"emendas": [linha]}) == []


def test_emenda_valor_com_milhar_e_virgula(fonte, raw):
    linha = _linha(raw, "emendas", "Código da Emenda", "202442900008")
    linha["Valor Empenhado"] = "1.234.567,89"
    [f] = fonte.normalize({"emendas": [linha]})
    assert f.atributos["valor_empenhado"] == 1234567.89


def test_emenda_autor_sem_informacao_vira_none(fonte, raw):
    linha = _linha(raw, "emendas", "Código da Emenda", "202442900008")
    linha["Nome do Autor da Emenda"] = "Sem informação"
    [f] = fonte.normalize({"emendas": [linha]})
    assert f.atributos["autor_nome"] is None


def test_emenda_linha_truncada_e_descartada(fonte, raw):
    linha = {k: v for k, v in _linha(raw, "emendas", "Código da Emenda", "202442900008").items()
             if k in ("Código da Emenda", "Ano da Emenda")}
    linha["Tipo de Emenda"] = None  # csv.DictReader preenche com None o que faltou na linha
    assert fonte.normalize({"emendas": [linha]}) == []


def test_normalize_de_raw_vazio_devolve_lista_vazia(fonte):
    assert fonte.normalize({}) == []


# ---------- fetch ----------

def _zip(nome: str, arquivo: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(nome, (FIX / arquivo).read_bytes())
    return buf.getvalue()


def _pagina(*datas: str) -> str:
    pushes = "\n".join(
        f'arquivos.push({{"ano" : "{d[:4]}", "mes" : "{d[4:6]}", "dia" : "{d[6:]}", '
        f'"origem" :  "X"}});' for d in datas)
    return f"<script>\n    var arquivos = [];\n{pushes}\n</script>"


DADOS = "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida"


def _servidor(visto: list[str] | None = None, paginas: dict[str, str] | None = None,
              status: int = 200) -> httpx.Client:
    paginas = paginas or {"ceis": _pagina("20261112", "20261119"), "cnep": _pagina("20261119")}
    zips = {
        f"{PAGINA}/ceis/20261119": _zip("20261119_CEIS.csv", "cgu_ceis_amostra.csv"),
        f"{PAGINA}/cnep/20261119": _zip("20261119_CNEP.csv", "cgu_cnep_amostra.csv"),
        f"{PAGINA}/emendas-parlamentares/UNICO": _zip("EmendasParlamentares.csv",
                                                       "cgu_emendas_amostra.csv"),
    }

    cdn = {f"{DADOS}/{url.removeprefix(PAGINA + '/')}": corpo for url, corpo in zips.items()}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if visto is not None:
            visto.append(url)
        if status != 200:
            return httpx.Response(status, content=b"erro")
        if url in zips:  # o portal responde 302 para o CDN da CGU
            destino = f"{DADOS}/{url.removeprefix(PAGINA + '/')}"
            return httpx.Response(302, headers={"location": destino})
        if url in cdn:
            return httpx.Response(200, content=cdn[url])
        for cad, html in paginas.items():
            if url == f"{PAGINA}/{cad}":
                return httpx.Response(200, text=html)
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def test_fetch_descobre_a_data_mais_recente_baixa_os_zips_e_salva_em_raw(raw_dir):
    visto: list[str] = []
    out = CguSource(client=_servidor(visto)).fetch()
    assert f"{PAGINA}/ceis/20261119" in visto and f"{PAGINA}/cnep/20261119" in visto
    assert f"{PAGINA}/emendas-parlamentares/UNICO" in visto
    assert not any("20261112" in u for u in visto)
    assert (raw_dir / "cgu" / "20261119_CEIS.zip").is_file()
    assert (raw_dir / "cgu" / "20261119_CNEP.zip").is_file()
    assert (raw_dir / "cgu" / "EmendasParlamentares.zip").is_file()
    assert sorted(i["arquivo"] for i in manifest.carregar(raw_dir)["arquivos"]) == [
        "20261119_CEIS.zip", "20261119_CNEP.zip", "EmendasParlamentares.zip"]
    assert len(out["ceis"]) == 5 and len(out["cnep"]) == 3 and len(out["emendas"]) == 9
    assert out["data_ceis"] == "2026-11-19"
    assert out["ceis"][0]["NOME DO SANCIONADO"] == "Reobote Comércio e Serviços Ltda"


def test_fetch_e_normalize_ponta_a_ponta(raw_dir, raw, fonte):
    facts = fonte.normalize(CguSource(client=_servidor()).fetch())
    esperados = {(f.tipo, f.chave) for f in fonte.normalize(raw)}
    assert esperados
    assert {(f.tipo, f.chave) for f in facts} == esperados


def test_fetch_so_emendas_nao_toca_nos_cadastros_de_sancao(raw_dir):
    visto: list[str] = []
    out = CguSource(client=_servidor(visto)).fetch(cadastros=("emendas",))
    assert set(out) == {"emendas"}
    assert not any("/ceis" in u or "/cnep" in u for u in visto)


def test_fetch_mantem_so_as_colunas_usadas(raw_dir):
    out = CguSource(client=_servidor()).fetch(cadastros=("ceis",))
    assert "FUNDAMENTAÇÃO LEGAL" not in out["ceis"][0]
    assert "CÓDIGO DA SANÇÃO" in out["ceis"][0]


def test_fetch_pagina_sem_data_da_erro_claro(raw_dir):
    cliente = _servidor(paginas={"ceis": "<html>sem arquivos</html>"})
    with pytest.raises(ValueError, match="data"):
        CguSource(client=cliente).fetch(cadastros=("ceis",))


def test_fetch_http_erro_propaga_e_nao_deixa_parcial(raw_dir):
    with pytest.raises(httpx.HTTPStatusError):
        CguSource(client=_servidor(status=500)).fetch(cadastros=("emendas",))
    assert list((raw_dir / "cgu").glob("*")) == []


def test_fetch_zip_com_cabecalho_sem_coluna_esperada_da_erro_claro(raw_dir):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("EmendasParlamentares.csv",
                   '"Coluna Nova";"Outra"\r\n"1";"2"\r\n'.encode("latin-1"))
    corpo = buf.getvalue()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=corpo)

    cliente = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="Código da Emenda"):
        CguSource(client=cliente).fetch(cadastros=("emendas",))


def test_cadastro_desconhecido_e_recusado(raw_dir):
    with pytest.raises(ValueError, match="cadastro"):
        CguSource(client=_servidor()).fetch(cadastros=("pep",))


def test_fetch_recusa_membro_que_descompacta_alem_do_limite(raw_dir):
    cgu = CguSource(client=_servidor(), max_bytes_descomprimido=1_000)
    with pytest.raises(ValueError, match="descompactado"):
        cgu.fetch(cadastros=("emendas",))  # o csv de amostra tem ~5 KB


def test_fetch_aceita_membro_dentro_do_limite(raw_dir):
    out = CguSource(client=_servidor(), max_bytes_descomprimido=1_000_000).fetch(
        cadastros=("emendas",))
    assert len(out["emendas"]) == 9
