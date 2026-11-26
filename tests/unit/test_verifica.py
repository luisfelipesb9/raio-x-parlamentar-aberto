"""scripts/verifica.py: recalcula governismo e CEAP direto dos brutos e confronta com banco e motor.

Dados sintéticos no formato real dos brutos da Câmara; nenhum teste usa rede (o modo --online é
exercitado com httpx.MockTransport).
"""
from __future__ import annotations

import ast
import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest

from engine import forward
from engine.factbase import FactBase
from engine.rules import load_rules
from repo.store import Store
from scripts import verifica
from sources.camara.source import CamaraSource
from sources.ceap.source import CeapSource


def votacao(vid, *, data="2025-02-10", gov="Sim", votos=()):
    return {"id": vid, "data": data, "siglaOrgao": "PLEN", "uri": f"https://x/votacoes/{vid}",
            "_votos": [{"tipoVoto": v, "deputado_": {"id": d}} for d, v in votos],
            "_orientacoes": ([{"siglaPartidoBloco": "Governo", "orientacaoVoto": gov}]
                             if gov is not None else [])}


def bruto_camara():
    """Dep 1: 12 votos todos Sim (dispara R01). Dep 2: 6 votos (poucos). Dep 3: sem voto."""
    vs = []
    for i in range(12):
        votos = [(1, "Sim")] + ([(2, "Não")] if i < 6 else [])
        vs.append(votacao(f"v{i}", votos=votos))
    vs.append(votacao("ab", gov="Não", votos=[(1, "Abstenção"), (2, "Sim")]))  # 1 inválido, 2 válido
    vs.append(votacao("sim"))  # simbólica: nenhum voto individual
    vs.append(votacao("sem-gov", gov=None, votos=[(1, "Sim")]))  # nominal sem orientação
    return {"deputados": [{"id": i, "nome": f"Dep {i}", "siglaPartido": "P", "siglaUf": "MG",
                           "uri": f"https://x/deputados/{i}"} for i in (1, 2, 3)],
            "votacoes": vs}


def linhas_ceap():
    base = {"ano": 2024, "mes": 3, "descricao": "COMBUSTÍVEL", "dataEmissao": "2024-03-10T00:00:00",
            "fornecedor": "Posto", "cnpjCPF": "11.222.333/0001-81", "parcela": 0, "lote": 1}
    return [
        {**base, "idDeputado": 1, "idDocumento": 11, "numero": "a", "valorLiquido": 100.10},
        {**base, "idDeputado": 1, "idDocumento": 12, "numero": "b", "valorLiquido": 200.20},
        {**base, "idDeputado": 1, "idDocumento": 13, "numero": "c", "valorLiquido": -50.05},
        {**base, "idDeputado": 2, "idDocumento": 21, "numero": "d", "valorLiquido": 10.0},
        {**base, "idDeputado": 99, "idDocumento": 91, "numero": "e", "valorLiquido": 999.0},  # fora
    ]


