"""publicar/: banco público enxuto (ADR-011). Antes e depois do corte: mesmos findings, mesmo grafo,
mesmas contagens. Origem = banco fictício do seed_demo (pseudonimizado, com findings)."""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import duckdb
import pytest

from contracts import CONTRACT_VERSION, Fact, Finding
from engine import forward
from engine.factbase import FactBase
from engine.rules import load_rules
from graph import SalAusenteError, project, sal_do_ambiente
from ingest.varredura import varrer_banco
from publicar import TIPOS_INTEGRAIS, PublicacaoErro, publicar
from publicar.__main__ import main
from repo.store import TABELAS_PUBLICACAO, Store
from scripts import seed_demo

HOJE = date(2026, 11, 26)


def cpf_ok(base9: str) -> str:
    n = [int(c) for c in base9]
    for _ in range(2):
        n.append((sum(d * p for d, p in zip(n, range(len(n) + 1, 1, -1), strict=True)) * 10 % 11) % 10)
    return "".join(map(str, n))


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("publicar")
    origem, destino = pasta / "origem.duckdb", pasta / "publico.duckdb"
    seed_demo.gerar(origem)
    resumo = publicar(origem, destino, hoje=HOJE)
    return origem, destino, resumo


@pytest.fixture(scope="module")
def so(demo):
    s = Store(demo[0], read_only=True)  # origem
    yield s
    s.con.close()


@pytest.fixture(scope="module")
def pub(demo):
    s = Store(demo[1], read_only=True)
    yield s
    s.con.close()


def _linhas(store, sql):
    return store.con.execute(sql).fetchall()


# ---------- antes x depois ----------
def test_mesmos_findings_e_explicacoes(so, pub):
    sql = "SELECT id, deputado_id, regra, cf, payload::VARCHAR, explanation::VARCHAR FROM finding ORDER BY id"
    assert _linhas(pub, sql) == _linhas(so, sql) and len(_linhas(pub, sql)) > 0


def test_mesmo_grafo_que_a_projecao_sobre_os_fatos_completos(so, pub):
    esperado = project(so.load_facts(), so.load_findings(), sal_id=sal_do_ambiente(), hoje=HOJE)
    assert pub.load_graph() == esperado
    assert any(n.tipo == "empresa" and n.atributos.get("sancionada") for n in esperado[0])


def test_mesma_inferencia_que_o_forward_run_sobre_os_fatos_completos(so, pub):
    res = forward.run(FactBase(so.load_facts()), load_rules())
    por_dep: dict[str, list[Finding]] = {}
    for f in res.findings:
        por_dep.setdefault(f.deputado_id, []).append(f.model_copy(update={"evidencias": []}))
    assert por_dep
    for dep, esperado in por_dep.items():
        assert pub.inferencia_de(dep) == sorted(esperado, key=lambda f: f.regra)


def test_meta_traz_as_contagens_do_banco_completo(demo, so, pub):
    origem, _, resumo = demo
    meta = pub.load_publicacao_meta()
    assert meta["contract_version"] == CONTRACT_VERSION
    assert meta["contagem_por_tipo"] == so.contagem_por_tipo()
    assert meta["n_fatos_origem"] == sum(so.contagem_por_tipo().values()) == resumo.n_fatos_origem
    assert meta["origem_sha256"] == hashlib.sha256(origem.read_bytes()).hexdigest()
    assert meta["grafo_em"] == HOJE.isoformat()
    esperado = [{"fonte": f.fonte, "tipos": f.tipos, "n_fatos": f.n_fatos}
                for f in so.cobertura_fontes()]
    assert [{k: f[k] for k in ("fonte", "tipos", "n_fatos")} for f in meta["cobertura_fontes"]] == esperado
    janela = so.janela_votos()
    assert meta["janela_votos"] == {
        "inicio": janela.inicio.isoformat(), "fim": janela.fim.isoformat(),
        "n_votacoes": janela.n_votacoes, "n_votacoes_nominais": janela.n_votacoes_nominais,
        "n_votacoes_com_orientacao": janela.n_votacoes_com_orientacao}
    assert meta["n_deputados"] == 6 and meta["n_findings"] == len(so.load_findings())
    assert meta["n_nos"] == len(pub.load_graph()[0]) and meta["n_arestas"] == len(pub.load_graph()[1])
    assert "gerado_em" in meta and pub.publicado()


