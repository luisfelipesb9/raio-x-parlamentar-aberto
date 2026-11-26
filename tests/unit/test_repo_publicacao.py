"""repo.store: tabelas materializadas da publicação enxuta (ADR-011) e cópia sem chave primária."""
from __future__ import annotations

import duckdb
import pytest

from contracts import Evidence, Fact, Finding, GraphEdge, GraphNode, Nivel
from repo.links import EntityLink
from repo.store import TABELAS_PUBLICACAO, Store


def F(tipo, chave, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def finding(fid, dep, regra, cf, evidencias=()):
    return Finding(id=fid, deputado_id=dep, regra=regra, categoria="gastos", conclusao="texto",
                   cf=cf, nivel=Nivel.from_cf(cf), evidencias=list(evidencias),
                   guardrails_aplicados=["R02"], valores={"n": 3, "lista": ["a", "b"]})


NOS = [GraphNode(id="deputado:1", tipo="deputado", rotulo="Ana Çá", atributos={"uf": "MG", "n": 2}),
       GraphNode(id="empresa:1", tipo="empresa", rotulo="Posto", atributos={
           "sancoes": [{"cadastro": "CEIS", "vigente": True}], "findings": ["R03:1"]})]
ARESTAS = [GraphEdge(origem="empresa:1", destino="deputado:1", relacao="recebeu", peso=1234.5, cf=0.4,
                     evidencia_ids=["despesa_ceap:9", "despesa_ceap:10"]),
           GraphEdge(origem="deputado:1", destino="deputado:2", relacao="votou_com", peso=0.8)]


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    yield s
    s.con.close()


# ---------- grafo ----------
def test_grafo_grava_e_le_iguais_e_na_ordem_da_projecao(store):
    store.save_graph(NOS, ARESTAS)
    nos, arestas = store.load_graph()
    assert nos == NOS and arestas == ARESTAS


def test_grafo_vazio_le_listas_vazias(store):
    assert store.load_graph() == ([], [])


def test_grafo_regravado_substitui_o_anterior(store):
    store.save_graph(NOS, ARESTAS)
    store.save_graph(NOS[:1], [])
    assert store.load_graph() == (NOS[:1], [])


def test_grafo_preserva_ordem_de_relacao_origem_destino_mesmo_gravado_fora_de_ordem(store):
    store.save_graph(list(reversed(NOS)), list(reversed(ARESTAS)))
    nos, arestas = store.load_graph()
    assert [n.id for n in nos] == ["deputado:1", "empresa:1"]
    assert [(e.relacao, e.origem) for e in arestas] == [("recebeu", "empresa:1"),
                                                         ("votou_com", "deputado:1")]


# ---------- inferência ----------
def test_inferencia_devolve_so_os_findings_do_deputado_sem_evidencias(store):
    ev = [Evidence(tipo="votacao", id_oficial="v1", url="https://x")]
    a, b, c = (finding("R01:1", "1", "R01", 0.9, ev), finding("R04:1", "1", "R04", 0.5, ev),
               finding("R01:2", "2", "R01", 0.3, ev))
    assert store.save_inferencia([a, b, c]) == 3
    achados = store.inferencia_de("1")
    assert [f.id for f in achados] == ["R01:1", "R04:1"]
    assert achados[0] == a.model_copy(update={"evidencias": []})
    assert store.inferencia_de("999") == []


def test_inferencia_regravada_substitui(store):
    store.save_inferencia([finding("R01:1", "1", "R01", 0.9)])
    store.save_inferencia([finding("R01:2", "2", "R01", 0.9)])
    assert store.inferencia_de("1") == [] and len(store.inferencia_de("2")) == 1


# ---------- metadados ----------
def test_meta_grava_e_le_tipos_json(store):
    meta = {"contract_version": "0.2.0", "contagem_por_tipo": {"voto": 3},
            "cobertura_fontes": [{"fonte": "camara", "tipos": ["voto"], "n_fatos": 3}],
            "janela_votos": {"inicio": "2025-02-01", "fim": None}}
    store.save_publicacao_meta(meta)
    assert store.load_publicacao_meta() == meta


def test_publicado_exige_meta_com_gerado_em(store):
    assert not store.publicado()  # tabelas existem, mas vazias (banco de trabalho)
    store.save_publicacao_meta({"outra": 1})
    assert not store.publicado()
    store.save_publicacao_meta({"gerado_em": "2026-11-26T12:00:00+00:00"})
    assert store.publicado()


def test_publicado_e_falso_em_banco_antigo_sem_as_tabelas(tmp_path):
    antigo = tmp_path / "antigo.duckdb"
    con = duckdb.connect(str(antigo))
    con.execute("CREATE TABLE fact (tipo TEXT, chave TEXT)")
    con.close()
    s = Store(antigo, read_only=True)
    assert not s.publicado()
    assert s.tabelas_publicacao_faltando() == list(TABELAS_PUBLICACAO)
    s.con.close()


# ---------- cópia enxuta, sem chave primária ----------
@pytest.fixture
def origem(tmp_path):
    caminho = tmp_path / "origem.duckdb"
    s = Store(caminho)
    s.upsert_facts([
        F("deputado", "1", nome="Ana"), F("votacao", "v1"), F("voto", "v1:1"),
        F("despesa_ceap", "d1"), F("despesa_ceap", "d2"), F("despesa_ceap", "d3"),
        F("emenda", "e1"), F("emenda", "e2"),
    ])
    ev = [Evidence(tipo="despesa_ceap", id_oficial="d1"), Evidence(tipo="emenda", id_oficial="e2"),
          Evidence(tipo="votacao", id_oficial="v1")]
    s.save_findings([finding("R04:1", "1", "R04", 0.8, ev)],
                    {"R04:1": _explicacao()})
    s.upsert_links([EntityLink("despesa_ceap:d1", "deputado:1", "cpf", 1.0),
                    EntityLink("despesa_ceap:d2", "deputado:1", "cpf", 1.0),  # d2 não é mantida
                    EntityLink("emenda:e2", "deputado:1", "nome_norm", 0.8)])
    s.con.close()
    return caminho


def _explicacao():
    from contracts import Explanation
    return Explanation(finding_id="R04:1", como=[], por_que="x")


def test_copia_so_integrais_e_citados_como_evidencia(tmp_path, origem):
    pub = Store.novo_publico(tmp_path / "pub.duckdb")
    por_tipo = pub.copiar_enxuto(origem, tipos_integrais=("deputado", "votacao", "voto"))
    assert por_tipo == {"deputado": 1, "votacao": 1, "voto": 1, "despesa_ceap": 1, "emenda": 1}
    assert sorted(f.chave for f in pub.load_facts()) == ["1", "d1", "e2", "v1", "v1:1"]
    assert [r[0] for r in pub.con.execute("SELECT id FROM finding").fetchall()] == ["R04:1"]
    assert pub.con.execute("SELECT explanation FROM finding").fetchone()[0]
    pub.con.close()


def test_copia_so_links_com_as_duas_pontas_mantidas(tmp_path, origem):
    pub = Store.novo_publico(tmp_path / "pub.duckdb")
    pub.copiar_enxuto(origem, tipos_integrais=("deputado",))
    assert [(lk.origem, lk.destino) for lk in pub.load_links()] == [
        ("despesa_ceap:d1", "deputado:1"), ("emenda:e2", "deputado:1")]
    pub.con.close()


def test_arquivo_publico_nao_tem_chave_primaria_nem_indice(tmp_path, origem):
    destino = tmp_path / "pub.duckdb"
    pub = Store.novo_publico(destino)
    pub.copiar_enxuto(origem, tipos_integrais=("deputado",))
    pub.checkpoint()
    pub.con.close()
    con = duckdb.connect(str(destino), read_only=True)
    assert con.execute("SELECT count(*) FROM duckdb_constraints()").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM duckdb_indexes()").fetchone()[0] == 0
    tabelas = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
    assert {"fact", "finding", "entity_link", "entity_ambiguity", *TABELAS_PUBLICACAO} <= tabelas
    con.close()


def test_novo_publico_nao_sobrescreve_arquivo_existente(tmp_path, origem):
    with pytest.raises(FileExistsError):
        Store.novo_publico(origem)
