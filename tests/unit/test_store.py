"""repo/store.py — DuckDB real (em memória ou em arquivo temporário), sem mock."""
from __future__ import annotations

import duckdb
import pytest

from contracts import Evidence, Explanation, Finding, Nivel
from repo.links import Ambiguidade, EntityLink
from repo.store import Store


def F(tipo, chave, **at):
    from contracts import Fact
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


@pytest.fixture
def store():
    return Store(":memory:")


def _por_chave(fatos):
    return {f.chave: f for f in fatos}


# ---------- upsert de fatos ----------

def test_valor_negativo_e_data_none_sobrevivem_ao_ciclo_gravar_ler(store):
    store.upsert_facts([F("despesa_ceap", "d1", deputado_id="1", valor=-120.5, data=None)])
    (f,) = store.facts_by_tipo("despesa_ceap")
    assert f.atributos["valor"] == -120.5
    assert f.atributos["data"] is None
    assert f.id_oficial == "d1" and f.url == "https://exemplo/despesa_ceap/d1"


def test_upsert_e_idempotente_e_substitui_pela_chave(store):
    fatos = [F("deputado", "1", nome="Ana"), F("deputado", "2", nome="Bia")]
    store.upsert_facts(fatos)
    store.upsert_facts(fatos)
    assert len(store.load_facts()) == 2
    store.upsert_facts([F("deputado", "1", nome="Ana Maria")])
    assert _por_chave(store.facts_by_tipo("deputado"))["1"].atributos["nome"] == "Ana Maria"
    assert len(store.load_facts()) == 2


def test_chave_repetida_no_mesmo_lote_vale_a_ultima(store):
    store.upsert_facts([F("deputado", "1", nome="velho"), F("deputado", "1", nome="novo")])
    (f,) = store.facts_by_tipo("deputado")
    assert f.atributos["nome"] == "novo"


def test_mesma_chave_em_tipos_diferentes_nao_colide(store):
    store.upsert_facts([F("deputado", "1", nome="x"), F("candidatura", "1", nome="y")])
    assert len(store.load_facts()) == 2


def test_lote_pequeno_grava_tudo(store):
    n = store.upsert_facts([F("voto", f"v{i}", voto="Sim") for i in range(7)], lote=2)
    assert n == 7
    assert len(store.facts_by_tipo("voto")) == 7


def test_upsert_vazio_nao_falha(store):
    assert store.upsert_facts([]) == 0


def test_texto_com_aspas_quebra_de_linha_e_unicode_sobrevive(store):
    nome = 'João "Zé"\nda Silva — ção'
    store.upsert_facts([F("deputado", "1", nome=nome)])
    assert store.facts_by_tipo("deputado")[0].atributos["nome"] == nome


# ---------- leitura ----------

def test_facts_by_tipo_aceita_um_ou_varios_tipos(store):
    store.upsert_facts([F("deputado", "1"), F("sancao", "s1"), F("pep", "p1")])
    assert [f.tipo for f in store.facts_by_tipo("pep")] == ["pep"]
    assert {f.tipo for f in store.facts_by_tipo(["deputado", "sancao"])} == {"deputado", "sancao"}
    assert store.facts_by_tipo("inexistente") == []


# ---------- entity_link ----------

def test_links_gravacao_idempotente(store):
    link = EntityLink("candidatura:10", "deputado:1", "nome_norm", 0.8)
    store.upsert_links([link])
    store.upsert_links([link])
    assert store.load_links() == [link]


def test_links_substituir_origens_remove_ligacao_obsoleta(store):
    store.upsert_links([EntityLink("candidatura:10", "deputado:1", "nome_norm", 0.8)])
    store.upsert_links([EntityLink("candidatura:10", "deputado:2", "cpf", 1.0)],
                       substituir_origens=["candidatura:10"])
    assert store.load_links() == [EntityLink("candidatura:10", "deputado:2", "cpf", 1.0)]


def test_load_links_filtra_por_tipo_de_origem(store):
    store.upsert_links([EntityLink("candidatura:10", "deputado:1", "nome_norm", 0.8),
                        EntityLink("emenda:9", "deputado:1", "nome_norm", 0.8)])
    assert [lk.origem for lk in store.load_links(origem_tipo="emenda")] == ["emenda:9"]


def test_links_de_um_destino_para_backlinks(store):
    store.upsert_links([EntityLink("candidatura:10", "deputado:1", "cpf", 1.0),
                        EntityLink("candidatura:11", "deputado:2", "cpf", 1.0)])
    assert [lk.origem for lk in store.links_to("deputado:1")] == ["candidatura:10"]


def test_ambiguidades_registradas_e_substituidas(store):
    store.save_ambiguities([Ambiguidade("candidatura:10", ("deputado:1", "deputado:2"), "nome+uf")])
    store.save_ambiguities([Ambiguidade("candidatura:10", ("deputado:1", "deputado:3"), "nome+uf")],
                           substituir_origens=["candidatura:10"])
    (a,) = store.load_ambiguities()
    assert a.candidatos == ("deputado:1", "deputado:3")


# ---------- compatibilidade com o motor / API ----------