def test_meta_nao_carrega_sal_nem_caminho(demo, pub):
    texto = str(pub.load_publicacao_meta())
    assert str(demo[0].parent) not in texto and "sal-" not in texto


# ---------- o corte ----------
def test_tipos_integrais_ficam_completos_e_o_resto_so_com_evidencia(so, pub):
    por_tipo_origem, por_tipo_pub = so.contagem_por_tipo(), pub.contagem_por_tipo()
    for tipo in TIPOS_INTEGRAIS:
        assert por_tipo_pub.get(tipo, 0) == por_tipo_origem.get(tipo, 0)
    evid = {(e.tipo, e.id_oficial) for f in so.load_findings() for e in f.evidencias}
    for f in pub.load_facts():
        assert f.tipo in TIPOS_INTEGRAIS or (f.tipo, f.id_oficial) in evid
    assert sum(por_tipo_pub.values()) < sum(por_tipo_origem.values())  # houve corte


def test_toda_evidencia_dos_findings_continua_resolvendo_para_um_fato(so, pub):
    mantidos = {(f.tipo, f.id_oficial) for f in pub.load_facts()}
    for f in so.load_findings():
        for e in f.evidencias:
            assert (e.tipo, e.id_oficial) in mantidos, (f.id, e)


def test_fatos_mantidos_sao_identicos_aos_da_origem(so, pub):
    origem = {(f.tipo, f.chave): f for f in so.load_facts()}
    assert pub.load_facts() and all(origem[(f.tipo, f.chave)] == f for f in pub.load_facts())


def test_arquivo_sem_chave_primaria_nem_indice(demo):
    con = duckdb.connect(str(demo[1]), read_only=True)
    assert con.execute("SELECT count(*) FROM duckdb_constraints()").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM duckdb_indexes()").fetchone()[0] == 0
    con.close()


def test_resumo_traz_o_tamanho_e_nao_sobra_wal_nem_temporario(demo):
    # (o ganho de tamanho só aparece em escala: com 6 deputados, o piso de blocos das tabelas domina)
    _, destino, resumo = demo
    assert resumo.bytes_destino == destino.stat().st_size > 0
    assert sorted(p.name for p in destino.parent.iterdir()) == ["origem.duckdb", "publico.duckdb"]


def test_banco_publicado_nao_tem_cpf_integro(pub):
    assert varrer_banco(pub) == []
    assert not pub.tabelas_publicacao_faltando() and set(TABELAS_PUBLICACAO) >= {"graph_node"}


# ---------- falhas ----------
def test_origem_inexistente(tmp_path):
    with pytest.raises(PublicacaoErro, match="origem"):
        publicar(tmp_path / "nao-existe.duckdb", tmp_path / "pub.duckdb")


def test_destino_existente_nao_e_sobrescrito(tmp_path):
    origem, destino = tmp_path / "o.duckdb", tmp_path / "p.duckdb"
    seed_demo.gerar(origem)
    destino.write_bytes(b"x")
    with pytest.raises(PublicacaoErro, match="já existe"):
        publicar(origem, destino)
    assert destino.read_bytes() == b"x"


def test_destino_igual_a_origem_e_recusado(tmp_path):
    origem = tmp_path / "o.duckdb"
    seed_demo.gerar(origem)
    with pytest.raises(PublicacaoErro, match="mesmo arquivo"):
        publicar(origem, origem)


def test_sem_sal_falha_antes_de_criar_o_arquivo(tmp_path, monkeypatch):
    origem, destino = tmp_path / "o.duckdb", tmp_path / "p.duckdb"
    seed_demo.gerar(origem)
    monkeypatch.delenv("RAIO_X_ID_SALT", raising=False)
    with pytest.raises(SalAusenteError):
        publicar(origem, destino)
    assert not destino.exists()


def test_cpf_integro_no_banco_publicado_aborta_e_nao_deixa_arquivo(tmp_path):
    origem, destino = tmp_path / "o.duckdb", tmp_path / "p.duckdb"
    s = Store(origem)
    # `votacao` é mantida por inteiro: o CPF no texto livre iria para o arquivo público
    s.upsert_facts([Fact(tipo="deputado", chave="1", atributos={"nome": "Ana"}, fonte="t",
                         id_oficial="1", url="https://x"),
                    Fact(tipo="votacao", chave="v1", atributos={"descricao": f"parecer {cpf_ok('123456789')}"},
                         fonte="t", id_oficial="v1", url="https://x")])
    s.con.close()
    with pytest.raises(PublicacaoErro, match="CPF"):
        publicar(origem, destino)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["o.duckdb"]  # nem destino nem .tmp


