"""CeapSource — cota parlamentar (CEAP). Fixture REAL recortada de Ano-2024.json.zip.

A amostra (`fixtures/ceap_2024_amostra.json`) são linhas reais do arquivo oficial da Câmara,
com `cpf` do parlamentar e `passageiro` esvaziados (dado pessoal que o normalize não usa).
Casos de borda sem linha real equivalente (CPF de fornecedor, valor inválido) são derivados
de uma linha real, alterando só o campo testado.
"""
from __future__ import annotations

import copy
import io
import json
import re
import zipfile
from pathlib import Path

import httpx
import pytest

import sources.base
from sources.ceap.source import CAMPOS_USADOS, FONTE, CeapSource, iterar_dados

FIXTURE = Path(__file__).parent / "fixtures" / "ceap_2024_amostra.json"
URL_ZIP_2024 = "https://www.camara.leg.br/cotas/Ano-2024.json.zip"


@pytest.fixture
def raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def fonte() -> CeapSource:
    return CeapSource(client=object())  # normalize é puro: não usa o client


def _linha(raw: dict, id_documento: int, numero: str | None = None) -> dict:
    return next(r for r in raw["dados"]
                if r["idDocumento"] == id_documento and (numero is None or r["numero"] == numero))


def _por_chave(facts):
    """Indexa pelo id oficial (idDocumento); só use com ids que aparecem uma vez."""
    return {f.id_oficial: f for f in facts}


# ---------- normalize: caso positivo ----------

def test_despesa_normal_tem_atributos_exatos_do_contrato(fonte, raw):
    facts = _por_chave(fonte.normalize(raw))
    f = facts["7773081"]
    assert f.tipo == "despesa_ceap"
    assert f.atributos == {
        "deputado_id": "62881",
        "cnpj": "63356042000180",
        "fornecedor": "ALARES",
        "valor": 95.53,
        "categoria": "MANUTENÇÃO DE ESCRITÓRIO DE APOIO À ATIVIDADE PARLAMENTAR",
        "data": "2024-06-29",
    }
    assert isinstance(f.atributos["valor"], float)


def test_rastreabilidade_fonte_id_oficial_e_url(fonte, raw):
    f = _por_chave(fonte.normalize(raw))["7773081"]
    assert f.fonte == FONTE == "camara_ceap"
    assert f.id_oficial == "7773081"
    assert f.url == ("https://www.camara.leg.br/cota-parlamentar/documentos/publ/"
                     "2227/2024/7773081.pdf")


def test_url_cai_para_o_dataset_quando_documento_nao_tem_pdf(fonte, raw):
    f = _por_chave(fonte.normalize(raw))["7855505"]
    assert f.url == URL_ZIP_2024


def test_nome_da_fonte_registravel():
    assert CeapSource.nome == "ceap"


# ---------- normalize: bordas ----------

def test_linhas_de_lideranca_sem_deputado_sao_ignoradas(fonte, raw):
    facts = fonte.normalize(raw)
    assert "7696122" not in {f.id_oficial for f in facts}  # LIDERANÇA DO GOVERNO NA CÂMARA
    assert all(f.atributos["deputado_id"] for f in facts)


def test_valor_negativo_e_preservado(fonte, raw):
    facts = fonte.normalize(raw)
    valores = sorted(f.atributos["valor"] for f in facts if f.atributos["fornecedor"] == "AZUL")
    assert valores == [-44.48, 558.48]


def test_data_ausente_vira_none_sem_inventar_dia(fonte, raw):
    facts = fonte.normalize(raw)
    telefonia = [f for f in facts if f.atributos["categoria"] == "TELEFONIA"]
    assert len(telefonia) == 2
    assert all(f.atributos["data"] is None for f in telefonia)


def test_cnpj_placeholder_zerado_nao_vira_cnpj(fonte, raw):
    # "000.000.000/0000-1" é o preenchimento da Câmara p/ telefonia funcional, não um CNPJ
    facts = fonte.normalize(raw)
    for f in (x for x in facts if x.atributos["categoria"] == "TELEFONIA"):
        assert "cnpj" not in f.atributos and "cpf" not in f.atributos


def test_fornecedor_pessoa_fisica_usa_chave_cpf_e_so_digitos(fonte, raw):
    linha = copy.deepcopy(_linha(raw, 7773081))
    linha["cnpjCPF"] = "111.444.777/35  -  "  # CPF fictício no formato do arquivo
    f = fonte.normalize({"dados": [linha]})[0]
    assert f.atributos["cpf"] == "11144477735"
    assert "cnpj" not in f.atributos


def test_valor_invalido_descarta_a_linha_em_vez_de_inventar_zero(fonte, raw):
    boa = _linha(raw, 7773081)
    ruim = copy.deepcopy(boa)
    ruim["idDocumento"] = 1
    ruim["valorLiquido"] = "n/d"
    facts = fonte.normalize({"dados": [boa, ruim]})
    assert [f.id_oficial for f in facts] == ["7773081"]


def test_raw_vazio_nao_quebra(fonte):
    assert fonte.normalize({}) == []
    assert fonte.normalize({"dados": []}) == []


