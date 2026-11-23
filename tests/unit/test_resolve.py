"""ingest/resolve — funções puras: fatos entram, (fatos enriquecidos, links, ambiguidades) saem."""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from contracts import Fact
from ingest.deploy_check import verificar_envio
from ingest.pipeline import (
    Opcoes,
    Pipeline,
    chamar_fetch,
    montar_kwargs,
    selecionar_escopo,
)
from ingest.pseudonimizar import pseudonimizar_fatos, salt_do_ambiente
from ingest.resolve import (
    normaliza_nome,
    resolver_candidaturas,
    resolver_cnpj,
    resolver_emendas,
    resolver_peps,
)
from ingest.resolve.comum import cnpj_valido, confronto_cpf
from ingest.varredura import cpfs_integros, varrer_banco
from repo.links import EntityLink
from repo.store import Store
from sources import REGISTRY
from sources.base import Source
from sources.tse.source import TseSource

FIX = Path(__file__).parent / "fixtures"


def F(tipo, chave, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def dep(id_, nome, uf="MG", partido="PL", **extra):
    return F("deputado", id_, nome=nome, uf=uf, partido=partido, **extra)


def cand(sq, nome_urna, nome=None, uf="MG", partido="PL", cpf=None, ano=2022, **extra):
    return F("candidatura", sq, ano=ano, cpf=cpf, nome=nome or nome_urna, nome_urna=nome_urna,
             cargo="Deputado Federal", uf=uf, partido=partido, **extra)


def por_chave(fatos):
    return {f.chave: f for f in fatos}


# ---------- normalização / helpers ----------

def test_normaliza_nome_tira_acento_caixa_e_espaco_duplo():
    assert normaliza_nome("  João   d'Ávila ") == "JOAO D'AVILA"
    assert normaliza_nome(None) == ""


def test_confronto_cpf_cobre_igual_diferente_compativel_e_desconhecido():
    assert confronto_cpf("12345678901", "123.456.789-01") == "igual"
    assert confronto_cpf("12345678901", "12345678902") == "diferente"
    assert confronto_cpf("***456789**", "12345678901") == "compativel"
    assert confronto_cpf("***456780**", "12345678901") == "diferente"
    assert confronto_cpf(None, "12345678901") == "desconhecido"
    assert confronto_cpf("***********", "12345678901") == "desconhecido"


def test_cnpj_valido_checa_digito_verificador():
    assert cnpj_valido("00000000000191")
    assert not cnpj_valido("00000000000192")
    assert not cnpj_valido("11111111111111")
    assert not cnpj_valido("123")


# ---------- candidatura -> deputado ----------

def test_candidatura_liga_por_nome_urna_e_uf_com_cf_08_e_preenche_deputado_id():
    r = resolver_candidaturas([cand("10", "Amancio Bruneto")], [dep("1", "Amâncio Bruneto")])
    assert r.links == [EntityLink("candidatura:10", "deputado:1", "nome_norm", 0.8)]
    assert por_chave(r.fatos)["10"].atributos["deputado_id"] == "1"
    assert por_chave(r.fatos)["10"].atributos["deputado_cf"] == 0.8
    assert r.ambiguos == [] and r.sem_match == []


def test_candidatura_liga_pelo_nome_civil_quando_o_nome_de_urna_difere():
    r = resolver_candidaturas(
        [cand("10", "Zé do Posto", nome="José da Silva")],
        [dep("1", "José da Silva")])
    assert [lk.destino for lk in r.links] == ["deputado:1"]


def test_candidatura_cpf_vence_nome_e_tem_cf_1():
    r = resolver_candidaturas(
        [cand("10", "Nome Totalmente Outro", cpf="12345678901")],
        [dep("1", "Fulano", cpf="123.456.789-01")])
    assert r.links == [EntityLink("candidatura:10", "deputado:1", "cpf", 1.0)]
    assert r.fatos[0].atributos["deputado_cf"] == 1.0


def test_candidatura_de_outra_uf_nao_liga():
    r = resolver_candidaturas([cand("10", "Joao Silva", uf="SP")], [dep("1", "Joao Silva", "MG")])
    assert r.links == [] and r.sem_match == ["candidatura:10"]
    assert "deputado_id" not in por_chave(r.fatos)["10"].atributos


def test_candidatura_cpf_diferente_descarta_homonimo():
    r = resolver_candidaturas(
        [cand("10", "Joao Silva", cpf="11111111111")],
        [dep("1", "Joao Silva", cpf="22222222222")])
    assert r.links == [] and r.ambiguos == []


def test_candidatura_dois_deputados_com_o_mesmo_nome_e_uf_e_ambigua_e_nao_liga():
    r = resolver_candidaturas([cand("10", "Joao Silva", partido="XX")],
                              [dep("1", "Joao Silva", partido="AA"),
                               dep("2", "Joao Silva", partido="BB")])
    assert r.links == []
    (amb,) = r.ambiguos
    assert amb.origem == "candidatura:10"
    assert set(amb.candidatos) == {"deputado:1", "deputado:2"}
    assert "deputado_id" not in por_chave(r.fatos)["10"].atributos
    assert "deputado_cf" not in por_chave(r.fatos)["10"].atributos


def test_dois_candidatos_com_o_mesmo_nome_e_uf_para_um_deputado_sao_ambiguos():
    r = resolver_candidaturas([cand("10", "Joao Silva", partido="XX"),
                               cand("11", "Joao Silva", partido="YY")],
                              [dep("1", "Joao Silva", partido="AA")])
    assert r.links == []
    assert {a.origem for a in r.ambiguos} == {"candidatura:10", "candidatura:11"}


def test_partido_desempata_ambiguidade_com_cf_07():
    r = resolver_candidaturas([cand("10", "Joao Silva", partido="PL")],
                              [dep("1", "Joao Silva", partido="PL"),
                               dep("2", "Joao Silva", partido="PT")])
    assert r.links == [EntityLink("candidatura:10", "deputado:1", "nome_norm", 0.7)]
    assert r.fatos[0].atributos["deputado_cf"] == 0.7
    assert r.ambiguos == []


def test_partido_igual_nos_dois_lados_continua_ambiguo():
    r = resolver_candidaturas([cand("10", "Joao Silva", partido="PL")],
                              [dep("1", "Joao Silva", partido="PL"),
                               dep("2", "Joao Silva", partido="PL")])
    assert r.links == [] and len(r.ambiguos) == 1


def test_mesmo_deputado_em_duas_eleicoes_liga_as_duas():
    r = resolver_candidaturas([cand("10", "Joao Silva", ano=2018), cand("11", "Joao Silva")],
                              [dep("1", "Joao Silva")])
    assert {lk.origem for lk in r.links} == {"candidatura:10", "candidatura:11"}


def test_lista_da_camara_com_id_repetido_nao_gera_ambiguidade():
    # a API repete o deputado (uma linha por partido que ele passou)
    r = resolver_candidaturas([cand("10", "Delegada Iara")],
                              [dep("1", "Delegada Iara", partido="AVANTE"),
                               dep("1", "Delegada Iara", partido="PL")])
    assert [lk.destino for lk in r.links] == ["deputado:1"]


def test_candidatura_que_ja_tem_deputado_id_nao_e_reprocessada():
    c = cand("10", "Joao Silva", deputado_id="99")
    r = resolver_candidaturas([c], [dep("1", "Joao Silva")])
    assert r.links == [] and por_chave(r.fatos)["10"].atributos["deputado_id"] == "99"


def test_resolucao_e_pura_e_idempotente():
    entrada = [cand("10", "Joao Silva")]
    deps = [dep("1", "Joao Silva")]
    r1 = resolver_candidaturas(entrada, deps)
    r2 = resolver_candidaturas(entrada, deps)
    assert r1.links == r2.links
    assert "deputado_id" not in entrada[0].atributos  # entrada intacta
    r3 = resolver_candidaturas(r1.fatos, deps)  # reaplicar sobre o já enriquecido não muda nada
    assert [f.atributos for f in r3.fatos] == [f.atributos for f in r1.fatos]


def test_fixture_real_de_mg_taxa_e_casos_conhecidos():
    d = json.loads((FIX / "resolve_mg_amostra.json").read_text(encoding="utf-8"))
    deps = [Fact(**x) for x in d["deputados"]]
    cands = [Fact(**x) for x in d["candidaturas"]]
    r = resolver_candidaturas(cands, deps)
    ligados = {lk.origem: lk.destino for lk in r.links}
    # nome idêntico nas duas bases
    assert ligados["candidatura:" + d["esperado"]["sq_plinio_abi_mansur"]] == (
        "deputado:" + d["esperado"]["plinio_abi_mansur"])
    assert {lk.cf for lk in r.links} == {0.8}
    # nomes divergentes (nome de urna "DELEGADA IARA BARBOSA" x "Delegada Iara"): sem match
    assert "candidatura:130001603582" not in ligados
    assert "candidatura:130001603582" in r.sem_match


# ---------- emenda -> deputado ----------

def emenda(cod, autor, **extra):
    return F("emenda", cod, autor_nome=autor, ano=2024, valor_empenhado=10.0, valor_pago=5.0,
             municipio_ibge="3106200", **extra)


def test_emenda_liga_por_nome_normalizado_e_fan_out_para_todas_as_emendas_do_autor():
    r = resolver_emendas([emenda("e1", "AMANCIO BRUNETO"), emenda("e2", "Amâncio Bruneto")],
                         [dep("1", "Amancio Bruneto")])
    assert {lk.origem for lk in r.links} == {"emenda:e1", "emenda:e2"}
    assert all(lk == EntityLink(lk.origem, "deputado:1", "nome_norm", 0.8) for lk in r.links)
    assert all(f.atributos["deputado_id"] == "1" and f.atributos["deputado_cf"] == 0.8
               for f in r.fatos)


def test_emenda_de_bancada_ou_autor_desconhecido_fica_sem_match():
    r = resolver_emendas([emenda("e1", "BANCADA DE MINAS GERAIS"), emenda("e2", None)],
                         [dep("1", "Amancio Bruneto")])
    assert r.links == [] and sorted(r.sem_match) == ["emenda:e1", "emenda:e2"]
    assert all("deputado_id" not in f.atributos for f in r.fatos)


def test_emenda_com_nome_de_dois_deputados_e_ambigua():
    r = resolver_emendas([emenda("e1", "Cassio Silva")],
                         [dep("1", "Cassio Silva", "MG"), dep("2", "Cassio Silva", "SP")])
    assert r.links == [] and len(r.ambiguos) == 1
    assert set(r.ambiguos[0].candidatos) == {"deputado:1", "deputado:2"}


def test_emenda_que_ja_traz_deputado_id_fica_como_esta():
    r = resolver_emendas([emenda("e1", "Amancio Bruneto", deputado_id="7")],
                         [dep("1", "Amancio Bruneto")])
    assert r.links == [] and r.fatos[0].atributos["deputado_id"] == "7"
    assert "deputado_cf" not in r.fatos[0].atributos  # id veio da fonte: ausente = 1.0


# ---------- pep -> deputado ----------

def pep(id_, nome, cpf=None, **extra):
    return F("pep", id_, nome=nome, cpf=cpf, cargo="Federal Deputy", **extra)


def test_pep_por_nome_civil_do_candidato_ligado_e_cpf_mascarado_compativel_cf_095():
    deps = [dep("1", "Amancio Bruneto")]
    cands = [cand("10", "Amancio Bruneto", nome="AMANCIO JORDAO BRUNETO MOURAO", cpf="12345678901")]
    links_c = [EntityLink("candidatura:10", "deputado:1", "nome_norm", 0.8)]
    r = resolver_peps([pep("p1", "Amâncio Jordao Bruneto Mourao", cpf="***456789**")],
                      deps, cands, links_c)
    assert r.links == [EntityLink("pep:p1", "deputado:1", "cpf", 0.95)]


def test_pep_cpf_mascarado_incompativel_descarta_mesmo_com_nome_igual():
    deps = [dep("1", "Amancio Bruneto")]
    cands = [cand("10", "Amancio Bruneto", nome="AMANCIO JORDAO BRUNETO MOURAO", cpf="12345678901")]
    links_c = [EntityLink("candidatura:10", "deputado:1", "nome_norm", 0.8)]
    r = resolver_peps([pep("p1", "AMANCIO JORDAO BRUNETO MOURAO", cpf="***999999**")],
                      deps, cands, links_c)
    assert r.links == []


def test_pep_por_nome_civil_sem_cpf_cf_07_e_por_nome_parlamentar_cf_05():
    deps = [dep("1", "Amancio Bruneto", nome_civil="AMANCIO JORDAO BRUNETO MOURAO"),
            dep("2", "Maria Souza")]
    r = resolver_peps([pep("p1", "AMANCIO JORDAO BRUNETO MOURAO"), pep("p2", "Maria Souza")], deps)
    assert {lk.origem: (lk.destino, lk.cf) for lk in r.links} == {
        "pep:p1": ("deputado:1", 0.7), "pep:p2": ("deputado:2", 0.5)}


def test_pep_homonimo_de_dois_deputados_e_ambiguo_e_pep_sem_par_e_sem_match():
    deps = [dep("1", "Cassio Silva", "MG"), dep("2", "Cassio Silva", "SP")]
    r = resolver_peps([pep("p1", "Cassio Silva"), pep("p2", "Outra Pessoa")], deps)
    assert r.links == [] and [a.origem for a in r.ambiguos] == ["pep:p1"]
    assert r.sem_match == ["pep:p2"]


def test_pep_so_usa_candidatura_com_link_formoso():
    deps = [dep("1", "Amancio Bruneto")]
    cands = [cand("10", "Amancio Bruneto", nome="AMANCIO JORDAO BRUNETO MOURAO")]
    fraco = [EntityLink("candidatura:10", "deputado:1", "nome_norm", 0.7)]
    r = resolver_peps([pep("p1", "AMANCIO JORDAO BRUNETO MOURAO")], deps, cands, fraco)
    assert r.links == []


# ---------- cnpj ----------

def test_despesa_liga_a_empresa_e_a_cada_sancao_por_cnpj_exato_cf_1():
    desp = [F("despesa_ceap", "d1", deputado_id="1", cnpj="00000000000191", valor=-10.0, data=None),
            F("despesa_ceap", "d2", deputado_id="1", cnpj="11222333000181", valor=5.0),
            F("despesa_ceap", "d3", deputado_id="1", cpf="12345678901", valor=5.0),
            F("despesa_ceap", "d4", deputado_id="1", valor=5.0)]
    emp = [F("empresa", "00000000000191", razao_social="X")]
    san = [F("sancao", "CEIS:1", cnpj="00000000000191", cadastro="CEIS"),
           F("sancao", "CNEP:2", cnpj="00000000000191", cadastro="CNEP"),
           F("sancao", "CEIS:3", cnpj=None, cpf="12345678901")]
    r = resolver_cnpj(desp, emp, san)
    assert sorted((lk.origem, lk.destino, lk.metodo, lk.cf) for lk in r.links) == [
        ("despesa_ceap:d1", "empresa:00000000000191", "cnpj", 1.0),
        ("despesa_ceap:d1", "sancao:CEIS:1", "cnpj", 1.0),
        ("despesa_ceap:d1", "sancao:CNEP:2", "cnpj", 1.0)]
    assert [f.chave for f in r.fatos] == ["d1", "d2", "d3", "d4"]


def test_cnpj_sem_empresa_nem_sancao_nao_gera_link():
    r = resolver_cnpj([F("despesa_ceap", "d2", cnpj="11222333000181", valor=5.0)], [], [])
    assert r.links == []


# =====================================================================================
# ingest/pipeline.py — fontes falsas só no fetch (rede); normalize, resolve e DuckDB são reais
# =====================================================================================

CHAMADAS: list[tuple[str, dict]] = []
CNPJ_A, CNPJ_B = "00000000000191", "11222333000181"  # dígitos verificadores válidos


def _fato(tipo, chave, fonte="fake", **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte=fonte, id_oficial=chave)


class FakeCamara(Source):
    nome = "camara"

    def fetch(self, legislatura=57, data_inicio="x", data_fim="y", max_votacoes=None,
              incluir_proposicoes=False, detalhar_deputados=False):
        CHAMADAS.append(("camara", {"data_inicio": data_inicio, "data_fim": data_fim,
                                    "max_votacoes": max_votacoes,
                                    "detalhar_deputados": detalhar_deputados}))
        return {"deputados": [{"id": 1, **({"_detalhe": {}} if detalhar_deputados else {})}]}

    def fetch_proposicoes(self, data_inicio, data_fim, deputado_ids=None, siglas_tipo=None,
                          max_proposicoes=None):
        CHAMADAS.append(("camara_prop", {"data_inicio": data_inicio, "data_fim": data_fim,
                                         "deputado_ids": deputado_ids,
                                         "siglas_tipo": siglas_tipo,
                                         "max_proposicoes": max_proposicoes}))
        return {"proposicoes": [{"id": "p1", "deps": ["1", "3"]}, {"id": "p2", "deps": ["3"]},
                                {"id": "p3", "deps": ["2"]}], "erros": []}

    def normalize(self, raw):
        if "proposicoes" in raw:
            return [f for p in raw["proposicoes"] for f in (
                _fato("proposicao", p["id"], "camara", sigla_tipo="PL"),
                *[_fato("autoria", f"{p['id']}:{d}:autor", "camara", proposicao_id=p["id"],
                        deputado_id=d, papel="autor") for d in p["deps"]])]
        deps = [("1", "Dep Um", "MG"), ("2", "Dep Dois", "MG"), ("3", "Dep Tres", "MG"),
                ("9", "Dep Nove", "SP")]
        fatos = [_fato("deputado", i, "camara", nome=n, uf=uf, partido="PL") for i, n, uf in deps]
        # a API repete o deputado: não pode virar ambiguidade nem duplicar
        fatos.append(_fato("deputado", "1", "camara", nome="Dep Um", uf="MG", partido="PT"))
        fatos.append(_fato("votacao", "v1", "camara", nominal=True))
        fatos += [_fato("voto", f"v1:{i}", "camara", votacao_id="v1", deputado_id=i, voto="Sim")
                  for i, _, _ in deps]
        return fatos


class FakeCeap(Source):
    nome = "ceap"
    despesas = None  # sobrescrito por teste

    def fetch(self, ano, max_linhas=None, max_deputados=None):
        CHAMADAS.append(("ceap", {"ano": ano}))
        return {"ano": ano}

    def normalize(self, raw):
        base = [("d1", "1", CNPJ_A, 100.0, "2024-03-01"), ("d2", "1", CNPJ_A, -30.0, None),
                ("d3", "2", CNPJ_B, 5.0, "2024-04-01"), ("d4", "9", CNPJ_A, 1000.0, "2024-05-01"),
                ("d5", "1", None, 7.0, "2024-06-01")]
        base = self.despesas if self.despesas is not None else base
        return [_fato("despesa_ceap", c, "camara_ceap", deputado_id=dep, valor=v, data=d,
                      **({"cnpj": cnpj} if cnpj else {})) for c, dep, cnpj, v, d in base]


class FakeCgu(Source):
    nome = "cgu"

    def fetch(self, cadastros=("ceis", "cnep", "emendas")):
        CHAMADAS.append(("cgu", {}))
        return {}

    def normalize(self, raw):
        return [_fato("sancao", "CEIS:1", "cgu_ceis", cnpj=CNPJ_A, cadastro="CEIS", fim=None),
                _fato("sancao", "CEIS:2", "cgu_ceis", cnpj="99999999000199", cadastro="CEIS"),
                _fato("emenda", "e1", "cgu_emendas", autor_nome="DEP UM", valor_empenhado=1.0),
                _fato("emenda", "e2", "cgu_emendas", autor_nome="DEP NOVE", valor_empenhado=1.0),
                _fato("emenda", "e3", "cgu_emendas", autor_nome="BANCADA X", valor_empenhado=1.0)]


def _cand(sq, urna, nome, cpf):
    return {"ANO_ELEICAO": "2022", "SQ_CANDIDATO": sq, "NR_CPF_CANDIDATO": cpf,
            "NM_CANDIDATO": nome, "NM_URNA_CANDIDATO": urna, "DS_CARGO": "DEPUTADO FEDERAL",
            "SG_UF": "MG", "SG_PARTIDO": "PL", "DS_SIT_TOT_TURNO": "ELEITO"}


def _receita(sq, sq_receita, valor):
    return {"AA_ELEICAO": "2022", "SQ_CANDIDATO": sq, "DS_CARGO": "Deputado Federal",
            "SQ_RECEITA": sq_receita, "NM_DOADOR": "MARIA", "NM_DOADOR_RFB": "MARIA SOUZA",
            "NR_CPF_CNPJ_DOADOR": "99999000001", "DS_ORIGEM_RECEITA": "Recursos de pessoas fisicas",
            "DT_RECEITA": "01/09/2022", "VR_RECEITA": valor}


def _voto(sq, cd, nome, qt):
    return {"ANO_ELEICAO": "2022", "SG_UF": "MG", "CD_MUNICIPIO": cd, "NM_MUNICIPIO": nome,
            "DS_CARGO": "Deputado Federal", "SQ_CANDIDATO": sq, "QT_VOTOS_NOMINAIS_VALIDOS": qt}


RAW_TSE = {
    "ano": 2022, "uf": "MG",
    "candidatos": [_cand("10", "Dep Um", "UM DA SILVA", "11111111111"),
                   _cand("11", "Dep Dois", "DOIS DA SILVA", "22222222222"),
                   _cand("12", "Dep Tres", "TRES DA SILVA", "33333333333"),
                   _cand("13", "Fulano Qualquer", "FULANO QUALQUER", "44444444444")],
    "receitas": [_receita("10", "r1", "100,00"), _receita("12", "r2", "200,00"),
                 _receita("13", "r3", "300,00")],
    "votacao": [_voto("10", "1", "BELO HORIZONTE", "50"), _voto("12", "1", "BELO HORIZONTE", "30"),
                _voto("13", "1", "BELO HORIZONTE", "20"), _voto("11", "2", "CONTAGEM", "10"),
                _voto("13", "2", "CONTAGEM", "90")],
    "municipios_ibge": [{"id": 3106200, "nome": "Belo Horizonte", "uf": "MG"},
                        {"id": 3118601, "nome": "Contagem", "uf": "MG"},
                        {"id": 3550308, "nome": "Sao Paulo", "uf": "SP"}],
}


class FakeTse(TseSource):
    def fetch(self, uf=None, ano=2022, conjuntos=("candidatos", "receitas", "votacao")):
        CHAMADAS.append(("tse", {"uf": uf, "ano": ano, "conjuntos": conjuntos}))
        return RAW_TSE


class FakeOpen(Source):
    nome = "opensanctions"

    def fetch(self, max_entidades=None):
        CHAMADAS.append(("opensanctions", {"max_entidades": max_entidades}))
        return {}

    def normalize(self, raw):
        return [_fato("pep", "p1", "os", nome="UM DA SILVA", cpf="***111111**", cpfs=[]),
                _fato("pep", "p2", "os", nome="OUTRO ALGUEM", cpf=None, cpfs=[])]


class FakeRfb(Source):
    nome = "rfb"

    def fetch(self, cnpjs):
        CHAMADAS.append(("rfb", {"cnpjs": list(cnpjs)}))
        return {"cnpjs": list(cnpjs)}

    def normalize(self, raw):
        return [f for c in raw["cnpjs"] for f in (
            _fato("empresa", c, "rfb", razao_social=f"EMPRESA {c}"),
            _fato("socio", f"{c}:FULANO", "rfb", cnpj=c, nome="FULANO"))]


FAKES = {"camara": FakeCamara, "ceap": FakeCeap, "cgu": FakeCgu, "tse": FakeTse,
         "opensanctions": FakeOpen, "rfb": FakeRfb}
TODAS = tuple(FAKES)


@pytest.fixture(autouse=True)
def _limpa_chamadas():
    CHAMADAS.clear()
    FakeCeap.despesas = None


def rodar(store=None, **kw):
    store = store or Store(":memory:")
    base = {"fontes": TODAS, "uf": "MG", "amostra": 2, "ano": 2024, "limite_rfb": 1}
    pipe = Pipeline(store, Opcoes(**{**base, **kw}), registry=dict(FAKES), log=lambda _: None)
    return store, pipe.executar()


def chaves(store, tipo):
    return {f.chave for f in store.facts_by_tipo(tipo)}


# ---------- kwargs por fonte (bug do Gate 1: fetch(max_votacoes=...) quebrava as novas fontes) ----------

def test_montar_kwargs_so_passa_o_que_a_assinatura_aceita():
    def fetch(ano, max_linhas=None):
        ...
    assert montar_kwargs(fetch, {"ano": 2024, "max_votacoes": 30, "uf": "MG"}) == {"ano": 2024}


def test_montar_kwargs_parametro_obrigatorio_ausente_e_erro_explicito():
    def fetch(cnpjs):
        ...
    with pytest.raises(ValueError, match="cnpjs"):
        montar_kwargs(fetch, {"ano": 2024})


def test_montar_kwargs_aceita_var_keyword():
    def fetch(**kw):
        ...
    assert montar_kwargs(fetch, {"a": 1}) == {"a": 1}


# o que cada passo do pipeline entrega ao fetch (mantido igual ao código do pipeline)
ENTREGA_AO_FETCH = {
    "camara": {"data_inicio": "2025-01-01", "data_fim": "2025-03-31", "max_votacoes": 30},
    "ceap": {"ano": 2024},
    "cgu": {},
    "tse": {"uf": "MG", "ano": 2022, "conjuntos": ("candidatos", "receitas", "votacao")},
    "opensanctions": {"max_entidades": None},
    "rfb": {"cnpjs": [CNPJ_A]},
}


@pytest.mark.parametrize("nome", sorted(REGISTRY))
def test_assinatura_do_fetch_das_fontes_reais_e_atendida(nome):
    src = REGISTRY[nome]()
    kwargs = montar_kwargs(src.fetch, ENTREGA_AO_FETCH[nome])
    inspect.signature(src.fetch).bind(**kwargs)  # levanta TypeError se não encaixa


def test_fetch_de_cada_fonte_falsa_so_recebe_os_proprios_argumentos():
    rodar()
    vistos = dict(CHAMADAS)
    assert vistos["ceap"] == {"ano": 2024}
    assert vistos["camara"]["max_votacoes"] == 30
    assert vistos["camara"]["detalhar_deputados"] is False  # opt-in: padrão não detalha
    assert vistos["tse"]["uf"] == "MG" and vistos["opensanctions"] == {"max_entidades": None}
    assert vistos["rfb"]["cnpjs"] == [CNPJ_A]  # limite_rfb=1: o de maior valor


def test_chamar_fetch_funciona_com_fonte_sem_parametros_extras():
    class S:
        def fetch(self):
            return {"ok": 1}
    assert chamar_fetch(S(), ano=2024, uf="MG") == {"ok": 1}


# ---------- escopo ----------

def test_selecionar_escopo_uf_amostra_e_sem_restricao():
    deps = [dep("10", "A", "MG"), dep("9", "B", "MG"), dep("100", "C", "MG"), dep("5", "D", "SP"),
            dep("9", "B", "MG", partido="PT")]
    assert selecionar_escopo(deps, "MG", 2) == {"9", "10"}  # ordem numérica, não textual
    assert selecionar_escopo(deps, "SP", None) == {"5"}
    assert selecionar_escopo(deps, None, 1) == {"5"}
    assert selecionar_escopo(deps, None, None) is None


# ---------- pipeline completo ----------

def test_pipeline_grava_so_o_escopo_e_resolve_entidades():
    store, rel = rodar()
    assert chaves(store, "deputado") == {"1", "2"}
    assert chaves(store, "voto") == {"v1:1", "v1:2"} and chaves(store, "votacao") == {"v1"}
    assert chaves(store, "despesa_ceap") == {"d1", "d2", "d3", "d5"}  # d4 é do deputado 9
    assert chaves(store, "sancao") == {"CEIS:1"}  # só CNPJ pago pelo escopo
    assert chaves(store, "emenda") == {"e1"}
    emenda = store.facts_by_tipo("emenda")[0]
    assert emenda.atributos["deputado_id"] == "1" and emenda.atributos["deputado_cf"] == 0.8
    assert rel["cgu"]["emendas"] == {"total": 3, "ligados": 2, "ambiguos": 0, "sem_match": 1}
    # TSE: candidatura ligada ao escopo; doação e votos só dos ligados
    cands = {f.chave: f for f in store.facts_by_tipo("candidatura")}
    assert set(cands) == {"10", "11"} and cands["10"].atributos["deputado_id"] == "1"
    assert cands["10"].atributos["deputado_cf"] == 0.8
    assert chaves(store, "doacao") == {"r1"}
    votos = {f.chave: f for f in store.facts_by_tipo("votos_municipio")}
    assert set(votos) == {"2022:10:3106200", "2022:11:3118601"}
    assert votos["2022:10:3106200"].atributos["votos"] == 50
    assert votos["2022:10:3106200"].atributos["votos_validos_municipio"] == 100  # inclui quem saiu
    assert rel["tse"]["candidaturas"]["total"] == 4
    # PEP só o ligado (nome civil da candidatura + CPF mascarado compatível)
    assert chaves(store, "pep") == {"p1"}
    # RFB só o CNPJ de maior valor; links por CNPJ
    assert chaves(store, "empresa") == {CNPJ_A}
    destinos = {(lk.origem, lk.destino) for lk in store.load_links(origem_tipo="despesa_ceap")}
    assert destinos == {("despesa_ceap:d1", f"empresa:{CNPJ_A}"),
                        ("despesa_ceap:d1", "sancao:CEIS:1"),
                        ("despesa_ceap:d2", f"empresa:{CNPJ_A}"),
                        ("despesa_ceap:d2", "sancao:CEIS:1")}
    assert {lk.destino for lk in store.load_links(origem_tipo="pep")} == {"deputado:1"}


def test_valor_negativo_e_data_none_chegam_ao_banco_pelo_pipeline():
    store, _ = rodar()
    d2 = next(f for f in store.facts_by_tipo("despesa_ceap") if f.chave == "d2")
    assert d2.atributos["valor"] == -30.0 and d2.atributos["data"] is None


def test_pipeline_e_idempotente():
    store, _ = rodar()
    antes = ({(f.tipo, f.chave) for f in store.load_facts()}, store.load_links(),
             store.load_ambiguities())
    rodar(store)
    depois = ({(f.tipo, f.chave) for f in store.load_facts()}, store.load_links(),
              store.load_ambiguities())
    assert antes == depois


def test_recarga_remove_despesa_que_sumiu_do_ano_mas_preserva_outro_ano():
    store = Store(":memory:")
    store.upsert_facts([_fato("despesa_ceap", "velha23", "camara_ceap", deputado_id="1",
                              valor=1.0, data="2023-05-05")])
    rodar(store, fontes=("camara", "ceap"))
    assert "d1" in chaves(store, "despesa_ceap")
    FakeCeap.despesas = [("d1", "1", CNPJ_A, 100.0, "2024-03-01")]  # d2, d3, d5 deixaram de existir
    rodar(store, fontes=("camara", "ceap"))
    assert chaves(store, "despesa_ceap") == {"d1", "velha23"}


def test_rfb_nao_reconsulta_cnpj_ja_conhecido():
    store, _ = rodar()
    CHAMADAS.clear()
    rodar(store, fontes=("rfb",), limite_rfb=5)
    assert dict(CHAMADAS)["rfb"]["cnpjs"] == [CNPJ_B]  # CNPJ_A já tem empresa


def test_relatorio_e_log_mostram_cnpj_sem_dados_da_receita():
    class FakeRfbFora(FakeRfb):
        def fetch(self, cnpjs):
            return {"cnpjs": [], "indisponiveis": list(cnpjs)}

    linhas: list[str] = []
    op = Opcoes(fontes=TODAS, uf="MG", amostra=2, ano=2024, limite_rfb=1)
    rel = Pipeline(Store(":memory:"), op, registry={**FAKES, "rfb": FakeRfbFora},
                   log=linhas.append).executar()
    assert rel["rfb"]["indisponiveis"] == [CNPJ_A] and rel["rfb"]["empresas"] == 0
    assert any("ATENÇÃO" in linha and CNPJ_A in linha for linha in linhas)


def test_passo_sem_camara_usa_os_deputados_ja_gravados():
    store, _ = rodar(fontes=("camara",))
    CHAMADAS.clear()
    rodar(store, fontes=("ceap",))
    assert chaves(store, "despesa_ceap") == {"d1", "d2", "d3", "d5"}


def test_ceap_sem_ano_e_fonte_desconhecida_falham_cedo():
    with pytest.raises(ValueError, match="--ano"):
        rodar(ano=None)
    with pytest.raises(ValueError, match="desconhecida"):
        rodar(fontes=("camara", "xyz"))


def test_sem_escopo_grava_todos_os_deputados_e_despesas():
    store, _ = rodar(uf=None, amostra=None, fontes=("camara", "ceap"))
    assert chaves(store, "deputado") == {"1", "2", "3", "9"}
    assert "d4" in chaves(store, "despesa_ceap")


def test_ambiguidade_fica_registrada_e_nao_vira_link():
    class TseAmbiguo(FakeTse):
        def fetch(self, uf=None, ano=2022, conjuntos=()):
            raw = dict(RAW_TSE)
            raw["candidatos"] = [_cand("10", "Dep Um", "UM", "11111111111"),
                                 _cand("20", "Dep Um", "UM", "55555555555")]
            return raw
    store = Store(":memory:")
    pipe = Pipeline(store, Opcoes(fontes=("camara", "tse"), uf="MG", amostra=2),
                    registry={**FAKES, "tse": TseAmbiguo}, log=lambda _: None)
    rel = pipe.executar()
    assert store.load_links(origem_tipo="candidatura") == []
    assert {a.origem for a in store.load_ambiguities()} == {"candidatura:10", "candidatura:20"}
    assert rel["tse"]["candidaturas"]["ambiguos"] == 2


# ---------- --detalhar-deputados (cpf/nome_civil do /deputados/{id}) ----------

def chamadas_camara():
    return [kw for nome, kw in CHAMADAS if nome == "camara"]


def test_detalhar_com_amostra_passa_so_os_ids_do_escopo_ao_fetch():
    rodar(fontes=("camara",), detalhar_deputados=True)
    assert chamadas_camara()[-1]["detalhar_deputados"] == ["1", "2"]


def test_detalhar_sem_escopo_pede_todos():
    rodar(fontes=("camara",), uf=None, amostra=None, detalhar_deputados=True)
    assert chamadas_camara() == [{**chamadas_camara()[0], "detalhar_deputados": True}]


def test_detalhar_em_fonte_sem_o_parametro_falha_em_vez_de_ignorar():
    class Antiga(FakeCamara):
        def fetch(self, data_inicio="x", data_fim="y", max_votacoes=None):
            return {}
    with pytest.raises(ValueError, match="detalhar"):
        Pipeline(Store(":memory:"), Opcoes(fontes=("camara",), detalhar_deputados=True),
                 registry={**FAKES, "camara": Antiga}, log=lambda _: None).executar()


def test_cache_ja_detalhado_do_escopo_dispensa_nova_coleta(tmp_path, monkeypatch):
    import sources.base
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    cache = tmp_path / "camara" / "camara_2025-01-01_2025-03-31.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"deputados": [{"id": 1, "_detalhe": {}}, {"id": 2, "_detalhe": {}}],
                                 "votacoes": []}))
    rodar(fontes=("camara",), detalhar_deputados=True, reusar_raw=True)
    assert chamadas_camara() == []