def test_findings_desatualizados_em_relacao_ao_motor_abortam(tmp_path):
    origem, destino = tmp_path / "o.duckdb", tmp_path / "p.duckdb"
    seed_demo.gerar(origem)
    s = Store(origem)
    s.con.execute("DELETE FROM finding WHERE id = (SELECT min(id) FROM finding)")
    s.con.close()
    with pytest.raises(PublicacaoErro, match="make infer"):
        publicar(origem, destino)
    assert not destino.exists()


def test_origem_sem_findings_e_aceita_quando_o_motor_tambem_nao_acha_nada(tmp_path):
    origem, destino = tmp_path / "o.duckdb", tmp_path / "p.duckdb"
    s = Store(origem)
    s.upsert_facts([Fact(tipo="deputado", chave="1", atributos={"nome": "Ana", "partido": "ABC"},
                         fonte="t", id_oficial="1", url="https://x")])
    s.con.close()
    r = publicar(origem, destino)
    assert (r.n_findings, r.n_fatos_publicados) == (0, 1)


# ---------- CLI ----------
def test_cli_publica_e_imprime_o_resumo(tmp_path, capsys):
    origem, destino = tmp_path / "o.duckdb", tmp_path / "p.duckdb"
    seed_demo.gerar(origem)
    main(["--origem", str(origem), "--destino", str(destino)])
    saida = capsys.readouterr().out
    assert destino.exists() and "fatos" in saida and "findings" in saida


def test_cli_sai_com_codigo_1_e_mensagem_em_falha(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        main(["--origem", str(tmp_path / "x.duckdb"), "--destino", str(tmp_path / "p.duckdb")])
    assert e.value.code == 1
    assert "origem" in capsys.readouterr().err


def test_fato_citado_como_evidencia_e_mantido_mesmo_fora_da_lista_integral(tmp_path, monkeypatch):
    from publicar import build
    monkeypatch.setattr(build, "TIPOS_INTEGRAIS", ("deputado",))
    origem, destino = tmp_path / "o.duckdb", tmp_path / "p.duckdb"
    seed_demo.gerar(origem)
    publicar(origem, destino)
    so, pub = Store(origem, read_only=True), Store(destino, read_only=True)
    evid = {(e.tipo, e.id_oficial) for f in so.load_findings() for e in f.evidencias}
    mantidos = pub.load_facts()
    assert {f.tipo for f in mantidos} > {"deputado"}
    assert all(f.tipo == "deputado" or (f.tipo, f.id_oficial) in evid for f in mantidos)
    assert evid <= {(f.tipo, f.id_oficial) for f in mantidos}


def test_tmp_de_publicacao_com_falha_nao_sobra(tmp_path):
    origem = Path(tmp_path / "o.duckdb")
    Store(origem).con.close()
    r = publicar(origem, tmp_path / "p.duckdb")
    assert r.n_fatos_publicados == 0
    assert not list(tmp_path.glob("*.tmp"))


# ---------- a varredura de CPF cobre as tabelas materializadas ----------
@pytest.mark.parametrize("tabela,colunas,valores", [
    ("graph_node", "id, payload", "('pessoa:x', '{\"rotulo\": \"CPF {cpf}\"}')"),
    ("graph_edge", "origem, destino, rel, payload", "('a', 'b', 'doou', '{\"evidencia_ids\": [\"{cpf}\"]}')"),
    ("inferencia", "deputado_id, regra, payload", "('1', 'R01', '{\"conclusao\": \"{cpf}\"}')"),
    ("publicacao_meta", "chave, valor", "('x', '\"{cpf}\"')"),
])
def test_varredura_acha_cpf_nas_tabelas_materializadas(tmp_path, tabela, colunas, valores):
    s = Store(tmp_path / "t.duckdb")
    assert varrer_banco(s) == []
    s.con.execute(f"INSERT INTO {tabela} ({colunas}) VALUES " + valores.replace("{cpf}", cpf_ok("123456789")))
    achados = varrer_banco(s)
    assert [a.tipo for a in achados] == [tabela]
    s.con.close()
