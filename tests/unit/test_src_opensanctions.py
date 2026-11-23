"""OpenSanctionsSource — dataset br_pep (pessoas politicamente expostas, divulgadas pela CGU).

Fixture SINTÉTICA: `opensanctions_br_pep_amostra.jsonl` = 6 entidades inventadas (nomes, ids e
CPFs mascarados fictícios) com o MESMO formato de `targets.nested.json` (uma por linha, como o
arquivo oficial). Os dados reais do OpenSanctions têm licença CC BY-NC e não são redistribuídos
aqui. Casos de borda sem entidade equivalente (sem ocupação, schema diferente, CPF inválido, data
inválida) são derivados de uma entidade da fixture mudando só o campo testado.

Por que `targets.nested.json` e não `targets.simple.csv`: o CSV só traz nome e CPF mascarado; cargo,
órgão, início e fim (exigidos por docs/fact_types.md) só existem no nested.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import httpx
import pytest

import sources.base
from sources import manifest
from sources.opensanctions.source import FONTE, OpenSanctionsSource

FIX = Path(__file__).parent / "fixtures" / "opensanctions_br_pep_amostra.jsonl"
URL = "https://data.opensanctions.org/datasets/latest/br_pep/targets.nested.json"
CDN = "https://data.opensanctions.org/artifacts/br_pep/20261117020206-blq/targets.nested.json"


@pytest.fixture
def entidades() -> list[dict]:
    return [json.loads(ln) for ln in FIX.read_text(encoding="utf-8").splitlines() if ln]


@pytest.fixture
def raw(entidades) -> dict:
    return {"entities": entidades}


@pytest.fixture
def fonte() -> OpenSanctionsSource:
    return OpenSanctionsSource(client=object())  # normalize é puro: não usa o client


def _por_chave(facts):
    return {f.chave: f for f in facts}


def _entidade(entidades: list[dict], id_: str) -> dict:
    return copy.deepcopy(next(e for e in entidades if e["id"] == id_))


def _sem_hora(facts) -> list[dict]:
    return [f.model_dump(mode="json", exclude={"coletado_em"}) for f in facts]


# ---------- normalize ----------

def test_pep_de_prefeito_encerrado_tem_atributos_exatos(fonte, raw):
    f = _por_chave(fonte.normalize(raw))["NK-sintetico-0001"]
    assert f.tipo == "pep" and f.fonte == FONTE
    assert f.id_oficial == "NK-sintetico-0001"
    assert f.url == "https://www.opensanctions.org/entities/NK-sintetico-0001/"
    ocupacao = {"cargo": "Mayor", "orgao": "Vila Exemplo-SC", "posicao": "Mayor, Vila Exemplo-SC",
                "inicio": "2021-01-01", "fim": "2024-12-31", "status": "ended"}
    assert f.atributos == {
        "nome": "ORLANDO EXEMPLO DE ARAUJO", "cpf": "***111222**", "cpfs": ["***111222**"],
        "cargo": "Mayor", "orgao": "Vila Exemplo-SC", "inicio": "2021-01-01", "fim": "2024-12-31",
        "status": "ended", "ocupacoes": [ocupacao],
    }


def test_cpf_mascarado_mantem_asteriscos_e_so_digitos_e_asteriscos(fonte, raw):
    for f in fonte.normalize(raw):
        assert f.atributos["cpf"] is None or (
            len(f.atributos["cpf"]) == 11 and set(f.atributos["cpf"]) <= set("*0123456789"))


def test_varias_ocupacoes_escolhe_a_mais_recente_e_guarda_todas(fonte, raw):
    a = _por_chave(fonte.normalize(raw))["SINT-0002"].atributos
    assert (a["cargo"], a["orgao"]) == ("Federal Deputy", "Chamber of Deputies")
    assert (a["inicio"], a["fim"]) == ("2024-03-25", "2024-08-01")
    assert len(a["ocupacoes"]) == 4
    assert sorted(o["inicio"] for o in a["ocupacoes"]) == [
        "2023-02-08", "2023-04-28", "2023-08-04", "2024-03-25"]


def test_ocupacao_em_exercicio_vence_ocupacao_encerrada_mais_recente(fonte, entidades):
    e = _entidade(entidades, "SINT-0002")
    atual = copy.deepcopy(e["properties"]["positionOccupancies"][0])
    atual["properties"].update(status=["current"], startDate=["2020-01-01"], endDate=["2030-01-01"])
    e["properties"]["positionOccupancies"].append(atual)
    a = fonte.normalize({"entities": [e]})[0].atributos
    assert (a["status"], a["inicio"], a["fim"]) == ("current", "2020-01-01", "2030-01-01")


def test_ocupacao_sem_status_e_sem_data_fim_fica_com_none(fonte, raw):
    a = _por_chave(fonte.normalize(raw))["NK-sintetico-0004"].atributos
    assert a["fim"] is None and a["status"] is None and a["inicio"] == "2018-02-14"
    assert (a["cargo"], a["orgao"]) == ("Secretary of State", "Secretariat of Public Security")


def test_ocupacao_atual_com_fim_de_mandato_previsto(fonte, raw):
    a = _por_chave(fonte.normalize(raw))["SINT-0005"].atributos
    assert (a["status"], a["inicio"], a["fim"]) == ("current", "2023-02-01", "2027-01-31")
    assert (a["cargo"], a["orgao"]) == ("State Representative", "Roraima")


def test_cargo_sem_virgula_fica_inteiro_e_orgao_none(fonte, raw):
    a = _por_chave(fonte.normalize(raw))["SINT-0006"].atributos
    assert a["cargo"] == "Governor of Amapá" and a["orgao"] is None


def test_dois_cpfs_na_mesma_entidade_deixa_cpf_none_e_lista_ambos(fonte, raw):
    a = _por_chave(fonte.normalize(raw))["SINT-0003"].atributos
    assert a["cpf"] is None
    assert a["cpfs"] == ["***555666**", "***777888**"]  # homônimos fundidos: não escolhemos um


def test_pessoa_sem_ocupacao_vira_pep_sem_cargo(fonte, entidades):
    e = _entidade(entidades, "SINT-0006")
    del e["properties"]["positionOccupancies"]
    [f] = fonte.normalize({"entities": [e]})
    assert f.atributos["cargo"] is None and f.atributos["ocupacoes"] == []
    assert f.atributos["nome"] == "CLÁUDIO LUÍS FICTÍCIO VIANA"


def test_pessoa_sem_cpf_fica_com_cpf_none(fonte, entidades):
    e = _entidade(entidades, "SINT-0006")
    del e["properties"]["taxNumber"]
    [f] = fonte.normalize({"entities": [e]})
    assert f.atributos["cpf"] is None and f.atributos["cpfs"] == []


@pytest.mark.parametrize("lixo", ["abc", "123", "***.12.3-**", ""])
def test_tax_number_invalido_e_ignorado(fonte, entidades, lixo):
    e = _entidade(entidades, "SINT-0006")
    e["properties"]["taxNumber"] = [lixo]
    [f] = fonte.normalize({"entities": [e]})
    assert f.atributos["cpf"] is None and f.atributos["cpfs"] == []


@pytest.mark.parametrize("data", ["2021", "ontem", "2021-13-40", ""])
def test_data_invalida_ou_parcial_vira_none(fonte, entidades, data):
    e = _entidade(entidades, "NK-sintetico-0001")
    e["properties"]["positionOccupancies"][0]["properties"]["endDate"] = [data]
    [f] = fonte.normalize({"entities": [e]})
    assert f.atributos["fim"] is None and f.atributos["inicio"] == "2021-01-01"


def test_entidade_que_nao_e_pessoa_ou_sem_id_e_ignorada(fonte, entidades):
    org = _entidade(entidades, "SINT-0006")
    org["schema"] = "Organization"
    sem_id = _entidade(entidades, "SINT-0003")
    del sem_id["id"]
    assert fonte.normalize({"entities": [org, sem_id]}) == []


def test_normalize_de_raw_vazio_devolve_lista_vazia(fonte):
    assert fonte.normalize({}) == []


def test_todo_fato_tem_fonte_id_oficial_e_url(fonte, raw):
    facts = fonte.normalize(raw)
    assert len(facts) == 6 and {f.tipo for f in facts} == {"pep"}
    assert all(f.fonte and f.id_oficial and f.url for f in facts)
    assert len({f.chave for f in facts}) == 6


# ---------- fetch ----------

@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def _client(corpo: bytes, status: int = 200, visto: list | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if visto is not None:
            visto.append(str(request.url))
        if str(request.url) == URL:  # o site responde 307 para o artefato versionado
            return httpx.Response(307, headers={"location": CDN})
        return httpx.Response(status, content=corpo)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_segue_o_redirect_guarda_o_arquivo_original_e_devolve_entidades(raw_dir):
    corpo = FIX.read_bytes()
    visto: list[str] = []
    out = OpenSanctionsSource(client=_client(corpo, visto=visto)).fetch()
    assert visto == [URL, CDN]
    assert (raw_dir / "opensanctions" / "br_pep.targets.nested.json").read_bytes() == corpo
    assert manifest.carregar(raw_dir)["arquivos"][0]["sha256"] == hashlib.sha256(corpo).hexdigest()
    assert [e["id"] for e in out["entities"]][:2] == ["NK-sintetico-0001", "SINT-0002"]
    assert len(out["entities"]) == 6


def test_fetch_compacta_sem_mudar_o_resultado_do_normalize(raw_dir, raw, fonte):
    out = OpenSanctionsSource(client=_client(FIX.read_bytes())).fetch()
    assert "referents" not in out["entities"][0]
    assert _sem_hora(fonte.normalize(out)) == _sem_hora(fonte.normalize(raw))


def test_fetch_max_entidades_gera_amostra(raw_dir):
    out = OpenSanctionsSource(client=_client(FIX.read_bytes())).fetch(max_entidades=2)
    assert len(out["entities"]) == 2


def test_fetch_ignora_linhas_em_branco_e_nao_pessoas(raw_dir):
    posicao = json.dumps({"id": "NK-pos", "schema": "Position", "properties": {}})
    corpo = FIX.read_bytes() + b"\n\n" + posicao.encode() + b"\n"
    out = OpenSanctionsSource(client=_client(corpo)).fetch()
    assert len(out["entities"]) == 6


def test_fetch_json_corrompido_da_erro_com_numero_da_linha(raw_dir):
    corpo = FIX.read_bytes() + b'{"id": "quebrado"\n'
    with pytest.raises(ValueError, match="linha 7"):
        OpenSanctionsSource(client=_client(corpo)).fetch()


def test_fetch_http_erro_propaga_sem_arquivo_parcial(raw_dir):
    with pytest.raises(httpx.HTTPStatusError):
        OpenSanctionsSource(client=_client(b"nope", status=503)).fetch()
    assert list((raw_dir / "opensanctions").glob("*")) == []