# ---------- normalize: chave determinística, independente do lote ----------

CHAVE = re.compile(r"(\d+|sem-doc):[0-9a-f]{10}")


def test_chave_tem_sempre_o_formato_id_dois_pontos_hash(fonte, raw):
    facts = fonte.normalize(raw)
    assert all(CHAVE.fullmatch(f.chave) for f in facts)
    assert _por_chave(facts)["7773081"].chave.startswith("7773081:")


def test_chave_nao_depende_do_lote(fonte, raw):
    # linha única (amostra) e lote completo precisam gerar a MESMA chave, p/ o upsert não duplicar
    completo = {f.id_oficial: f.chave for f in fonte.normalize(raw)}
    sozinha = fonte.normalize({"dados": [_linha(raw, 7773081)]})[0]
    assert sozinha.chave == completo["7773081"]
    # id repetido: cada linha mantém a chave mesmo sem a "irmã" no lote
    azul = [r for r in raw["dados"] if r["idDocumento"] == 256307]
    chaves_lote = [f.chave for f in fonte.normalize({"dados": azul})]
    chaves_solo = [fonte.normalize({"dados": [r]})[0].chave for r in azul]
    assert chaves_lote == chaves_solo


def test_chave_muda_quando_o_conteudo_muda(fonte, raw):
    base = _linha(raw, 7773081)
    alt = copy.deepcopy(base)
    alt["valorLiquido"] = "96.00"
    assert (fonte.normalize({"dados": [base]})[0].chave
            != fonte.normalize({"dados": [alt]})[0].chave)


# ---------- normalize: unicidade de chave (idDocumento repetido / zero) ----------

def test_id_documento_repetido_gera_chaves_distintas_e_nao_perde_valor(fonte, raw):
    facts = fonte.normalize(raw)
    azul = [f for f in facts if f.atributos["fornecedor"] == "AZUL"]
    assert len(azul) == 2
    assert len({f.chave for f in azul}) == 2
    assert all(f.chave.startswith("256307:") for f in azul)
    assert all(f.id_oficial == "256307" for f in azul)  # id oficial segue o da Câmara


def test_id_documento_zero_gera_chaves_distintas(fonte, raw):
    facts = fonte.normalize(raw)
    sem_doc = [f for f in facts if f.atributos["categoria"] == "TELEFONIA"]
    assert len({f.chave for f in sem_doc}) == 2
    assert all(f.chave.startswith("sem-doc:") for f in sem_doc)


def test_chaves_sao_unicas_e_deterministicas(fonte, raw):
    a = [f.chave for f in fonte.normalize(raw)]
    b = [f.chave for f in fonte.normalize(copy.deepcopy(raw))]
    assert a == b
    assert len(a) == len(set(a))


def test_linhas_identicas_nao_colidem(fonte, raw):
    linha = _linha(raw, 256307, "LJHZYZ")
    facts = fonte.normalize({"dados": [copy.deepcopy(linha), copy.deepcopy(linha)]})
    assert len({f.chave for f in facts}) == 2


# ---------- idDocumento fora do padrão ----------

@pytest.mark.parametrize("bruto", ["ABC-123", "12.5", "", None, 0, "0", -5, [1], {"a": 1}])
def test_id_documento_nao_numerico_vira_sem_doc_sem_quebrar(fonte, raw, bruto):
    linha = copy.deepcopy(_linha(raw, 7773081))
    linha["idDocumento"] = bruto
    f = fonte.normalize({"dados": [linha]})[0]
    assert f.chave.startswith("sem-doc:")
    assert f.id_oficial == f.chave


@pytest.mark.parametrize("bruto", [7773081, "7773081", " 7773081 ", 7773081.0])
def test_id_documento_numerico_em_outros_tipos_vale_como_inteiro(fonte, raw, bruto):
    linha = copy.deepcopy(_linha(raw, 7773081))
    original = fonte.normalize({"dados": [copy.deepcopy(linha)]})[0]
    linha["idDocumento"] = bruto
    f = fonte.normalize({"dados": [linha]})[0]
    assert f.chave == original.chave  # mesma chave, qualquer que seja a representação
    assert f.id_oficial == "7773081"


def test_ids_nao_numericos_diferentes_nao_colidem_e_sao_estaveis(fonte, raw):
    a, b = (copy.deepcopy(_linha(raw, 7773081)) for _ in range(2))
    a["idDocumento"], b["idDocumento"] = "ABC-1", "ABC-2"
    ka = [f.chave for f in fonte.normalize({"dados": [a, b]})]
    assert len(set(ka)) == 2
    assert ka == [f.chave for f in fonte.normalize({"dados": [b, a]})][::-1]  # independe da ordem


# ---------- fetch ----------

