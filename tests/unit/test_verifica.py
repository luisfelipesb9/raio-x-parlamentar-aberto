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


# --------------------------------------------------------------------------- CEAP de vários anos
def _linhas_2023():
    base = {"ano": 2023, "mes": 5, "descricao": "COMBUSTÍVEL", "dataEmissao": "2023-05-10T00:00:00",
            "fornecedor": "Posto", "cnpjCPF": "11.222.333/0001-81", "parcela": 0, "lote": 1}
    return [{**base, "idDeputado": 1, "idDocumento": 31, "numero": "x", "valorLiquido": 40.0},
            {**base, "idDeputado": 1, "idDocumento": 32, "numero": "y", "valorLiquido": 60.5},
            {**base, "idDeputado": 2, "idDocumento": 33, "numero": "z", "valorLiquido": 5.0}]


def _zip_ano(raw: Path, ano: int, linhas: list[dict]) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"Ano-{ano}.json", json.dumps({"dados": linhas}))
    (raw / "ceap" / f"Ano-{ano}.json.zip").write_bytes(buf.getvalue())


@pytest.fixture
def ambiente_dois_anos(ambiente):
    """O ambiente de sempre (CEAP 2024) mais o zip de 2023, também ingerido no banco."""
    db, raw = ambiente
    linhas = _linhas_2023()
    _zip_ano(raw, 2023, linhas)
    s = Store(db)
    s.upsert_facts([f for f in CeapSource().normalize({"dados": linhas})])
    s.con.close()
    return db, raw


def test_ceap_soma_os_zips_de_todos_os_anos_do_diretorio(ambiente_dois_anos):
    db, raw = ambiente_dois_anos
    linhas = {lin.item.split(" ")[0]: lin for lin in por(rodar(db, raw), "ceap")}
    assert linhas["1"].esperado == linhas["1"].obtido == "5 despesas, R$ 350,75"  # 250,25 + 100,50
    assert linhas["2"].esperado == linhas["2"].obtido == "2 despesas, R$ 15,00"
    assert all(x.status == "ok" for x in linhas.values())


def test_ceap_de_varios_anos_avisa_quais_zips_somou(ambiente_dois_anos):
    db, raw = ambiente_dois_anos
    r = rodar(db, raw)
    assert any("Ano-2023.json.zip" in a and "Ano-2024.json.zip" in a for a in r.avisos)


def test_ceap_de_um_ano_so_nao_gera_aviso_de_zips(ambiente):
    db, raw = ambiente
    assert not any("Ano-" in a for a in rodar(db, raw).avisos)


def test_ceap_diverge_se_falta_no_banco_uma_despesa_de_um_dos_anos(ambiente_dois_anos):
    db, raw = ambiente_dois_anos
    s = Store(db)
    s.con.execute("DELETE FROM fact WHERE tipo = 'despesa_ceap' AND json_extract_string(atributos, "
                  "'$.data') LIKE '2023%' AND json_extract_string(atributos, '$.deputado_id') = '2'")
    s.con.close()
    lin = next(x for x in por(rodar(db, raw), "ceap") if x.item.startswith("2 "))
    assert lin.status == "diverge" and "1 despesas" in lin.obtido and "2 despesas" in lin.esperado


def test_ceap_zip_de_um_ano_ilegivel_e_nao_verificado_e_nao_aprova(ambiente_dois_anos):
    db, raw = ambiente_dois_anos
    (raw / "ceap" / "Ano-2023.json.zip").write_bytes(b"isto nao e um zip")
    [lin] = por(rodar(db, raw), "ceap")
    assert lin.status == "nao_verificado" and "Ano-2023.json.zip" in lin.item


def test_ceap_anos_restringe_os_zips_conferidos(ambiente_dois_anos):
    db, raw = ambiente_dois_anos
    _zip_ano(raw, 2020, [{**_linhas_2023()[0], "ano": 2020, "idDocumento": 77}])  # zip velho, fora do banco
    ok = por(rodar(db, raw, anos_ceap=(2023, 2024)), "ceap")
    assert ok and all(x.status == "ok" for x in ok)
    forcado = por(rodar(db, raw, anos_ceap=(2020, 2024)), "ceap")  # o usuário manda: vale o que pediu
    assert any(x.status == "diverge" for x in forcado)


def test_banco_so_com_2024_e_zips_2023_e_2024_em_disco_confere_sem_divergir(ambiente):
    """O padrão são os anos efetivamente ingeridos: o zip de 2023 sobrando não reprova, mas também
    não fica como se estivesse conferido."""
    db, raw = ambiente
    _zip_ano(raw, 2023, _linhas_2023())  # não foi ingerido neste banco
    r = rodar(db, raw)
    deputados = [x for x in por(r, "ceap") if x.item[0].isdigit()]
    assert deputados and all(x.status == "ok" for x in deputados) and r.divergencias == 0
    [zip_sobrando] = [x for x in por(r, "ceap") if x.item == "Ano-2023.json.zip"]
    assert zip_sobrando.status == "nao_verificado"
    assert "não fecha com o banco" in zip_sobrando.detalhe and "--anos-ceap" in zip_sobrando.detalhe
    assert r.nao_verificados >= 1
    assert any("Ano-2023.json.zip" in a and "ignorado" in a for a in r.avisos)


def test_ano_que_faltou_entrar_no_banco_nao_passa_como_ok(ambiente):
    """Banco com 2023, zip de 2024 íntegro em disco que não foi ingerido: o 2024 sai como não
    verificado, e o relatório não diz que tudo foi conferido."""
    db, raw = ambiente
    _zip_ano(raw, 2023, _linhas_2023())
    s = Store(db)
    s.con.execute("DELETE FROM fact WHERE tipo = 'despesa_ceap'")  # o banco só tem 2023
    s.upsert_facts(CeapSource().normalize({"dados": _linhas_2023()}))
    s.con.close()
    r = rodar(db, raw)
    assert r.divergencias == 0
    [faltou] = [x for x in por(r, "ceap") if x.item == "Ano-2024.json.zip"]
    assert faltou.status == "nao_verificado" and "--anos-ceap" in faltou.detalhe
    assert "Ano-2024.json.zip" in verifica.renderizar_md(r).split("## Não verificado")[1]