def test_cache_sem_detalhe_e_refeito_pedindo_detalhe_so_do_escopo(tmp_path, monkeypatch):
    import sources.base
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    cache = tmp_path / "camara" / "camara_2025-01-01_2025-03-31.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"deputados": [{"id": 1}, {"id": 2}], "votacoes": []}))
    rodar(fontes=("camara",), detalhar_deputados=True, reusar_raw=True)
    assert [c["detalhar_deputados"] for c in chamadas_camara()] == [["1", "2"]]


def test_deputado_com_cpf_liga_candidatura_por_cpf_cf_1_mesmo_com_nome_diferente():
    class CamaraComCpf(FakeCamara):
        def normalize(self, raw):
            return [_fato("deputado", "1", "camara", nome="Nome Que Nao Bate", uf="MG",
                          partido="PL", cpf="11111111111", nome_civil="UM DA SILVA")]
    store = Store(":memory:")
    Pipeline(store, Opcoes(fontes=("camara", "tse"), uf="MG", amostra=1),
             registry={**FAKES, "camara": CamaraComCpf}, log=lambda _: None).executar()
    assert [(lk.origem, lk.destino, lk.metodo, lk.cf)
            for lk in store.load_links(origem_tipo="candidatura")] == [
        ("candidatura:10", "deputado:1", "cpf", 1.0)]


