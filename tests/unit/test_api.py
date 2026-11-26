"""API FastAPI read-only, sobre um DuckDB temporário populado com fatos sintéticos + motor real."""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")  # dependência adicionada ao pyproject pelo orquestrador
from fastapi.testclient import TestClient

from api.main import create_app
from contracts import Explanation, Fact, Finding
from engine import forward
from engine.factbase import FactBase
from engine.rules import load_rules
from repo.store import Store


def F(tipo, chave, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def fatos_sinteticos() -> list[Fact]:
    fs = [
        F("deputado", "1", nome="Ana Souza", partido="ABC", uf="MG", foto="http://f/1.jpg"),
        F("deputado", "2", nome="Álvaro Dias", partido="ABC", uf="SP"),
        F("deputado", "3", nome="Carla Mendes", partido="XYZ", uf="SP"),
        F("deputado", "4", nome="Zélia Prado", partido="XYZ", uf="BA"),  # sem nenhum dado
    ]
    for i in range(12):  # 12 votações nominais, governo orienta Sim
        fs.append(F("votacao", f"v{i}", nominal=True, orientacao_governo="Sim"))
        fs.append(F("voto", f"v{i}:1", votacao_id=f"v{i}", deputado_id="1", voto="Sim"))
        fs.append(F("voto", f"v{i}:2", votacao_id=f"v{i}", deputado_id="2",
                    voto="Não" if i % 2 else "Sim"))
    # deputada 3 pagou, em fev/2025, empresa sancionada desde jan/2025 (R03)
    fs += [
        F("despesa_ceap", "n3", deputado_id="3", cnpj="00000000000003", fornecedor="Posto Três",
          valor=1030.0, categoria="combustivel", data="2025-02-10"),
        F("sancao", "ceis1", cnpj="00000000000003", cadastro="CEIS", inicio="2025-01-01",
          fim=None),
        F("despesa_ceap", "n1", deputado_id="1", cnpj="00000000000001", fornecedor="Posto Um",
          valor=500.0, categoria="combustivel", data="2025-02-10"),
        F("despesa_ceap", "n2", deputado_id="2", cnpj="00000000000001", fornecedor="Posto Um",
          valor=700.0, categoria="combustivel", data="2025-02-12"),
        F("emenda", "e1", deputado_id="1", ano="2024", valor_empenhado=1000.0,
          municipio_ibge="3106200"),
    ]
    return fs


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.duckdb")
    fatos = fatos_sinteticos()
    s.upsert_facts(fatos)
    res = forward.run(FactBase(fatos), load_rules())
    s.save_findings(res.findings, res.explanations)
    return s


@pytest.fixture
def client(store):
    with TestClient(create_app(store=store)) as c:
        yield c


def ids(resp_json) -> list[str]:
    return [d["id"] for d in resp_json["items"]]


# --------------------------------------------------------------------------- /deputados
def test_lista_deputados_ordenada_por_nome_e_paginada(client):
    r = client.get("/deputados")
    assert r.status_code == 200
    body = r.json()
    assert ids(body) == ["2", "1", "3", "4"]  # Álvaro, Ana, Carla, Zélia (ordem sem acento)
    assert (body["total"], body["page"], body["page_size"]) == (4, 1, 20)
    assert body["items"][1] == {"id": "1", "nome": "Ana Souza", "partido": "ABC", "uf": "MG",
                                "foto": "http://f/1.jpg"}


def test_paginacao_page_e_page_size(client):
    p1 = client.get("/deputados", params={"page": 1, "page_size": 2}).json()
    p2 = client.get("/deputados", params={"page": 2, "page_size": 2}).json()
    assert ids(p1) == ["2", "1"] and ids(p2) == ["3", "4"]
    assert p1["total"] == p2["total"] == 4
    assert client.get("/deputados", params={"page": 9, "page_size": 2}).json()["items"] == []


@pytest.mark.parametrize("params", [
    {"page_size": 101}, {"page_size": 0}, {"page": 0}, {"uf": "MGX"}, {"uf": "1"},
    {"q": "a" * 81},
])
def test_parametros_invalidos_da_lista_dao_422(client, params):
    r = client.get("/deputados", params=params)
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["status"] == 422


def test_filtros_uf_partido_e_q_sem_acento_nem_caixa(client):
    assert ids(client.get("/deputados", params={"uf": "sp"}).json()) == ["2", "3"]
    assert ids(client.get("/deputados", params={"partido": "abc"}).json()) == ["2", "1"]
    assert ids(client.get("/deputados", params={"partido": "xyz", "uf": "ba"}).json()) == ["4"]
    assert ids(client.get("/deputados", params={"q": "alvaro"}).json()) == ["2"]
    assert ids(client.get("/deputados", params={"q": "SOUZA", "uf": "MG"}).json()) == ["1"]
    assert client.get("/deputados", params={"q": "zzz"}).json()["total"] == 0


def test_q_com_sql_injection_e_apenas_texto(client, store):
    r = client.get("/deputados", params={"q": "'; DROP TABLE fact; --"})
    assert r.status_code == 200 and r.json()["total"] == 0
    assert store.con.execute("SELECT count(*) FROM fact").fetchone()[0] > 0


# --------------------------------------------------------------------------- /deputados/{id}
def test_perfil_resume_findings_por_categoria(client):
    r = client.get("/deputados/3")
    assert r.status_code == 200
    body = r.json()
    assert body["nome"] == "Carla Mendes" and body["partido"] == "XYZ" and body["uf"] == "SP"
    cats = {c["categoria"]: c for c in body["categorias"]}
    assert cats["integridade"]["n_findings"] == 1
    assert cats["integridade"]["cf_max"] == 0.9
    assert cats["integridade"]["nivel_max"] == "alta"
    assert body["n_findings"] == sum(c["n_findings"] for c in body["categorias"])


def test_perfil_de_deputado_sem_findings_tem_categorias_vazias(client):
    body = client.get("/deputados/4").json()
    assert body["id"] == "4" and body["nome"] == "Zélia Prado"
    assert body["n_findings"] == 0 and body["categorias"] == []


def test_perfil_404_e_id_malformado_422(client):
    r = client.get("/deputados/999")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert "999" in r.json()["detail"]
    assert client.get("/deputados/1;DROP").status_code == 422


# --------------------------------------------------------------------------- findings/explicar
def test_findings_do_deputado_validam_contra_o_contrato_e_ordenam_por_cf(client):
    r = client.get("/deputados/3/findings")
    assert r.status_code == 200
    fs = [Finding.model_validate(x) for x in r.json()]
    assert fs and all(f.deputado_id == "3" for f in fs)
    assert [f.cf for f in fs] == sorted((f.cf for f in fs), reverse=True)
    assert fs[0].regra == "R03" and fs[0].nivel.value == "alta"
    assert any(e.tipo == "sancao" for e in fs[0].evidencias)


def test_findings_de_deputado_sem_nenhum_e_lista_vazia_e_inexistente_e_404(client):
    r = client.get("/deputados/4/findings")
    assert r.status_code == 200 and r.json() == []
    assert client.get("/deputados/999/findings").status_code == 404


def test_explicar_devolve_trilha_do_finding(client):
    r = client.get("/findings/R03:3/explicar")
    assert r.status_code == 200
    ex = Explanation.model_validate(r.json())
    assert ex.finding_id == "R03:3"
    assert ex.como and ex.por_que and ex.limitacoes
    assert any(p.regra == "R03" for p in ex.como)


def test_explicar_404_para_finding_inexistente(client):
    r = client.get("/findings/R99:1/explicar")
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"
    assert client.get("/findings/x'; DROP TABLE finding;--/explicar").status_code == 422


# --------------------------------------------------------------------------- grafo
def test_grafo_exige_centro_valido_e_respeita_limites(client):
    assert client.get("/grafo").status_code == 422
    assert client.get("/grafo", params={"centro": "deputado:1; x"}).status_code == 422
    assert client.get("/grafo", params={"centro": "foo:1"}).status_code == 422
    assert client.get("/grafo", params={"centro": "deputado:1", "profundidade": 3}).status_code == 422
    assert client.get("/grafo", params={"centro": "deputado:1", "profundidade": -1}).status_code == 422
    assert client.get("/grafo", params={"centro": "deputado:999"}).status_code == 404


def test_grafo_profundidade_1_do_deputado(client):
    r = client.get("/grafo", params={"centro": "deputado:3"})
    assert r.status_code == 200
    body = r.json()
    assert body["centro"] == "deputado:3" and body["profundidade"] == 1
    assert body["truncado"] is False
    nos = {n["id"]: n for n in body["nodes"]}
    assert set(nos) == {"deputado:3", "partido:XYZ", "empresa:00000000000003"}
    assert nos["deputado:3"]["atributos"]["n_findings"] == 1
    assert nos["empresa:00000000000003"]["atributos"]["sancionada"] is True
    assert nos["empresa:00000000000003"]["atributos"]["findings"] == ["R03:3"]
    rels = {(e["origem"], e["destino"], e["relacao"]) for e in body["edges"]}
    assert ("empresa:00000000000003", "deputado:3", "recebeu") in rels
    assert ("deputado:3", "partido:XYZ", "filiado_a") in rels


def test_grafo_filtra_relacoes_e_rejeita_desconhecida(client):
    r = client.get("/grafo", params={"centro": "deputado:1", "profundidade": 2,
                                     "relacoes": "recebeu,enviou_emenda"})
    assert r.status_code == 200
    assert {e["relacao"] for e in r.json()["edges"]} == {"recebeu", "enviou_emenda"}
    assert client.get("/grafo", params={"centro": "deputado:1", "relacoes": "hackeia"}).status_code == 422


def test_grafo_trunca_pelo_limite_de_nos(store):
    with TestClient(create_app(store=store, max_nos_grafo=2)) as c:
        body = c.get("/grafo", params={"centro": "deputado:1", "profundidade": 2}).json()
    assert body["truncado"] is True and len(body["nodes"]) == 2


def test_backlinks_do_no(client):
    r = client.get("/grafo/backlinks/partido:ABC")
    assert r.status_code == 200
    body = r.json()
    assert body["node_id"] == "partido:ABC" and body["total"] == 2
    assert [(b["no"]["id"], b["aresta"]["relacao"]) for b in body["backlinks"]] == [
        ("deputado:1", "filiado_a"), ("deputado:2", "filiado_a")]
    assert client.get("/grafo/backlinks/deputado:999").status_code == 404
    assert client.get("/grafo/backlinks/lixo").status_code == 422


def test_backlinks_de_no_que_so_tem_ligacoes_de_saida(client):
    """Empresa que recebeu da cota: nada aponta para ela, mas o painel precisa mostrar."""
    no = "empresa:00000000000001"
    body = client.get(f"/grafo/backlinks/{no}").json()
    assert body["total"] >= 2
    assert {b["aresta"]["origem"] for b in body["backlinks"]} == {no}
    pesos = [b["aresta"]["peso"] for b in body["backlinks"] if b["aresta"]["relacao"] == "recebeu"]
    assert pesos == sorted(pesos, reverse=True)


# --------------------------------------------------------------------------- perguntar
def test_perguntar_prova_objetivo_com_trilha(client):
    r = client.get("/perguntar", params={"deputado": "3", "objetivo": "risco_integridade"})
    assert r.status_code == 200
    body = r.json()
    assert body["objetivo"] == "risco_integridade" and body["deputado_id"] == "3"
    assert body["cf"] == 0.9 and body["nivel"] == "alta"
    assert "R03" in body["regras_usadas"] and "R03:3" in body["finding_ids"]
    assert body["trilha"][0]["objetivo"] == "risco_integridade"
    assert any(p["regra"] == "R03" and p["cf"] == 0.9 for p in body["trilha"])


def test_perguntar_objetivo_composto_propaga_cf(client):
    body = client.get("/perguntar", params={"deputado": "3",
                                            "objetivo": "merece_atencao_fiscalizacao"}).json()
    assert body["cf"] == pytest.approx(0.8 * 0.9, abs=1e-3)
    assert "R09" in body["regras_usadas"]


def test_perguntar_sem_prova_devolve_cf_zero_e_inconclusivo(client):
    body = client.get("/perguntar", params={"deputado": "1", "objetivo": "risco_integridade"}).json()
    assert body["cf"] == 0 and body["nivel"] == "inconclusivo" and body["finding_ids"] == []
    assert body["trilha"]  # mesmo sem prova a trilha mostra o que foi tentado


def test_perguntar_valida_parametros(client):
    assert client.get("/perguntar", params={"deputado": "999",
                                            "objetivo": "risco_integridade"}).status_code == 404
    r = client.get("/perguntar", params={"deputado": "1", "objetivo": "inexistente"})
    assert r.status_code == 422
    assert "risco_integridade" in r.json()["detail"]  # lista os objetivos válidos
    assert client.get("/perguntar", params={"objetivo": "risco_integridade"}).status_code == 422
    assert client.get("/perguntar", params={"deputado": "1", "objetivo": "x;y"}).status_code == 422


# --------------------------------------------------------------------------- comparar
def test_comparar_dois_deputados(client):
    r = client.get("/comparar", params={"a": "1", "b": "2"})
    assert r.status_code == 200
    body = r.json()
    assert body["a"]["id"] == "1" and body["b"]["id"] == "2"
    af = body["afinidade_votos"]
    assert (af["n_votacoes_comuns"], af["n_iguais"], af["afinidade"]) == (12, 6, 0.5)
    comum = {n["id"] for n in body["em_comum"]}
    assert "empresa:00000000000001" in comum and "partido:ABC" in comum
    assert "deputado:1" not in comum and "deputado:2" not in comum
    cats = {c["categoria"] for c in body["categorias"]}
    assert cats >= {c["categoria"] for c in body["a"]["categorias"]}


def test_comparar_sem_votos_comuns_tem_afinidade_nula(client):
    body = client.get("/comparar", params={"a": "1", "b": "3"}).json()
    assert body["afinidade_votos"] is None
    assert body["findings_b"][0]["regra"] == "R03"


def test_comparar_valida(client):
    assert client.get("/comparar", params={"a": "1", "b": "1"}).status_code == 422
    assert client.get("/comparar", params={"a": "1", "b": "999"}).status_code == 404
    assert client.get("/comparar", params={"a": "1"}).status_code == 422


# --------------------------------------------------------------------------- transversais
def test_cors_so_libera_localhost_3000(client):
    ok = client.get("/deputados", headers={"Origin": "http://localhost:3000"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:3000"
    ruim = client.get("/deputados", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in ruim.headers
    pre = client.options("/deputados", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert pre.status_code == 200
    pre_ruim = client.options("/deputados", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in pre_ruim.headers


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_api_e_somente_leitura(client, metodo):
    assert getattr(client, metodo)("/deputados").status_code == 405


def test_snapshot_e_construido_uma_vez_por_processo(store, monkeypatch):
    import api.state as st

    chamadas = []
    original = st.project
    monkeypatch.setattr(st, "project", lambda *a, **k: chamadas.append(1) or original(*a, **k))
    with TestClient(create_app(store=store)) as c:
        for _ in range(3):
            c.get("/grafo", params={"centro": "deputado:1"})
            c.get("/deputados")
    assert len(chamadas) == 1


def test_banco_inexistente_da_503_sem_vazar_caminho(tmp_path, monkeypatch):
    monkeypatch.setenv("RAIO_X_DB", str(tmp_path / "nao_existe.duckdb"))
    with TestClient(create_app()) as c:
        r = c.get("/deputados")
    assert r.status_code == 503
    assert str(tmp_path) not in r.text
    assert not (tmp_path / "nao_existe.duckdb").exists()  # a API não cria banco


def test_env_raio_x_db_escolhe_o_banco(store, tmp_path, monkeypatch):
    store.con.close()
    monkeypatch.setenv("RAIO_X_DB", str(tmp_path / "t.duckdb"))
    with TestClient(create_app()) as c:
        assert c.get("/deputados").json()["total"] == 4


def test_erro_interno_nao_vaza_detalhes(store):
    app = create_app(store=store)

    @app.get("/boom")
    def boom():
        raise RuntimeError("segredo-interno-123")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/boom")
    assert r.status_code == 500
    assert "segredo-interno-123" not in r.text
    assert r.headers["content-type"].startswith("application/problem+json")


def test_openapi_expoe_apenas_gets(client):
    spec = client.get("/openapi.json").json()
    metodos = {m for p in spec["paths"].values() for m in p}
    assert metodos == {"get"}


def test_api_abre_o_banco_somente_leitura(store, tmp_path, monkeypatch):
    """Com a API no ar o arquivo continua abrível por outro leitor; escrita seria recusada."""
    store.con.close()
    monkeypatch.setenv("RAIO_X_DB", str(tmp_path / "t.duckdb"))
    with TestClient(create_app()) as c:
        assert c.get("/deputados").status_code == 200
        outro = Store(tmp_path / "t.duckdb", read_only=True)  # RW dentro do mesmo processo falharia
        assert outro.con.execute("SELECT count(*) FROM fact").fetchone()[0] > 0
        outro.con.close()


def test_cors_origens_via_env_e_curinga_ignorado(store, monkeypatch):
    monkeypatch.setenv("RAIO_X_CORS_ORIGINS", "https://app.exemplo.com/, *")
    with TestClient(create_app(store=store)) as c:
        ok = c.get("/deputados", headers={"Origin": "https://app.exemplo.com"})
        assert ok.headers["access-control-allow-origin"] == "https://app.exemplo.com"
        outro = c.get("/deputados", headers={"Origin": "http://localhost:3000"})
        assert "access-control-allow-origin" not in outro.headers
        qualquer = c.get("/deputados", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in qualquer.headers


# --------------------------------------------------------------------------- LGPD
CPFS = ["11122233344", "55566677788", "99988877766", "12312312312", "111.222.333-44"]
FRAGMENTOS_MASCARADOS = ["123456", "999888", "***"]


def _varre_chaves(obj, achados: list[str], caminho: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            # flag booleana do motor (ex.: valores.confirmado_por_cpf) não carrega CPF
            if "cpf" in k.lower() and not isinstance(v, bool):
                achados.append(f"{caminho}/{k}")
            _varre_chaves(v, achados, f"{caminho}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _varre_chaves(v, achados, f"{caminho}[{i}]")


@pytest.fixture
def client_lgpd(tmp_path):
    fatos = fatos_sinteticos()
    for f in fatos:
        if f.tipo == "deputado" and f.chave == "1":
            f.atributos.update(cpf="11122233344", nome_civil="Ana Souza da Silva")
    fatos += [
        F("candidatura", "sq1", ano="2022", cpf="11122233344", nome="Ana Souza da Silva",
          nome_urna="Ana", cargo="DEPUTADO FEDERAL", uf="MG", partido="ABC", deputado_id="1"),
        F("doacao", "r1", sq_candidato="sq1", doador_nome="Pedro Integro",
          doador_cpf_cnpj="55566677788", valor=100.0, tipo_doador="PF"),
        F("doacao", "r2", sq_candidato="sq1", doador_nome="MARIA SOUZA",
          doador_cpf_cnpj="***123456**", valor=300.0, tipo_doador="PF"),
        F("socio", "00000000000001:MARIA", cnpj="00000000000001", nome="Maria Souza",
          cpf_cnpj="***123456**", qualificacao="Sócio"),
        F("socio", "00000000000001:JOSE", cnpj="00000000000001", nome="José Integro",
          cpf_cnpj="99988877766", qualificacao="Sócio"),
        F("despesa_ceap", "pf1", deputado_id="1", cpf="12312312312", fornecedor="Pessoa Física",
          valor=80.0, categoria="taxi", data="2025-03-01"),
        F("emenda", "e9", deputado_id="1", ano="2024", valor_empenhado=10.0, municipio_ibge="1"),
    ]
    s = Store(tmp_path / "lgpd.duckdb")
    s.upsert_facts(fatos)
    res = forward.run(FactBase(fatos), load_rules())
    s.save_findings(res.findings, res.explanations)
    with TestClient(create_app(store=s)) as c:
        yield c


def test_nenhuma_resposta_expoe_cpf_nem_chave_cpf(client_lgpd):
    """Varre TODOS os endpoints com uma base cheia de CPFs (íntegros e mascarados)."""
    c = client_lgpd
    respostas: list[tuple[str, object]] = []

    def pega(url, **params):
        r = c.get(url, params=params)
        assert r.status_code in (200, 404), (url, r.status_code, r.text)
        respostas.append((url + str(params), r.json()))
        return r.json()

    deps = [d["id"] for d in pega("/deputados", page_size=100)["items"]]
    assert "1" in deps
    pega("/cobertura")
    nos: set[str] = set()
    for d in deps:
        pega(f"/deputados/{d}")
        pega(f"/deputados/{d}/metricas")
        for f in pega(f"/deputados/{d}/findings"):
            pega(f"/findings/{f['id']}/explicar")
        g = pega("/grafo", centro=f"deputado:{d}", profundidade=2)
        nos |= {n["id"] for n in g["nodes"]}
        for obj in ("risco_integridade", "merece_atencao_fiscalizacao"):
            pega("/perguntar", deputado=d, objetivo=obj)
        for outro in deps:
            if outro > d:
                pega("/comparar", a=d, b=outro)
    assert any(n.startswith("pessoa:") for n in nos)  # a base realmente produziu nós de pessoa
    for n in sorted(nos):
        pega(f"/grafo/backlinks/{n}")
        pega("/grafo", centro=n, profundidade=1)

    for url, corpo in respostas:
        texto = str(corpo)
        for cpf in CPFS + FRAGMENTOS_MASCARADOS:
            assert cpf not in texto, f"{cpf} vazou em {url}"
        achados: list[str] = []
        _varre_chaves(corpo, achados)
        assert achados == [], f"chave cpf em {url}: {achados}"


def test_pessoa_com_cpf_mascarado_nao_expoe_nome_no_grafo(client_lgpd):
    g = client_lgpd.get("/grafo", params={"centro": "deputado:1", "profundidade": 2}).json()
    pessoas = [n for n in g["nodes"] if n["tipo"] == "pessoa"]
    rotulos = sorted(n["rotulo"] for n in pessoas)
    assert "Doador(a) pessoa física" in rotulos
    assert any(r.startswith("Sócio(a) de ") for r in rotulos)
    assert not any("MARIA" in (n["id"] + n["rotulo"]).upper() for n in pessoas)


# --------------------------------------------------------------------------- /saude
def test_saude_com_banco_ok(client, store):
    from contracts import CONTRACT_VERSION

    r = client.get("/saude")
    assert r.status_code == 200
    body = r.json()
    n_findings = store.con.execute("SELECT count(*) FROM finding").fetchone()[0]
    assert body == {"status": "ok", "contract_version": CONTRACT_VERSION, "n_deputados": 4,
                    "n_findings": n_findings, "banco": "ok", "pseudonimizado": True}
    assert n_findings > 0


def test_saude_com_banco_ausente_nao_vaza_caminho(tmp_path, monkeypatch):
    monkeypatch.setenv("RAIO_X_DB", str(tmp_path / "nao_existe.duckdb"))
    with TestClient(create_app()) as c:
        r = c.get("/saude")
    assert r.status_code == 503
    assert r.json() == {"status": "degradado", "contract_version": "0.2.0", "n_deputados": 0,
                        "n_findings": 0, "banco": "ausente", "pseudonimizado": False}
    assert str(tmp_path) not in r.text


def test_saude_nao_monta_o_snapshot(store, monkeypatch):
    import api.state as st

    monkeypatch.setattr(st, "project", lambda *a, **k: pytest.fail("saude não deve projetar"))
    with TestClient(create_app(store=store)) as c:
        assert c.get("/saude").status_code == 200


# --------------------------------------------------------------------------- /perguntar x forward
def test_perguntar_reusa_um_forward_por_snapshot_quando_prove_aceita_resultado(store, monkeypatch):
    from engine import backward
    from engine import forward as fw
    from engine.forward import InferenceResult

    rodadas, recebidos = [], []
    original = fw.run
    monkeypatch.setattr(fw, "run", lambda *a, **k: rodadas.append(1) or original(*a, **k))

    def prove_falso(goal, deputado_id, fb, rules, resultado=None):
        recebidos.append(resultado)
        return backward.GoalAnswer(goal, deputado_id, 0.0, [], [], [])

    monkeypatch.setattr(backward, "prove", prove_falso)
    with TestClient(create_app(store=store)) as c:
        for dep in ("1", "2", "3"):
            for obj in ("risco_integridade", "merece_atencao_fiscalizacao"):
                assert c.get("/perguntar", params={"deputado": dep, "objetivo": obj}).status_code == 200
    assert len(rodadas) == 1
    assert len(recebidos) == 6
    assert all(isinstance(x, InferenceResult) for x in recebidos)
    assert len({id(x) for x in recebidos}) == 1


# --------------------------------------------------------------------------- entrada Vercel
def test_api_index_exporta_o_mesmo_app_asgi(store, monkeypatch):
    import api.index as idx
    from api.main import app

    assert idx.app is app
    spec = TestClient(idx.app).get("/openapi.json").json()
    assert "/saude" in spec["paths"]


def test_caminho_relativo_do_banco_resolve_a_partir_da_raiz_do_projeto(store, tmp_path, monkeypatch):
    import api.state as st

    store.con.close()
    monkeypatch.setattr(st, "RAIZ", tmp_path)
    monkeypatch.chdir("/")  # cwd diferente da raiz (como numa função serverless)
    monkeypatch.setenv("RAIO_X_DB", "t.duckdb")
    with TestClient(create_app()) as c:
        assert c.get("/saude").json()["banco"] == "ok"


def _client_com(tmp_path, extras):
    fatos = fatos_sinteticos() + extras
    s = Store(tmp_path / "ps.duckdb")
    s.upsert_facts(fatos)
    return TestClient(create_app(store=s))


@pytest.mark.parametrize(("extras", "esperado"), [
    ([F("doacao", "r1", sq_candidato="x", doador_nome="A", doador_cpf_cnpj="hmac:ab12cd34",
        valor=1.0, tipo_doador="PF"),
      F("socio", "c:A", cnpj="00000000000001", nome="A", cpf_cnpj="hmac:ab12cd34"),
      F("doacao", "r2", sq_candidato="x", doador_nome="B", doador_cpf_cnpj="***123456**",
        valor=1.0, tipo_doador="PF")], True),  # hash e mascarado não são CPF íntegro
    ([F("doacao", "r1", sq_candidato="x", doador_nome="A", doador_cpf_cnpj="12345678901",
        valor=1.0, tipo_doador="PF")], False),
    ([F("doacao", "r1", sq_candidato="x", doador_nome="A", doador_cpf_cnpj="123.456.789-01",
        valor=1.0, tipo_doador="PF")], False),
    ([F("socio", "c:A", cnpj="00000000000001", nome="A", cpf_cnpj="12345678901")], False),
    ([F("pep", "p1", nome="P", cpf="12345678901", cargo="x", orgao="y", inicio="2020-01-01")], False),
    ([F("despesa_ceap", "pf", deputado_id="1", cpf="12345678901", valor=1.0)], False),
    ([F("doacao", "r1", sq_candidato="x", doador_nome="PJ", doador_cpf_cnpj="22222222000122",
        valor=1.0, tipo_doador="PJ")], True),  # CNPJ não é CPF
])
def test_saude_pseudonimizado_so_quando_nao_ha_cpf_integro_de_terceiro(tmp_path, extras, esperado):
    with _client_com(tmp_path, extras) as c:
        r = c.get("/saude")
    assert r.status_code == 200 and r.json()["pseudonimizado"] is esperado


def test_saude_erro_inesperado_da_503_com_banco_erro(store, monkeypatch):
    import api.state as st

    def quebra(self):
        raise RuntimeError("falha-interna-xyz")

    monkeypatch.setattr(st.AppState, "contagens", quebra)
    with TestClient(create_app(store=store)) as c:
        r = c.get("/saude")
    assert r.status_code == 503 and r.json()["banco"] == "erro"
    assert "falha-interna-xyz" not in r.text
