"""ingest.deploy_check: o sal do envio e os segredos locais (banco e CPF: tests/unit/test_resolve.py)."""
import pytest

from contracts import Fact
from ingest import deploy_check
from ingest.deploy_check import (
    DISTINTOS_MINIMO_SAL,
    TAMANHO_MINIMO_SAL,
    verificar_envio,
    verificar_sal,
)
from repo.store import Store

SAL_BOM = "x7Kq9vR2mN4pL8sT1wY6zB3cD5fG0hJ-"  # 32 caracteres, inventado para o teste
assert len(SAL_BOM) == TAMANHO_MINIMO_SAL


@pytest.mark.parametrize("sal", [None, "", "   "])
def test_reprova_sal_ausente(sal):
    (erro,) = verificar_sal(sal)
    assert "RAIO_X_ID_SALT" in erro and "ausente" in erro


@pytest.mark.parametrize("sal", ["raio-x-v1", "sal-fixo-da-demonstracao", "sal-somente-para-testes",
                                 "  raio-x-v1  "])
def test_reprova_sal_publico_conhecido(sal):
    (erro,) = verificar_sal(sal)
    assert "público" in erro
    assert sal.strip() not in erro  # nunca ecoa o valor do sal


def test_reprova_sal_publico_mesmo_quando_longo(monkeypatch):
    longo = "z" * 40
    monkeypatch.setattr(deploy_check, "SAIS_PUBLICOS", frozenset({longo}))
    (erro,) = verificar_sal(longo)
    assert "público" in erro


def test_reprova_sal_curto():
    curto = SAL_BOM[:-1]
    (erro,) = verificar_sal(curto)
    assert "curto" in erro and str(TAMANHO_MINIMO_SAL) in erro and curto not in erro


@pytest.mark.parametrize("sal", ["a" * 64, "ab" * 32, "0123456" * 6])  # longos, mas com < 8 distintos
def test_reprova_sal_longo_com_pouca_variedade(sal):
    (erro,) = verificar_sal(sal)
    assert "distintos" in erro and str(DISTINTOS_MINIMO_SAL) in erro and sal not in erro


def test_aceita_sal_com_exatamente_o_minimo_de_distintos():
    assert verificar_sal("01234567" * 4) == []


def test_aceita_sal_longo_e_desconhecido():
    assert verificar_sal(SAL_BOM) == []
    assert verificar_sal(f"  {SAL_BOM}  ") == []


def _base_publica(raiz):
    pub = raiz / "data" / "sample" / "raio_x_publico.duckdb"
    st = Store(pub)
    st.upsert_facts([Fact(tipo="doacao", chave="r1", atributos={"doador_cpf_cnpj": "hmac:abc"},
                          fonte="teste", id_oficial="r1", url="https://exemplo/doacao/r1")])
    st.save_publicacao_meta({"gerado_em": "2026-11-26T00:00:00+00:00"})  # marca: gerada por `publicar`
    st.con.close()
    return pub


@pytest.mark.parametrize("nome", [".env", ".env.local", "web/.env.production", "api/.env.vercel"])
def test_reprova_env_local_no_pacote(tmp_path, nome):
    pub = _base_publica(tmp_path)
    arq = tmp_path / nome
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text("RAIO_X_ID_SALT=segredo-que-nao-pode-ir\n")
    (erro,) = verificar_envio(tmp_path, pub)
    assert nome in erro and "segredo" in erro
    assert f"rm {nome}" in erro  # a mensagem diz como limpar
    assert "segredo-que-nao-pode-ir" not in erro


def test_env_de_exemplo_e_pastas_ignoradas_passam(tmp_path):
    pub = _base_publica(tmp_path)
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / ".env.example").write_text("NEXT_PUBLIC_API_URL=http://localhost:8000\n")
    (tmp_path / "node_modules" / "pacote").mkdir(parents=True)
    (tmp_path / "node_modules" / "pacote" / ".env").write_text("x=1\n")
    assert verificar_envio(tmp_path, pub) == []


def test_main_reprova_sem_sal_mesmo_com_o_pacote_limpo(tmp_path, monkeypatch, capsys):
    pub = _base_publica(tmp_path)
    monkeypatch.delenv("RAIO_X_ID_SALT", raising=False)
    with pytest.raises(SystemExit) as saida:
        deploy_check.main(["--raiz", str(tmp_path), "--publico", str(pub)])
    assert saida.value.code == 1
    assert "RAIO_X_ID_SALT" in capsys.readouterr().out


def test_main_reprova_o_sal_da_demo(tmp_path, monkeypatch, capsys):
    pub = _base_publica(tmp_path)
    monkeypatch.setenv("RAIO_X_ID_SALT", "sal-fixo-da-demonstracao")
    with pytest.raises(SystemExit) as saida:
        deploy_check.main(["--raiz", str(tmp_path), "--publico", str(pub)])
    assert saida.value.code == 1
    assert "sal-fixo-da-demonstracao" not in capsys.readouterr().out


def test_main_aprova_sal_bom_e_pacote_limpo(tmp_path, monkeypatch, capsys):
    pub = _base_publica(tmp_path)
    monkeypatch.setenv("RAIO_X_ID_SALT", SAL_BOM)
    with pytest.raises(SystemExit) as saida:
        deploy_check.main(["--raiz", str(tmp_path), "--publico", str(pub)])
    assert saida.value.code == 0
    out = capsys.readouterr().out
    assert "ok" in out and SAL_BOM not in out


def test_reprova_base_publica_que_nao_foi_gerada_por_publicar(tmp_path):
    pub = tmp_path / "data" / "sample" / "raio_x_publico.duckdb"
    st = Store(pub)  # tabelas novas existem, mas vazias: é banco de trabalho
    st.con.close()
    (erro,) = verificar_envio(tmp_path, pub)
    assert "make publicar" in erro


def test_reprova_base_publica_antiga_sem_as_tabelas_novas(tmp_path):
    import duckdb
    pub = tmp_path / "data" / "sample" / "raio_x_publico.duckdb"
    pub.parent.mkdir(parents=True)
    con = duckdb.connect(str(pub))
    con.execute("CREATE TABLE fact (tipo TEXT, chave TEXT, atributos JSON, fonte TEXT, id_oficial TEXT, "
                "url TEXT, coletado_em TIMESTAMPTZ)")
    con.execute("CREATE TABLE finding (id TEXT, deputado_id TEXT, regra TEXT, cf DOUBLE, payload JSON, "
                "explanation JSON)")
    con.execute("CREATE TABLE entity_link (origem TEXT, destino TEXT, metodo TEXT, cf DOUBLE)")
    con.execute("CREATE TABLE entity_ambiguity (origem TEXT, candidatos JSON, motivo TEXT)")
    con.close()
    (erro,) = verificar_envio(tmp_path, pub)
    assert "graph_node" in erro and "publicacao_meta" in erro and "make publicar" in erro


@pytest.mark.parametrize("nome", ["raio_x_publico.duckdb.tmp", "outro.duckdb.wal", "x.duckdb.tmp"])
def test_reprova_temporario_e_wal_de_banco_na_arvore(tmp_path, nome):
    pub = _base_publica(tmp_path)
    (tmp_path / "data" / "sample" / nome).write_text("x")
    (erro,) = verificar_envio(tmp_path, pub)
    assert nome in erro