# ---------- --incluir-proposicoes (autoria para a R05) ----------

def chamadas_prop():
    return [kw for nome, kw in CHAMADAS if nome == "camara_prop"]


def test_proposicoes_pedem_so_os_ids_do_escopo_e_os_tipos_configurados():
    rodar(fontes=("camara",), incluir_proposicoes=True, max_proposicoes=50)
    (c,) = chamadas_prop()
    assert c["deputado_ids"] == ["1", "2"] and c["max_proposicoes"] == 50
    assert list(c["siglas_tipo"]) == ["PL", "PEC", "PLP"]


def test_proposicoes_sem_escopo_pedem_a_janela_toda():
    rodar(fontes=("camara",), uf=None, amostra=None, incluir_proposicoes=True)
    assert chamadas_prop()[0]["deputado_ids"] is None


def test_proposicoes_gravam_so_autoria_do_escopo_e_proposicao_com_autor_do_escopo():
    store, rel = rodar(fontes=("camara",), incluir_proposicoes=True)
    assert chaves(store, "autoria") == {"p1:1:autor", "p3:2:autor"}  # dep 3 está fora do escopo
    assert chaves(store, "proposicao") == {"p1", "p3"}  # p2 só tem autor fora do escopo
    assert rel["camara"]["autorias"] == 2