def test_zip_sobrando_nao_mascara_despesa_que_falta_no_banco(ambiente):
    db, raw = ambiente
    _zip_ano(raw, 2023, _linhas_2023())
    s = Store(db)
    s.con.execute("DELETE FROM fact WHERE chave IN (SELECT chave FROM fact WHERE tipo = 'despesa_ceap' "
                  "AND json_extract_string(atributos, '$.deputado_id') = '1' LIMIT 1)")
    s.con.close()
    assert any(x.status == "diverge" for x in por(rodar(db, raw), "ceap"))


def test_ceap_anos_com_zip_ausente_e_nao_verificado(ambiente):
    db, raw = ambiente
    [lin] = por(rodar(db, raw, anos_ceap=(2023, 2024)), "ceap")
    assert lin.status == "nao_verificado" and "2023" in lin.detalhe


def test_cli_anos_ceap_e_repassado(ambiente_dois_anos, tmp_path):
    db, raw = ambiente_dois_anos
    _zip_ano(raw, 2020, [{**_linhas_2023()[0], "ano": 2020, "idDocumento": 77}])
    args = ["--db", str(db), "--raw", str(raw), "--gerar-manifesto", "--saida", str(tmp_path / "v.md")]
    assert verifica.main(args) == 0  # padrão: os anos ingeridos
    assert verifica.main([*args, "--anos-ceap", "2023,2024"]) == 0
    assert verifica.main([*args, "--anos-ceap", "2020,2024"]) == 1


def test_cli_anos_ceap_invalido_e_erro_claro(ambiente, tmp_path):
    db, raw = ambiente
    with pytest.raises(SystemExit):
        verifica.main(["--db", str(db), "--raw", str(raw), "--anos-ceap", "24"])


# --------------------------------------------------------------------------- manifesto
def test_sem_manifesto_vira_uma_linha_nao_verificado_e_nao_reprova(ambiente):
    db, raw = ambiente
    r = rodar(db, raw)
    [lin] = por(r, "manifesto")
    assert lin.status == "nao_verificado" and "--gerar-manifesto" in lin.detalhe
    assert "manifesto ausente" in lin.detalhe
    assert r.divergencias == 0 and r.nao_verificados == 1


def test_manifesto_existente_com_arquivo_fora_dele_continua_divergindo(ambiente):
    db, raw = ambiente
    rodar(db, raw, gerar_manifesto=True)
    (raw / "ceap" / "extra.json").write_text("{}", encoding="utf-8")
    r = rodar(db, raw)
    assert [(lin.status, lin.item) for lin in por(r, "manifesto")] == [("diverge", "ceap/extra.json")]
    assert r.divergencias == 1


def test_cli_sem_manifesto_sai_com_zero(ambiente, tmp_path):
    db, raw = ambiente
    assert verifica.main(["--db", str(db), "--raw", str(raw), "--saida", str(tmp_path / "v.md")]) == 0


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


# --------------------------------------------------------------------------- escolha do bruto da Câmara
def _copia_com_janela(raw, inicio, fim):
    origem = next((raw / "camara").glob("camara_2025-01-01_2025-03-31.json"))
    (raw / "camara" / f"camara_{inicio}_{fim}.json").write_text(
        origem.read_text("utf-8"), encoding="utf-8")


def test_escolhe_o_bruto_cuja_janela_cobre_as_votacoes_do_banco(ambiente):
    db, raw = ambiente  # votações de 2025-02-10
    _copia_com_janela(raw, "2025-04-01", "2025-06-30")  # último em ordem alfabética, mas outra janela
    r = rodar(db, raw, gerar_manifesto=True)
    assert r.avisos == []
    assert por(r, "votacoes") and all(lin.status == "ok" for lin in por(r, "votacoes"))
    assert r.divergencias == 0


def test_avisa_quando_mais_de_um_bruto_cobre_ou_nenhum_decide(ambiente):
    db, raw = ambiente
    _copia_com_janela(raw, "2024-01-01", "2025-12-31")  # também cobre 2025-02-10
    r = rodar(db, raw, gerar_manifesto=True)
    assert len(r.avisos) == 1 and "camara_" in r.avisos[0]
    assert "avisos" in verifica.renderizar_md(r).lower() or "aviso" in verifica.renderizar_md(r).lower()


def test_um_unico_bruto_nao_gera_aviso(ambiente):
    db, raw = ambiente
    assert rodar(db, raw, gerar_manifesto=True).avisos == []


def test_online_fecha_o_cliente_http_que_ele_mesmo_criou(ambiente, monkeypatch):
    db, raw = ambiente
    criados = []

    class Cliente(httpx.Client):
        def __init__(self, *a, **k):
            super().__init__(transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json={"dados": [{"tipoVoto": "Sim"}] * 99})))
            criados.append(self)

    monkeypatch.setattr(verifica.httpx, "Client", Cliente)
    rodar(db, raw, gerar_manifesto=True, online=True, amostra_online=1)
    assert len(criados) == 1 and criados[0].is_closed


def test_online_nao_fecha_o_cliente_que_o_chamador_passou(ambiente):
    db, raw = ambiente
    c = cliente(contagens_reais())
    rodar(db, raw, gerar_manifesto=True, online=True, cliente_http=c, amostra_online=1)
    assert not c.is_closed