def _zip_bytes(raw: dict, nome: str = "Ano-2024.json") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(nome, json.dumps(raw, ensure_ascii=False))
    return buf.getvalue()


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def _client(corpo: bytes, status: int = 200, visto: list | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if visto is not None:
            visto.append(str(request.url))
        return httpx.Response(status, content=corpo)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_baixa_o_zip_oficial_salva_em_raw_e_devolve_dados(raw, raw_dir):
    visto: list[str] = []
    src = CeapSource(client=_client(_zip_bytes(raw), visto=visto))
    out = src.fetch(ano=2024)
    assert visto == [URL_ZIP_2024]
    assert (raw_dir / "ceap" / "Ano-2024.json.zip").is_file()
    assert out["ano"] == 2024
    assert len(out["dados"]) == len(raw["dados"])
    assert out["dados"][0]["fornecedor"] == raw["dados"][0]["fornecedor"]


def test_fetch_e_normalize_ponta_a_ponta(raw, raw_dir):
    src = CeapSource(client=_client(_zip_bytes(raw)))
    facts = src.normalize(src.fetch(ano=2024))
    assert {f.tipo for f in facts} == {"despesa_ceap"}
    assert len(facts) == 7  # 8 linhas na amostra − 1 liderança


def test_fetch_max_linhas_conta_so_linhas_de_deputado(raw, raw_dir):
    # a liderança vem antes na amostra; o limite não pode ser gasto com ela
    dados = [_linha(raw, 7696122)] + [r for r in raw["dados"] if r.get("idDeputado")]
    src = CeapSource(client=_client(_zip_bytes({"dados": dados})))
    out = src.fetch(ano=2024, max_linhas=2)
    assert len(out["dados"]) == 2
    assert all(r.get("idDeputado") for r in out["dados"])


def test_fetch_max_deputados_limita_deputados_distintos(raw, raw_dir):
    src = CeapSource(client=_client(_zip_bytes(raw)))
    out = src.fetch(ano=2024, max_deputados=1)
    assert {r["idDeputado"] for r in out["dados"]} == {62881}
    assert len(out["dados"]) == 6  # todas as linhas do primeiro deputado


def test_fetch_http_erro_propaga(raw_dir):
    src = CeapSource(client=_client(b"nope", status=404))
    with pytest.raises(httpx.HTTPStatusError):
        src.fetch(ano=1900)
    assert not (raw_dir / "ceap" / "Ano-1900.json.zip").exists()  # sem lixo parcial


def test_fetch_zip_sem_json_da_erro_claro(raw_dir):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("leiame.txt", "oi")
    src = CeapSource(client=_client(buf.getvalue()))
    with pytest.raises(ValueError, match="json"):
        src.fetch(ano=2024)


# ---------- fetch: streaming, campos usados, teto de tamanho ----------

def test_leitura_em_streaming_com_pedacos_minusculos_reproduz_o_json(raw, raw_dir):
    # pedaço de 7 caracteres força cortes no meio de strings, números e objetos
    src = CeapSource(client=_client(_zip_bytes(raw)), tamanho_pedaco=7)
    out = src.fetch(ano=2024)
    esperado = [{k: v for k, v in r.items() if k in CAMPOS_USADOS} for r in raw["dados"]]
    assert out["dados"] == esperado


def test_fetch_guarda_so_os_campos_usados_pelo_normalize(raw, raw_dir):
    out = CeapSource(client=_client(_zip_bytes(raw))).fetch(ano=2024)
    campos = set().union(*(r.keys() for r in out["dados"]))
    assert campos <= CAMPOS_USADOS
    assert "cpf" not in campos and "passageiro" not in campos
    # e o normalize do slim dá exatamente os mesmos fatos que o do bruto completo
    src = CeapSource(client=object())
    assert ([f.model_dump(exclude={"coletado_em"}) for f in src.normalize(out)]
            == [f.model_dump(exclude={"coletado_em"}) for f in src.normalize(raw)])


def test_max_linhas_para_de_ler_o_arquivo(raw, raw_dir):
    # JSON truncado depois de 2 linhas de deputado: só passa se a leitura parar no limite
    dados = [r for r in raw["dados"] if r.get("idDeputado")]
    lista = json.dumps(dados[:2], ensure_ascii=False)[:-1]  # sem o "]" final
    truncado = '{"dados": ' + lista + ', {"idDeputado": 1, "valorLiq'  # 3ª linha cortada
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Ano-2024.json", truncado)
    src = CeapSource(client=_client(buf.getvalue()))
    assert len(src.fetch(ano=2024, max_linhas=2)["dados"]) == 2
    with pytest.raises(ValueError, match="incompleto"):
        src.fetch(ano=2024)


def test_zip_acima_do_teto_descompactado_e_recusado(raw, raw_dir):
    src = CeapSource(client=_client(_zip_bytes(raw)), max_descompactado=100)
    with pytest.raises(ValueError, match="limite"):
        src.fetch(ano=2024)


def test_teto_vale_tambem_para_o_que_foi_realmente_lido(raw):
    # cabeçalho do zip pode mentir sobre o tamanho (zip bomb): o leitor conta o que consome
    fluxo = io.BytesIO(json.dumps(raw).encode("utf-8"))
    with pytest.raises(ValueError, match="limite"):
        list(iterar_dados(fluxo, pedaco=64, teto=100))