def test_proposicoes_recarga_remove_autoria_que_sumiu_e_e_idempotente():
    store, _ = rodar(fontes=("camara",), incluir_proposicoes=True)
    store.upsert_facts([_fato("autoria", "velha:1:autor", "camara", proposicao_id="velha",
                              deputado_id="1", papel="autor")])
    antes = {(f.tipo, f.chave) for f in store.load_facts()}
    rodar(store, fontes=("camara",), incluir_proposicoes=True)
    depois = {(f.tipo, f.chave) for f in store.load_facts()}
    assert ("autoria", "velha:1:autor") in antes and ("autoria", "velha:1:autor") not in depois
    assert depois == antes - {("autoria", "velha:1:autor")}


def test_proposicoes_em_fonte_sem_fetch_proposicoes_falha_claramente():
    class Antiga(FakeCamara):
        fetch_proposicoes = None
    with pytest.raises(ValueError, match="proposi"):
        Pipeline(Store(":memory:"), Opcoes(fontes=("camara",), incluir_proposicoes=True),
                 registry={**FAKES, "camara": Antiga}, log=lambda _: None).executar()


# ---------- --pseudonimizar (HMAC do CPF de terceiros) e varredura ----------

def cpf_ok(base9: str) -> str:
    """CPF com dígitos verificadores válidos a partir de 9 dígitos."""
    n = [int(c) for c in base9]
    for _ in range(2):
        n.append((sum(d * p for d, p in zip(n, range(len(n) + 1, 1, -1), strict=True)) * 10 % 11)
                 % 10)
    return "".join(map(str, n))