@pytest.fixture
def ambiente(tmp_path):
    """Banco e brutos coerentes entre si, como saem do ingest + `make infer`."""
    raw = tmp_path / "raw"
    (raw / "camara").mkdir(parents=True)
    (raw / "ceap").mkdir()
    bc, lc = bruto_camara(), linhas_ceap()
    (raw / "camara" / "camara_2025-01-01_2025-03-31.json").write_text(json.dumps(bc), "utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("Ano-2024.json", json.dumps({"dados": lc}))
    (raw / "ceap" / "Ano-2024.json.zip").write_bytes(buf.getvalue())
    fatos = CamaraSource().normalize(bc) + [f for f in CeapSource().normalize({"dados": lc})
                                            if f.atributos["deputado_id"] in ("1", "2")]
    db = tmp_path / "t.duckdb"
    s = Store(db)
    s.upsert_facts(fatos)
    res = forward.run(FactBase(fatos), load_rules())
    s.save_findings(res.findings, res.explanations)
    s.con.close()
    return db, raw


def rodar(db, raw, **kw):
    return verifica.verificar(db, raw, **kw)


def por(resultado, verificacao):
    return [lin for lin in resultado.linhas if lin.verificacao == verificacao]


# --------------------------------------------------------------------------- governismo
def test_base_coerente_nao_tem_divergencia(ambiente):
    db, raw = ambiente
    r = rodar(db, raw, gerar_manifesto=True)
    assert [lin for lin in r.linhas if lin.status != "ok"] == []
    assert r.divergencias == 0


def test_governismo_do_bruto_conta_so_voto_valido_em_votacao_nominal_com_orientacao():
    g = verifica.governismo_do_bruto(bruto_camara())
    assert (g["1"].n, g["1"].taxa) == (12, 1.0)   # 'ab' (Abstenção) e 'sem-gov' ficam fora
    assert (g["2"].n, g["2"].convergentes) == (7, 0)  # 6 Não contra Sim + 1 Sim contra orientação Não
    assert "3" not in g  # nunca votou


def test_governismo_linha_por_deputado_traz_n_taxa_e_decisao(ambiente):
    db, raw = ambiente
    r = {lin.item.split(" ")[0]: lin for lin in por(rodar(db, raw), "governismo")}
    assert set(r) == {"1", "2", "3"}  # todo deputado do banco, mesmo sem voto
    assert (r["1"].esperado, r["1"].obtido) == ("12 votos, taxa 1.0, dispara", ) * 2
    assert r["2"].esperado == r["2"].obtido == "7 votos, taxa 0.0, não dispara"
    assert r["3"].esperado == r["3"].obtido == "0 votos, taxa —, não dispara"


def test_diverge_quando_um_voto_some_do_banco(ambiente):
    db, raw = ambiente
    s = Store(db)
    s.con.execute("DELETE FROM fact WHERE tipo = 'voto' AND chave = 'v0:1'")
    s.con.close()
    r = rodar(db, raw)
    lin = next(x for x in por(r, "governismo") if x.item.startswith("1 "))
    assert lin.status == "diverge" and "11 votos" in lin.obtido and "12 votos" in lin.esperado
    assert r.divergencias >= 1


def test_diverge_quando_o_motor_deixa_de_gerar_o_finding(ambiente):
    db, raw = ambiente
    s = Store(db)
    s.con.execute("DELETE FROM finding WHERE id = 'R01:1'")
    s.con.close()
    lin = next(x for x in por(rodar(db, raw), "governismo") if x.item.startswith("1 "))
    assert lin.status == "diverge" and "não dispara" in lin.obtido


def test_diverge_quando_a_taxa_do_motor_difere_do_bruto(ambiente):
    db, raw = ambiente
    s = Store(db)
    payload = json.loads(s.con.execute("SELECT payload FROM finding WHERE id = 'R01:1'").fetchone()[0])
    payload["valores"]["taxa_governismo"] = 0.9
    s.con.execute("UPDATE finding SET payload = ? WHERE id = 'R01:1'", [json.dumps(payload)])
    s.con.close()
    lin = next(x for x in por(rodar(db, raw), "governismo") if x.item.startswith("1 "))
    assert lin.status == "diverge" and "taxa 0.9" in lin.obtido


def test_votacoes_do_bruto_batem_com_o_banco(ambiente):
    db, raw = ambiente
    esperado = {lin.item: (lin.esperado, lin.obtido) for lin in por(rodar(db, raw), "votacoes")}
    assert esperado["votações"] == ("15", "15")
    assert esperado["votações nominais"] == ("14", "14")
    assert esperado["votações com orientação Sim/Não"] == ("14", "14")


# --------------------------------------------------------------------------- CEAP
def test_ceap_soma_em_centavos_por_deputado_do_bruto():
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as z:
        z.writestr("a.json", json.dumps({"dados": linhas_ceap()}))
    tot = verifica.ceap_do_bruto(io.BytesIO(zip_bytes.getvalue()), {"1", "2"})
    assert tot == {"1": (3, 25025), "2": (1, 1000)}  # 100,10 + 200,20 - 50,05


def test_ceap_confere_contagem_e_valor_por_deputado(ambiente):
    db, raw = ambiente
    linhas = {lin.item.split(" ")[0]: lin for lin in por(rodar(db, raw), "ceap")}
    assert linhas["1"].esperado == linhas["1"].obtido == "3 despesas, R$ 250,25"
    assert linhas["2"].esperado == linhas["2"].obtido == "1 despesas, R$ 10,00"
    assert all(x.status == "ok" for x in linhas.values())


def test_ceap_diverge_se_o_valor_no_banco_muda_mais_de_um_centavo(ambiente):
    db, raw = ambiente
    s = Store(db)
    s.con.execute("UPDATE fact SET atributos = json_merge_patch(atributos, '{\"valor\": 250.0}') "
                  "WHERE tipo = 'despesa_ceap' AND json_extract_string(atributos, '$.deputado_id') = '2'")
    s.con.close()
    lin = next(x for x in por(rodar(db, raw), "ceap") if x.item.startswith("2 "))
    assert lin.status == "diverge" and "R$ 250,00" in lin.obtido


def test_ceap_diverge_se_falta_uma_despesa_no_banco(ambiente):
    db, raw = ambiente
    s = Store(db)
    s.con.execute("DELETE FROM fact WHERE chave IN (SELECT chave FROM fact WHERE tipo = 'despesa_ceap' "
                  "AND json_extract_string(atributos, '$.deputado_id') = '1' LIMIT 1)")
    s.con.close()
    lin = next(x for x in por(rodar(db, raw), "ceap") if x.item.startswith("1 "))
    assert lin.status == "diverge" and "2 despesas" in lin.obtido


def test_ceap_sem_zip_vira_aviso_e_nao_aprova_em_silencio(ambiente):
    db, raw = ambiente
    (raw / "ceap" / "Ano-2024.json.zip").unlink()
    r = rodar(db, raw)
    [lin] = por(r, "ceap")
    assert lin.status == "nao_verificado" and "zip" in lin.detalhe
    assert r.nao_verificados >= 1


# --------------------------------------------------------------------------- manifesto
def test_sem_manifesto_acusa_arquivos_nao_registrados(ambiente):
    db, raw = ambiente
    r = rodar(db, raw)
    assert {lin.status for lin in por(r, "manifesto")} == {"diverge"}
    assert r.divergencias == 2  # o json da Câmara e o zip da CEAP


def test_gerar_manifesto_cria_retroativo_e_depois_confere(ambiente):
    db, raw = ambiente
    r = rodar(db, raw, gerar_manifesto=True)
    assert r.manifesto_gerado == 2
    assert [lin.status for lin in por(r, "manifesto")] == ["ok"]
    assert r.divergencias == 0


def test_arquivo_alterado_depois_do_manifesto_e_divergencia(ambiente):
    db, raw = ambiente
    rodar(db, raw, gerar_manifesto=True)
    (raw / "ceap" / "Ano-2024.json.zip").write_bytes(b"adulterado")
    r = rodar(db, raw)
    assert any("sha256_diferente" in lin.detalhe for lin in por(r, "manifesto"))
    assert r.divergencias >= 1


# --------------------------------------------------------------------------- online
def cliente(contagens: dict[str, int], visto: list[str] | None = None) -> httpx.Client:
    def handler(req: httpx.Request) -> httpx.Response:
        if visto is not None:
            visto.append(str(req.url))
        vid = req.url.path.split("/")[-2]
        return httpx.Response(200, json={"dados": [{"tipoVoto": "Sim"}] * contagens[vid]})
    return httpx.Client(transport=httpx.MockTransport(handler))


def contagens_reais():
    return {v["id"]: len(v["_votos"]) for v in bruto_camara()["votacoes"]}


def test_online_desligado_por_padrao_nao_chama_a_rede(ambiente, monkeypatch):
    db, raw = ambiente

    def proibido(*a, **k):
        raise AssertionError("rede não deveria ser usada sem --online")

    monkeypatch.setattr(httpx.Client, "send", proibido)
    r = rodar(db, raw)
    assert por(r, "online") == []


def test_online_confere_contagem_de_votos_por_amostragem(ambiente):
    db, raw = ambiente
    visto: list[str] = []
    r = rodar(db, raw, online=True, cliente_http=cliente(contagens_reais(), visto), amostra_online=4,
              semente=7)
    linhas = por(r, "online")
    assert len(linhas) == 4 == len(visto)
    assert all(x.status == "ok" for x in linhas)
    assert all(u.startswith("https://dadosabertos.camara.leg.br/api/v2/votacoes/") for u in visto)


def test_online_e_reprodutivel_com_a_mesma_semente(ambiente):
    db, raw = ambiente
    a = rodar(db, raw, online=True, cliente_http=cliente(contagens_reais()), amostra_online=3, semente=1)
    b = rodar(db, raw, online=True, cliente_http=cliente(contagens_reais()), amostra_online=3, semente=1)
    assert [x.item for x in por(a, "online")] == [x.item for x in por(b, "online")]


def test_online_diverge_quando_a_api_tem_outra_contagem(ambiente):
    db, raw = ambiente
    falsas = {k: v + 1 for k, v in contagens_reais().items()}
    r = rodar(db, raw, online=True, cliente_http=cliente(falsas), amostra_online=2, semente=0,
              gerar_manifesto=True)
    assert {x.status for x in por(r, "online")} == {"diverge"}
    assert r.divergencias == 2


def test_online_com_falha_de_rede_e_nao_verificado_nunca_ok(ambiente):
    db, raw = ambiente

    def cai(req):
        raise httpx.ConnectError("sem rede")

    c = httpx.Client(transport=httpx.MockTransport(cai))
    r = rodar(db, raw, online=True, cliente_http=c, amostra_online=2, semente=0,
              gerar_manifesto=True)
    assert {x.status for x in por(r, "online")} == {"nao_verificado"}
    assert r.divergencias == 0 and r.nao_verificados >= 2


# --------------------------------------------------------------------------- saída e CLI
def test_relatorio_markdown_lista_divergencias_e_data(ambiente):
    db, raw = ambiente
    s = Store(db)
    s.con.execute("DELETE FROM fact WHERE tipo = 'voto' AND chave = 'v0:1'")
    s.con.close()
    md = verifica.renderizar_md(rodar(db, raw), quando="2026-11-26")
    assert md.startswith("# Verificação dos dados")
    assert "2026-11-26" in md and "REPROVADO" in md
    assert "## Divergências" in md and "11 votos" in md
    assert str(raw) not in md and str(db) not in md  # sem caminho da máquina no documento


def test_relatorio_markdown_sem_divergencia_diz_isso_explicitamente(ambiente):
    db, raw = ambiente
    md = verifica.renderizar_md(rodar(db, raw, gerar_manifesto=True), quando="2026-11-26")
    assert "APROVADO" in md and "Nenhuma divergência" in md


def test_cli_grava_relatorio_e_devolve_codigo_de_saida(ambiente, tmp_path, capsys):
    db, raw = ambiente
    saida = tmp_path / "verificacao.md"
    ok = verifica.main(["--db", str(db), "--raw", str(raw), "--gerar-manifesto",
                        "--saida", str(saida)])
    assert ok == 0 and saida.exists()
    assert "governismo" in capsys.readouterr().out
    s = Store(db)
    s.con.execute("DELETE FROM fact WHERE tipo = 'voto' AND chave = 'v0:1'")
    s.con.close()
    assert verifica.main(["--db", str(db), "--raw", str(raw), "--saida", str(saida)]) == 1


def test_cli_usa_variaveis_de_ambiente_como_padrao(ambiente, monkeypatch, tmp_path):
    db, raw = ambiente
    monkeypatch.setenv("RAIO_X_DB", str(db))
    monkeypatch.setenv("RAIO_X_RAW", str(raw))
    assert verifica.main(["--gerar-manifesto", "--saida", str(tmp_path / "v.md")]) == 0


def test_banco_inexistente_e_erro_claro(tmp_path):
    with pytest.raises(SystemExit):
        verifica.main(["--db", str(tmp_path / "nao.duckdb"), "--raw", str(tmp_path)])


def test_verifica_nao_importa_o_motor():
    """Independência: a verificação não pode herdar um erro do motor que ela deve conferir."""
    arvore = ast.parse(Path(verifica.__file__).read_text(encoding="utf-8"))
    importados = {n.module.split(".")[0] for n in ast.walk(arvore)
                  if isinstance(n, ast.ImportFrom) and n.module} | \
                 {a.name.split(".")[0] for n in ast.walk(arvore) if isinstance(n, ast.Import)
                  for a in n.names}
    assert not importados & {"engine", "graph", "api", "knowledge"}