def test_findings_continuam_funcionando(store):
    f = Finding(id="f1", deputado_id="1", regra="R03", categoria="integridade",
                conclusao="x", cf=0.9, nivel=Nivel.ALTA,
                evidencias=[Evidence(tipo="sancao", id_oficial="s1")])
    store.save_findings([f], {"f1": Explanation(finding_id="f1", como=[], por_que="p")})
    assert [x.id for x in store.findings_of("1")] == ["f1"]
    assert store.findings_of("2") == []


# ---------- escolha do banco ----------

def test_variavel_raio_x_db_escolhe_o_arquivo(tmp_path, monkeypatch):
    alvo = tmp_path / "outro" / "amostra.duckdb"
    monkeypatch.setenv("RAIO_X_DB", str(alvo))
    s = Store()
    s.upsert_facts([F("deputado", "1")])
    s.con.close()
    assert alvo.exists()
    assert len(Store(alvo).load_facts()) == 1


def test_parametro_explicito_vence_a_variavel_de_ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("RAIO_X_DB", str(tmp_path / "env.duckdb"))
    Store(tmp_path / "explicito.duckdb").con.close()
    assert (tmp_path / "explicito.duckdb").exists()
    assert not (tmp_path / "env.duckdb").exists()


def test_somente_leitura_le_mas_nao_escreve(tmp_path):
    caminho = tmp_path / "ro.duckdb"
    w = Store(caminho)
    w.upsert_facts([F("deputado", "1")])
    w.con.close()
    ro = Store(caminho, read_only=True)
    assert len(ro.load_facts()) == 1
    with pytest.raises(duckdb.Error):
        ro.upsert_facts([F("deputado", "2")])


def test_reabrir_banco_existente_nao_perde_dados_nem_quebra_migracao(tmp_path):
    caminho = tmp_path / "x.duckdb"
    a = Store(caminho)
    a.upsert_facts([F("deputado", "1")])
    a.upsert_links([EntityLink("candidatura:1", "deputado:1", "cpf", 1.0)])
    a.con.close()
    b = Store(caminho)
    assert len(b.load_facts()) == 1 and len(b.load_links()) == 1


# ---------- substituição antes de recarregar (chave antiga não pode sobrar) ----------

def _carga(store):
    store.upsert_facts([
        F("despesa_ceap", "a", deputado_id="1", data="2024-03-01", valor=1.0),
        F("despesa_ceap", "b", deputado_id="1", data="2023-12-30", valor=2.0),
        F("despesa_ceap", "c", deputado_id="1", data=None, valor=3.0),
        F("despesa_ceap", "d", deputado_id="2", data="2024-05-01", valor=4.0),
        F("sancao", "s1", cnpj="1"),
    ])


def test_delete_facts_por_tipo_e_atributo(store):
    _carga(store)
    assert store.delete_facts("despesa_ceap", onde={"deputado_id": ["1"]}) == 3
    assert {f.chave for f in store.load_facts()} == {"d", "s1"}


def test_delete_facts_ano_da_data_apaga_o_ano_e_as_sem_data(store):
    _carga(store)
    store.delete_facts("despesa_ceap", ano_data=2024)
    assert {f.chave for f in store.facts_by_tipo("despesa_ceap")} == {"b"}


def test_delete_facts_filtra_por_fonte_e_nao_toca_outros_tipos(store):
    _carga(store)
    assert store.delete_facts("despesa_ceap", fonte="outra") == 0
    assert store.delete_facts("despesa_ceap", fonte="teste", onde={"deputado_id": ["2"]}) == 1
    assert len(store.facts_by_tipo("sancao")) == 1


def test_delete_facts_compara_numero_e_texto_igual(store):
    store.upsert_facts([F("candidatura", "1", ano=2022, uf="MG")])
    assert store.delete_facts("candidatura", onde={"ano": [2022], "uf": ["MG"]}) == 1


def test_delete_facts_lista_vazia_nao_apaga_nada(store):
    _carga(store)
    assert store.delete_facts("despesa_ceap", onde={"deputado_id": []}) == 0
    assert len(store.facts_by_tipo("despesa_ceap")) == 4


def test_somente_leitura_de_arquivo_inexistente_da_erro_claro_e_nao_cria_arquivo(tmp_path):
    alvo = tmp_path / "nao_existe.duckdb"
    with pytest.raises(FileNotFoundError, match="nao_existe.duckdb"):
        Store(alvo, read_only=True)
    assert not alvo.exists()


def test_somente_leitura_nao_roda_migracoes(tmp_path):
    caminho = tmp_path / "antigo.duckdb"
    con = duckdb.connect(str(caminho))  # banco "antigo": sem a tabela da migração 002
    con.execute("CREATE TABLE fact (tipo TEXT, chave TEXT, atributos JSON, fonte TEXT, "
                "id_oficial TEXT, url TEXT, coletado_em TIMESTAMPTZ)")
    con.close()
    ro = Store(caminho, read_only=True)
    tabelas = {r[0] for r in ro.con.execute("SHOW TABLES").fetchall()}
    assert tabelas == {"fact"}