CPF_A, CPF_B = cpf_ok("123456789"), cpf_ok("987654321")
SAL = "sal-de-teste"


def test_salt_ausente_ou_vazio_da_erro_claro_citando_a_variavel():
    with pytest.raises(ValueError, match="RAIO_X_ID_SALT"):
        salt_do_ambiente({})
    with pytest.raises(ValueError, match="RAIO_X_ID_SALT"):
        salt_do_ambiente({"RAIO_X_ID_SALT": "  "})
    assert salt_do_ambiente({"RAIO_X_ID_SALT": "abc"}) == "abc"


def test_doador_pf_vira_hash_estavel_com_digitos_visiveis_e_pj_fica():
    fatos = [F("doacao", "r1", tipo_doador="PF", doador_cpf_cnpj=CPF_A, doador_nome="MARIA"),
             F("doacao", "r2", tipo_doador="PF", doador_cpf_cnpj=CPF_A, doador_nome="MARIA"),
             F("doacao", "r3", tipo_doador="PF", doador_cpf_cnpj=CPF_B),
             F("doacao", "r4", tipo_doador="PJ", doador_cpf_cnpj="00000000000191"),
             F("doacao", "r5", tipo_doador="PF", doador_cpf_cnpj=None)]
    r = por_chave(pseudonimizar_fatos(fatos, SAL))
    a1, a2, b = r["r1"].atributos, r["r2"].atributos, r["r3"].atributos
    assert a1["doador_cpf_cnpj"] == a2["doador_cpf_cnpj"] != b["doador_cpf_cnpj"]
    assert CPF_A not in json.dumps(a1) and a1["doador_cpf_cnpj"].startswith("hmac:")
    assert a1["doador_cpf_visivel"] == CPF_A[3:9]  # posições 4–9: o que o mascarado mostra
    assert r["r4"].atributos["doador_cpf_cnpj"] == "00000000000191"
    assert "doador_cpf_visivel" not in r["r4"].atributos
    assert r["r5"].atributos["doador_cpf_cnpj"] is None


def test_hash_depende_do_sal():
    f = [F("doacao", "r1", tipo_doador="PF", doador_cpf_cnpj=CPF_A)]
    h1 = pseudonimizar_fatos(f, "um")[0].atributos["doador_cpf_cnpj"]
    h2 = pseudonimizar_fatos(f, "dois")[0].atributos["doador_cpf_cnpj"]
    assert h1 != h2


def test_cpf_formatado_e_o_mesmo_cpf_sem_formatacao_dao_o_mesmo_hash():
    formatado = f"{CPF_A[:3]}.{CPF_A[3:6]}.{CPF_A[6:9]}-{CPF_A[9:]}"
    r = pseudonimizar_fatos([F("despesa_ceap", "d1", cpf=formatado),
                             F("despesa_ceap", "d2", cpf=CPF_A)], SAL)
    assert r[0].atributos["cpf"] == r[1].atributos["cpf"] and formatado not in str(r[0].atributos)


def test_socio_pep_sancao_e_despesa_cpf_integro_viram_hash_mas_mascarado_e_cnpj_ficam():
    fatos = [F("socio", "s1", cnpj="1", cpf_cnpj=CPF_A), F("socio", "s2", cnpj="1",
                                                           cpf_cnpj="***101202**"),
             F("socio", "s3", cnpj="1", cpf_cnpj="00000000000191"),
             F("sancao", "x1", cnpj=None, cpf=CPF_A), F("sancao", "x2", cnpj="1", cpf=None),
             F("pep", "p1", cpf="***111111**", cpfs=["***111111**", CPF_B]),
             F("despesa_ceap", "d1", cpf=CPF_B)]
    r = por_chave(pseudonimizar_fatos(fatos, SAL))
    assert r["s1"].atributos["cpf_cnpj"].startswith("hmac:")
    assert r["s2"].atributos["cpf_cnpj"] == "***101202**"
    assert r["s3"].atributos["cpf_cnpj"] == "00000000000191"
    assert r["x1"].atributos["cpf"].startswith("hmac:") and r["x2"].atributos["cpf"] is None
    assert r["p1"].atributos["cpf"] == "***111111**"
    assert r["p1"].atributos["cpfs"][0] == "***111111**"
    assert r["p1"].atributos["cpfs"][1].startswith("hmac:")
    assert r["d1"].atributos["cpf"].startswith("hmac:")


def test_cpf_dentro_de_texto_livre_tambem_e_trocado_pelo_mesmo_hash():
    # a Câmara grava o CPF do fornecedor PF colado no nome ("NOME 12345678901")
    r = pseudonimizar_fatos([
        F("despesa_ceap", "d1", cpf=CPF_A, fornecedor=f"ANNA GOMES {CPF_A}"),
        F("despesa_ceap", "d2", fornecedor="LOJA 12345678900 LTDA", obs=[f"cpf {CPF_B}."]),
        F("pep", "p1", ocupacoes=[{"nota": f"{CPF_B[:3]}.{CPF_B[3:6]}.{CPF_B[6:9]}-{CPF_B[9:]}"}])],
        SAL)
    d1, d2, p1 = (x.atributos for x in r)
    assert d1["fornecedor"] == f"ANNA GOMES {d1['cpf']}" and CPF_A not in str(d1)
    assert d2["fornecedor"] == "LOJA 12345678900 LTDA"  # 11 dígitos sem DV válido: não é CPF
    assert CPF_B not in str(d2) and CPF_B not in str(p1)
    assert d2["obs"][0].startswith("cpf hmac:") and d2["obs"][0].endswith(".")


def test_cpf_de_deputado_e_candidato_continua_integro_e_a_entrada_nao_muda():
    fatos = [dep("1", "A", cpf=CPF_A), cand("10", "A", cpf=CPF_A)]
    r = pseudonimizar_fatos(fatos, SAL)
    assert [f.atributos["cpf"] for f in r] == [CPF_A, CPF_A]
    d = F("doacao", "r1", tipo_doador="PF", doador_cpf_cnpj=CPF_A)
    pseudonimizar_fatos([d], SAL)
    assert d.atributos["doador_cpf_cnpj"] == CPF_A


def test_varredura_acha_cpf_integro_de_terceiro_formatado_ou_nao_e_nunca_devolve_o_valor():
    formatado = f"{CPF_B[:3]}.{CPF_B[3:6]}.{CPF_B[6:9]}-{CPF_B[9:]}"
    fatos = [F("doacao", "r1", doador_cpf_cnpj=CPF_A), F("despesa_ceap", "d1", cpf=formatado),
             F("socio", "s1", obs={"nota": f"cpf {CPF_A} aqui"}),
             dep("1", "A", cpf=CPF_A), cand("10", "A", cpf=CPF_B),  # cadastral público: permitido
             F("socio", "s2", cpf_cnpj="***101202**"),
             F("empresa", "00000000000191"),  # CNPJ de 14 dígitos não é CPF
             F("emenda", "e1", codigo="12345678901")]  # 11 dígitos, dígito verificador inválido
    achados = cpfs_integros(fatos)
    assert sorted((a.tipo, a.chave) for a in achados) == [
        ("despesa_ceap", "d1"), ("doacao", "r1"), ("socio", "s1")]
    assert CPF_A not in str(achados) and CPF_B not in str(achados)


def test_varredura_olha_chave_url_e_id_oficial_tambem():
    f = Fact(tipo="pep", chave=f"x:{CPF_A}", atributos={}, fonte="t", id_oficial="1",
             url=f"https://e/{CPF_B}")
    assert [a.campo for a in cpfs_integros([f])] == ["chave", "url"]


def test_pseudonimizar_nao_quebra_r06b_e_hash_igual_preserva_igualdade():
    from engine.factbase import FactBase
    from engine.predicates.circuito import circuito_doador_socio
    fatos = [dep("1", "Dep"), cand("10", "Dep", deputado_id="1", deputado_cf=1.0),
             F("doacao", "r1", sq_candidato="10", tipo_doador="PF", doador_nome="MARIA SOUZA",
               doador_cpf_cnpj=cpf_ok("123456789"), valor=100.0),
             F("despesa_ceap", "d1", deputado_id="1", cnpj="00000000000191", valor=50.0),
             F("socio", "s1", cnpj="00000000000191", nome="Maria Souza",
               cpf_cnpj="***" + cpf_ok("123456789")[3:9] + "**")]
    for modo in ("indicio",):
        antes = circuito_doador_socio(FactBase(fatos), {"modo": modo})
        depois = circuito_doador_socio(FactBase(pseudonimizar_fatos(fatos, SAL)), {"modo": modo})
        assert len(antes) == len(depois) == 1
        assert depois[0].valores["n_circuitos"] == antes[0].valores["n_circuitos"]
    # dígitos visíveis incompatíveis continuam descartando o caso, mesmo pseudonimizado
    outro = [*fatos[:-1], F("socio", "s1", cnpj="00000000000191", nome="Maria Souza",
                            cpf_cnpj="***000000**")]
    assert circuito_doador_socio(FactBase(pseudonimizar_fatos(outro, SAL)), {"modo": "indicio"}) == []


def test_pipeline_com_pseudonimizar_nao_deixa_cpf_integro_de_terceiro(monkeypatch):
    monkeypatch.setenv("RAIO_X_ID_SALT", SAL)

    class CeapCpf(FakeCeap):
        def normalize(self, raw):
            return [*super().normalize(raw), _fato("despesa_ceap", "dpf", "camara_ceap",
                                                   deputado_id="1", cpf=CPF_A, valor=1.0,
                                                   data="2024-01-01")]

    class TseCpf(FakeTse):
        def fetch(self, uf=None, ano=2022, conjuntos=()):
            raw = dict(RAW_TSE)
            raw["receitas"] = [{**_receita("10", "r1", "100,00"), "NR_CPF_CNPJ_DOADOR": CPF_B}]
            return raw

    reg = {**FAKES, "ceap": CeapCpf, "tse": TseCpf}
    cru, limpo = Store(":memory:"), Store(":memory:")
    base = {"fontes": TODAS, "uf": "MG", "amostra": 2, "ano": 2024, "limite_rfb": 1}
    Pipeline(cru, Opcoes(**base), registry=dict(reg), log=lambda _: None).executar()
    Pipeline(limpo, Opcoes(**base, pseudonimizar=True), registry=dict(reg),
             log=lambda _: None).executar()
    assert {(a.tipo, a.chave) for a in cpfs_integros(cru.load_facts())} == {
        ("despesa_ceap", "dpf"), ("doacao", "r1")}
    assert cpfs_integros(limpo.load_facts()) == []
    doacao = limpo.facts_by_tipo("doacao")[0].atributos
    assert doacao["doador_cpf_visivel"] == CPF_B[3:9]


def test_pipeline_com_pseudonimizar_sem_salt_falha_antes_de_coletar(monkeypatch):
    monkeypatch.delenv("RAIO_X_ID_SALT", raising=False)
    with pytest.raises(ValueError, match="RAIO_X_ID_SALT"):
        rodar(pseudonimizar=True)
    assert CHAMADAS == []


# ---------- revisão: ponto único de pseudonimização, links/ambiguidades, cpf_visivel, deploy-check ----------

def test_todo_fato_gravado_com_pseudonimizar_passa_pelo_ponto_unico(monkeypatch):
    """Antes só alguns passos pseudonimizavam; um fato qualquer (aqui, a descrição de uma
    votação da Câmara) com CPF em texto saía íntegro."""
    monkeypatch.setenv("RAIO_X_ID_SALT", SAL)

    class CamaraComCpfNoTexto(FakeCamara):
        def normalize(self, raw):
            return [*super().normalize(raw), _fato("votacao", "v2", "camara", nominal=False,
                                                   descricao=f"parecer do relator {CPF_A}"),
                    _fato("deputado", "5", "camara", nome="Dep Cinco", uf="MG", partido="PL",
                          cpf=CPF_B)]
    store = Store(":memory:")
    Pipeline(store, Opcoes(fontes=("camara",), uf=None, amostra=None, pseudonimizar=True),
             registry={**FAKES, "camara": CamaraComCpfNoTexto}, log=lambda _: None).executar()
    assert cpfs_integros(store.load_facts()) == []
    assert "hmac:" in store.facts_by_tipo("votacao")[1].atributos["descricao"]
    cinco = next(f for f in store.facts_by_tipo("deputado") if f.chave == "5")
    assert cinco.atributos["cpf"] == CPF_B  # deputado: dado cadastral público


def test_socio_com_cpf_integro_ganha_cpf_visivel_igual_ao_do_doador():
    (s,) = pseudonimizar_fatos([F("socio", "s1", cnpj="1", cpf_cnpj=CPF_A)], SAL)
    assert s.atributos["cpf_visivel"] == CPF_A[3:9]
    (m,) = pseudonimizar_fatos([F("socio", "s2", cnpj="1", cpf_cnpj="***101202**")], SAL)
    assert "cpf_visivel" not in m.atributos  # mascarado já mostra os dígitos


def test_varredura_cobre_entity_link_e_entity_ambiguity():
    store = Store(":memory:")
    store.upsert_links([EntityLink(f"candidatura:{CPF_A}", "deputado:1", "cpf", 1.0),
                        EntityLink("candidatura:2", "deputado:1", "cpf", 1.0)])
    from repo.links import Ambiguidade
    store.save_ambiguities([Ambiguidade("pep:9", (f"deputado:{CPF_B}", "deputado:2"), "x")])
    achados = {(a.tipo, a.campo) for a in varrer_banco(store)}
    assert achados == {("entity_link", "origem"), ("entity_ambiguity", "candidatos")}


def _base_publica(caminho, com_cpf=False):
    st = Store(caminho)
    st.upsert_facts([F("doacao", "r1", doador_cpf_cnpj=CPF_A if com_cpf else "hmac:abc")])
    st.con.close()


def test_deploy_check_aceita_so_a_base_publica_limpa(tmp_path):
    pub = tmp_path / "data" / "sample" / "raio_x_publico.duckdb"
    _base_publica(pub)
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.duckdb").write_text("ignorado")
    assert verificar_envio(tmp_path, pub) == []


def test_deploy_check_reprova_outro_duckdb_e_o_wal(tmp_path):
    pub = tmp_path / "data" / "sample" / "raio_x_publico.duckdb"
    _base_publica(pub)
    (tmp_path / "data" / "raio_x.duckdb").write_text("x")
    (tmp_path / "data" / "sample" / "raio_x_sample.duckdb.wal").write_text("x")
    erros = verificar_envio(tmp_path, pub)
    assert len(erros) == 2 and all("duckdb" in e for e in erros)


def test_deploy_check_reprova_base_publica_com_cpf_ou_ausente(tmp_path):
    pub = tmp_path / "data" / "sample" / "raio_x_publico.duckdb"
    assert "não existe" in verificar_envio(tmp_path, pub)[0]
    _base_publica(pub, com_cpf=True)
    erros = verificar_envio(tmp_path, pub)
    assert len(erros) == 1 and "CPF" in erros[0] and CPF_A not in erros[0]


def test_hash_com_sequencia_de_11_digitos_nao_e_falso_positivo_nem_e_re_hasheado():
    # 32 hex podem, por acaso, conter 11 dígitos seguidos com dígito verificador válido
    token = "hmac:a" + CPF_A + "b" + "0" * 19
    assert len(token) == len("hmac:") + 32
    f = F("doacao", "r1", doador_cpf_cnpj=token, obs=f"x {token} y")
    assert cpfs_integros([f]) == []
    (g,) = pseudonimizar_fatos([f], SAL)
    assert g.atributos["doador_cpf_cnpj"] == token and g.atributos["obs"] == f"x {token} y"
    (h,) = pseudonimizar_fatos([F("despesa_ceap", "d", fornecedor=f"{token} {CPF_B}")], SAL)
    assert h.atributos["fornecedor"].startswith(token + " hmac:") and CPF_B not in str(h.atributos)
