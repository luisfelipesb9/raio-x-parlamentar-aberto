"""Projeção de fatos/findings em grafo (graph/). Função pura: sem banco, sem rede."""
from __future__ import annotations

import time
from datetime import date

import pytest

from contracts import Evidence, Fact, Finding, Nivel
from graph import (
    RELACOES,
    afinidade_votos,
    backlinks,
    build_graph,
    project,
    subgrafo,
)


def F(tipo: str, chave: str, **at) -> Fact:
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def edges_of(edges, relacao):
    return [e for e in edges if e.relacao == relacao]


def edge(edges, origem, destino, relacao):
    achadas = [e for e in edges if (e.origem, e.destino, e.relacao) == (origem, destino, relacao)]
    assert len(achadas) == 1, f"esperava 1 aresta {origem}-{relacao}->{destino}, achei {achadas}"
    return achadas[0]


def ids(nodes):
    return {n.id for n in nodes}


@pytest.fixture
def base():
    """2 deputados, 1 partido em comum, 1 empresa paga por um deles."""
    return [
        F("deputado", "1", nome="Ana", partido="ABC", uf="MG"),
        F("deputado", "2", nome="Beto", partido="ABC", uf="SP"),
        F("despesa_ceap", "d1", deputado_id="1", cnpj="11111111000111", fornecedor="Posto Alfa",
          valor=100.0, categoria="combustivel", data="2025-01-10"),
        F("despesa_ceap", "d2", deputado_id="1", cnpj="11111111000111", fornecedor="Posto Alfa",
          valor=50.5, categoria="combustivel", data="2025-02-10"),
    ]


# --------------------------------------------------------------------------- nós e arestas simples
def test_deputado_vira_no_e_filiado_a_partido(base):
    nodes, edges = build_graph(base, [])
    por_id = {n.id: n for n in nodes}
    assert por_id["deputado:1"].tipo == "deputado"
    assert por_id["deputado:1"].rotulo == "Ana"
    assert por_id["deputado:1"].atributos["uf"] == "MG"
    assert por_id["partido:ABC"].tipo == "partido"
    e = edge(edges, "deputado:1", "partido:ABC", "filiado_a")
    assert e.peso == 1.0 and e.cf == 1.0
    assert e.evidencia_ids == ["deputado:1"]


def test_recebeu_soma_ceap_por_empresa_e_aponta_empresa_para_deputado(base):
    nodes, edges = build_graph(base, [])
    empresa = {n.id: n for n in nodes}["empresa:11111111000111"]
    assert empresa.tipo == "empresa"
    assert empresa.rotulo == "Posto Alfa"
    e = edge(edges, "empresa:11111111000111", "deputado:1", "recebeu")
    assert e.peso == 150.5
    assert e.evidencia_ids == ["despesa_ceap:d1", "despesa_ceap:d2"]


def test_despesa_sem_cnpj_nao_cria_empresa(base):
    base.append(F("despesa_ceap", "d9", deputado_id="1", cpf="12345678901", valor=10.0))
    base.append(F("despesa_ceap", "d10", deputado_id="1", valor=10.0))
    nodes, edges = build_graph(base, [])
    assert [n.id for n in nodes if n.tipo == "empresa"] == ["empresa:11111111000111"]
    assert len(edges_of(edges, "recebeu")) == 1


def test_estorno_negativo_entra_na_soma(base):
    base.append(F("despesa_ceap", "d3", deputado_id="1", cnpj="11111111000111", valor=-20.5))
    _, edges = build_graph(base, [])
    assert edge(edges, "empresa:11111111000111", "deputado:1", "recebeu").peso == 130.0


def test_autoria_gera_autor_de_e_relator_de(base):
    base += [
        F("proposicao", "p1", sigla_tipo="PL", numero="10", ano="2024", ementa="Dispõe sobre X"),
        F("autoria", "p1:1:autor", proposicao_id="p1", deputado_id="1", papel="autor"),
        F("autoria", "p1:2:coautor", proposicao_id="p1", deputado_id="2", papel="coautor"),
        F("autoria", "p1:2:relator", proposicao_id="p1", deputado_id="2", papel="relator"),
    ]
    nodes, edges = build_graph(base, [])
    prop = {n.id: n for n in nodes}["proposicao:p1"]
    assert prop.tipo == "proposicao"
    assert prop.rotulo == "PL 10/2024"
    assert prop.atributos["ementa"] == "Dispõe sobre X"
    edge(edges, "deputado:1", "proposicao:p1", "autor_de")
    edge(edges, "deputado:2", "proposicao:p1", "autor_de")  # coautor também é autor_de
    edge(edges, "deputado:2", "proposicao:p1", "relator_de")


def test_emendas_somam_valor_por_municipio_e_ignoram_sem_municipio(base):
    base += [
        F("emenda", "e1", deputado_id="1", ano="2024", valor_empenhado=1000.0, municipio_ibge="3106200"),
        F("emenda", "e2", deputado_id="1", ano="2025", valor_empenhado=500.0, municipio_ibge="3106200"),
        F("emenda", "e3", deputado_id="1", ano="2025", valor_empenhado=700.0),  # sem município
        F("emenda", "e4", autor_nome="Fulano", ano="2025", valor_empenhado=9.0,
          municipio_ibge="3550308"),  # autor não resolvido a deputado
    ]
    nodes, edges = build_graph(base, [])
    assert {n.id: n for n in nodes}["municipio:3106200"].tipo == "municipio"
    e = edge(edges, "deputado:1", "municipio:3106200", "enviou_emenda")
    assert e.peso == 1500.0
    assert e.evidencia_ids == ["emenda:e1", "emenda:e2"]
    assert len(edges_of(edges, "enviou_emenda")) == 1
    assert "municipio:3550308" not in ids(nodes)


# --------------------------------------------------------------------------- doações
def test_doou_resolve_candidatura_para_deputado_e_separa_pj_pf(base):
    base += [
        F("candidatura", "sq1", ano="2022", cpf="***", nome="Ana", cargo="DEPUTADO FEDERAL",
          uf="MG", partido="ABC", deputado_id="1"),
        F("candidatura", "sq9", ano="2022", nome="Zé", cargo="DEPUTADO FEDERAL", uf="MG",
          partido="XYZ"),  # não resolvida
        F("doacao", "r1", sq_candidato="sq1", doador_nome="Construtora Beta",
          doador_cpf_cnpj="22222222000122", valor=1000.0, tipo_doador="PJ"),
        F("doacao", "r2", sq_candidato="sq1", doador_nome="João da Silva",
          doador_cpf_cnpj="***123456**", valor=300.0, tipo_doador="PF"),
        F("doacao", "r3", sq_candidato="sq1", doador_nome="João da Silva",
          doador_cpf_cnpj="***123456**", valor=200.0, tipo_doador="PF"),
        F("doacao", "r4", sq_candidato="sq1", doador_nome="Ana", doador_cpf_cnpj="***",
          valor=50.0, tipo_doador="proprio"),
        F("doacao", "r5", sq_candidato="sq9", doador_nome="Outro", doador_cpf_cnpj="33333333000133",
          valor=70.0, tipo_doador="PJ"),
    ]
    nodes, edges = build_graph(base, [])
    por_id = {n.id: n for n in nodes}
    assert edge(edges, "empresa:22222222000122", "deputado:1", "doou").peso == 1000.0
    doacoes_pf = sorted((e for e in edges_of(edges, "doou") if e.origem.startswith("pessoa:")),
                        key=lambda e: e.peso)
    # CPF mascarado: cada doação é um nó próprio (não funde homônimos) e sem o nome
    assert [e.peso for e in doacoes_pf] == [200.0, 300.0]
    assert doacoes_pf[0].origem != doacoes_pf[1].origem
    assert [e.evidencia_ids for e in doacoes_pf] == [["doacao:r3"], ["doacao:r2"]]
    for e in doacoes_pf:
        assert por_id[e.origem].tipo == "pessoa"
        assert por_id[e.origem].rotulo == "Doador(a) pessoa física"
    assert len(edges_of(edges, "doou")) == 3  # 'proprio' e candidatura não resolvida ficam de fora
    assert "empresa:33333333000133" not in ids(nodes)
    assert not any("123456" in n.id or "123456" in str(n.atributos) for n in nodes)
    assert not any("João" in n.rotulo or "SILVA" in n.id.upper() or "Silva" in str(n.atributos)
                   for n in nodes)


def test_doacao_de_partido_so_liga_a_sigla_conhecida(base):
    base += [
        F("candidatura", "sq1", ano="2022", nome="Ana", cargo="DEPUTADO FEDERAL", uf="MG",
          partido="ABC", deputado_id="1"),
        F("doacao", "r1", sq_candidato="sq1", doador_nome="ABC", valor=900.0, tipo_doador="partido"),
        F("doacao", "r2", sq_candidato="sq1", doador_nome="DIRETORIO ESTADUAL QUALQUER",
          valor=10.0, tipo_doador="partido"),
    ]
    _, edges = build_graph(base, [])
    assert edge(edges, "partido:ABC", "deputado:1", "doou").peso == 900.0
    assert len(edges_of(edges, "doou")) == 1


# --------------------------------------------------------------------------- sanção e sócios
def test_empresa_sancionada_e_marcada_no_no(base):
    base += [
        F("sancao", "CEIS:1", cnpj="11111111000111", cadastro="CEIS", inicio="2024-01-01",
          orgao="CGU"),
        F("sancao", "CEIS:2", cnpj="99999999000199", cadastro="CEIS", inicio="2024-01-01"),
    ]
    nodes, _ = project(base, [], hoje=date(2025, 6, 1))
    por_id = {n.id: n for n in nodes}
    e = por_id["empresa:11111111000111"]
    assert e.atributos["sancionada"] is True
    assert e.atributos["sancao_vigente"] is True
    assert e.atributos["sancoes"][0]["cadastro"] == "CEIS"
    # empresa sancionada sem nenhuma ligação com deputado não entra (grafo não vira cadastro do CEIS)
    assert "empresa:99999999000199" not in por_id


def test_sancao_expirada_marca_mas_nao_e_vigente(base):
    base.append(F("sancao", "CEIS:1", cnpj="11111111000111", cadastro="CEIS", inicio="2023-01-01",
                  fim="2023-12-31"))
    nodes, _ = project(base, [], hoje=date(2025, 6, 1))
    e = {n.id: n for n in nodes}["empresa:11111111000111"]
    assert e.atributos["sancionada"] is True
    assert e.atributos["sancao_vigente"] is False


def test_empresa_sem_sancao_nao_tem_marca(base):
    nodes, _ = build_graph(base, [])
    e = {n.id: n for n in nodes}["empresa:11111111000111"]
    assert e.atributos.get("sancionada", False) is False


def test_socio_de_so_para_empresas_do_grafo_e_cf_cai_com_cpf_mascarado(base):
    base += [
        F("socio", "11111111000111:MARIA", cnpj="11111111000111", nome="Maria Souza",
          cpf_cnpj="***111222**", qualificacao="Sócio-Administrador"),
        F("socio", "11111111000111:PEDRO", cnpj="11111111000111", nome="Pedro Lima",
          cpf_cnpj="12345678901", qualificacao="Sócio"),
        F("socio", "55555555000155:JOSE", cnpj="55555555000155", nome="José",
          cpf_cnpj="***", qualificacao="Sócio"),  # empresa fora do grafo
    ]
    nodes, edges = build_graph(base, [])
    socios = edges_of(edges, "socio_de")
    assert sorted(e.cf for e in socios) == [0.4, 1.0]
    assert not any(e.origem.endswith("JOSE") for e in socios)
    assert not any("José" in n.rotulo for n in nodes)


def test_socio_mascarado_e_doador_homonimo_sao_dois_nos_sem_nome(base):
    """Nome igual + CPF mascarado NÃO funde nem expõe o nome (homônimo e LGPD)."""
    base += [
        F("candidatura", "sq1", ano="2022", nome="Ana", cargo="DEPUTADO FEDERAL", uf="MG",
          partido="ABC", deputado_id="1"),
        F("doacao", "r2", sq_candidato="sq1", doador_nome="MARIA SOUZA",
          doador_cpf_cnpj="***111222**", valor=300.0, tipo_doador="PF"),
        F("socio", "11111111000111:MARIA", cnpj="11111111000111", nome="Maria Sôuza",
          cpf_cnpj="***111222**", qualificacao="Sócio"),
    ]
    nodes, edges = build_graph(base, [])
    pessoas = [n for n in nodes if n.tipo == "pessoa"]
    assert len(pessoas) == 2
    doou = edges_of(edges, "doou")[0]
    socio = edges_of(edges, "socio_de")[0]
    assert doou.origem != socio.origem
    por_id = {n.id: n for n in nodes}
    assert por_id[socio.origem].rotulo == "Sócio(a) de Posto Alfa"
    assert por_id[doou.origem].rotulo == "Doador(a) pessoa física"
    for n in pessoas:
        assert "SOUZA" not in (n.id + n.rotulo + str(n.atributos)).upper()
        assert "SÔUZA" not in (n.id + n.rotulo + str(n.atributos)).upper()


def test_cpf_integro_igual_funde_doador_e_socio_sem_expor_o_cpf(base):
    base += [
        F("candidatura", "sq1", ano="2022", nome="Ana", cargo="DEPUTADO FEDERAL", uf="MG",
          partido="ABC", deputado_id="1"),
        F("doacao", "r2", sq_candidato="sq1", doador_nome="Maria Souza",
          doador_cpf_cnpj="12345678901", valor=300.0, tipo_doador="PF"),
        F("socio", "11111111000111:MARIA", cnpj="11111111000111", nome="Maria Souza",
          cpf_cnpj="123.456.789-01", qualificacao="Sócio"),
        F("doacao", "r3", sq_candidato="sq1", doador_nome="Maria Souza",
          doador_cpf_cnpj="99999999999", valor=10.0, tipo_doador="PF"),  # homônima, outro CPF
    ]
    nodes, edges = build_graph(base, [])
    doou = {e.origem: e for e in edges_of(edges, "doou")}
    socio = edges_of(edges, "socio_de")[0]
    assert socio.origem in doou  # mesmo CPF íntegro: um único nó pessoa
    assert socio.cf == 1.0
    assert len(doou) == 2  # a homônima com CPF diferente é outro nó
    assert len([n for n in nodes if n.tipo == "pessoa"]) == 2
    assert {n.rotulo for n in nodes if n.tipo == "pessoa"} == {"Maria Souza"}
    assert not any(d in str(n) for n in nodes for d in ("12345678901", "99999999999"))
    assert not any(d in str(e) for e in edges for d in ("12345678901", "99999999999"))


def test_id_da_pessoa_e_estavel_entre_execucoes_e_muda_com_o_sal(base):
    base.append(F("candidatura", "sq1", ano="2022", nome="Ana", uf="MG", partido="ABC",
                  cargo="DEPUTADO FEDERAL", deputado_id="1"))
    base.append(F("doacao", "r2", sq_candidato="sq1", doador_nome="Maria",
                  doador_cpf_cnpj="12345678901", valor=1.0, tipo_doador="PF"))
    a1 = {n.id for n in project(base, [])[0] if n.tipo == "pessoa"}
    a2 = {n.id for n in project(list(reversed(base)), [])[0] if n.tipo == "pessoa"}
    b = {n.id for n in project(base, [], sal_id="outro-sal")[0] if n.tipo == "pessoa"}
    assert a1 == a2 and a1 != b


# --------------------------------------------------------------------------- findings
def _finding(fid, dep, regra="R03", cf=0.9, **valores):
    return Finding(id=fid, deputado_id=dep, regra=regra, categoria="integridade",
                   conclusao="x", cf=cf, nivel=Nivel.from_cf(cf),
                   evidencias=[Evidence(tipo="despesa_ceap", id_oficial="d1")], valores=valores)


def test_findings_anotam_deputado_e_empresas_citadas(base):
    fs = [_finding("R03:1", "1", cnpjs=["11111111000111"]),
          _finding("R04:1", "1", regra="R04", cf=0.5)]
    nodes, _ = build_graph(base, fs)
    por_id = {n.id: n for n in nodes}
    dep = por_id["deputado:1"].atributos
    assert dep["n_findings"] == 2
    assert dep["cf_max"] == 0.9
    assert dep["nivel_max"] == "alta"
    assert por_id["deputado:2"].atributos["n_findings"] == 0
    assert por_id["empresa:11111111000111"].atributos["findings"] == ["R03:1"]


def test_finding_de_deputado_desconhecido_nao_quebra(base):
    nodes, _ = build_graph(base, [_finding("R03:77", "77", cnpjs=["00000000000000"])])
    assert "deputado:77" not in ids(nodes)


# --------------------------------------------------------------------------- votou_com
def _votos(dep: str, valores: list[str], prefixo="v") -> list[Fact]:
    return [F("voto", f"{prefixo}{i}:{dep}", votacao_id=f"{prefixo}{i}", deputado_id=dep, voto=v)
            for i, v in enumerate(valores)]


def _votacoes(n: int, prefixo="v", nominal=True) -> list[Fact]:
    return [F("votacao", f"{prefixo}{i}", nominal=nominal, orientacao_governo="Sim")
            for i in range(n)]


def test_votou_com_calcula_percentual_de_votos_iguais_e_cf_pelo_n_comum():
    fs = [F("deputado", d, nome=f"Dep {d}", partido="P", uf="MG") for d in ("1", "2")]
    fs += _votacoes(12)
    fs += _votos("1", ["Sim"] * 12)
    fs += _votos("2", ["Sim"] * 9 + ["Não"] * 3)  # 9 iguais de 12 = 75%
    _, edges = build_graph(fs, [])
    e = edge(edges, "deputado:1", "deputado:2", "votou_com")
    assert e.peso == 0.75
    assert e.cf == pytest.approx(12 / 30)
    assert len(e.evidencia_ids) == 0  # afinidade é agregada: não há 1 fato que a sustente


def test_votou_com_cf_satura_em_1_com_30_votacoes_comuns():
    fs = [F("deputado", d, nome=d, partido="P", uf="MG") for d in ("1", "2")]
    fs += _votacoes(45) + _votos("1", ["Sim"] * 45) + _votos("2", ["Sim"] * 45)
    _, edges = build_graph(fs, [])
    e = edge(edges, "deputado:1", "deputado:2", "votou_com")
    assert e.peso == 1.0 and e.cf == 1.0


def test_votou_com_ignora_votacao_simbolica_artigo17_e_votos_nao_comuns():
    fs = [F("deputado", d, nome=d, partido="P", uf="MG") for d in ("1", "2")]
    fs += _votacoes(6) + _votacoes(4, prefixo="s", nominal=False)
    fs += [F("votacao", "x0", nominal=True)]  # nominal onde 2 não votou
    fs += _votos("1", ["Sim"] * 6) + _votos("2", ["Sim"] * 6)
    fs += _votos("1", ["Sim"] * 4, prefixo="s") + _votos("2", ["Não"] * 4, prefixo="s")
    fs += [F("voto", "x0:1", votacao_id="x0", deputado_id="1", voto="Sim")]
    fs += [F("voto", "x0:2", votacao_id="x0", deputado_id="2", voto="Artigo 17")]
    _, edges = build_graph(fs, [])
    e = edge(edges, "deputado:1", "deputado:2", "votou_com")
    assert e.peso == 1.0  # simbólicas (discordam) e Art. 17 não contam
    assert e.cf == pytest.approx(6 / 30)


def test_votou_com_exige_minimo_de_votacoes_comuns():
    fs = [F("deputado", d, nome=d, partido="P", uf="MG") for d in ("1", "2")]
    fs += _votacoes(4) + _votos("1", ["Sim"] * 4) + _votos("2", ["Sim"] * 4)
    _, edges = build_graph(fs, [])
    assert edges_of(edges, "votou_com") == []
    _, edges = build_graph(fs, [], min_votacoes_comuns=4)
    assert len(edges_of(edges, "votou_com")) == 1


def test_votou_com_so_guarda_top_k_por_deputado():
    deps = [str(i) for i in range(1, 8)]
    fs = [F("deputado", d, nome=d, partido="P", uf="MG") for d in deps]
    fs += _votacoes(10)
    fs += _votos("1", ["Sim"] * 10)
    # deputado 2 é o mais parecido com 1, 7 o menos
    for i, d in enumerate(deps[1:]):
        fs += _votos(d, ["Sim"] * (10 - i) + ["Não"] * i)
    _, edges = build_graph(fs, [], votou_com_k=2)
    vizinhos_de_1 = {e.destino if e.origem == "deputado:1" else e.origem
                     for e in edges_of(edges, "votou_com") if "deputado:1" in (e.origem, e.destino)}
    assert vizinhos_de_1 == {"deputado:2", "deputado:3"}
    # sem arestas duplicadas (a-b e b-a)
    pares = [frozenset((e.origem, e.destino)) for e in edges_of(edges, "votou_com")]
    assert len(pares) == len(set(pares))


def test_afinidade_votos_direta_entre_dois_deputados():
    fs = [F("deputado", d, nome=d, partido="P", uf="MG") for d in ("1", "2")]
    fs += _votacoes(10) + _votos("1", ["Sim"] * 10) + _votos("2", ["Sim"] * 4 + ["Não"] * 6)
    a = afinidade_votos(fs, "1", "2")
    assert a is not None
    assert (a.n_votacoes_comuns, a.n_iguais) == (10, 4)
    assert a.afinidade == 0.4
    assert a.cf == pytest.approx(10 / 30)
    assert afinidade_votos(fs, "1", "999") is None  # sem votos comuns


def test_votou_com_escala_para_513_deputados_em_tempo_razoavel():
    import random
    rng = random.Random(7)
    deps = [str(i) for i in range(513)]
    fs = [F("deputado", d, nome=d, partido="P", uf="MG") for d in deps]
    fs += _votacoes(150)
    for d in deps:
        fs += _votos(d, [rng.choice(["Sim", "Não", "Abstenção"]) for _ in range(150)])
    t0 = time.perf_counter()
    nodes, edges = build_graph(fs, [], votou_com_k=5)
    dur = time.perf_counter() - t0
    vc = edges_of(edges, "votou_com")
    assert len(vc) <= 513 * 5  # nunca O(n²) arestas
    assert len([n for n in nodes if n.tipo == "deputado"]) == 513
    assert dur < 15, f"projeção levou {dur:.1f}s"


# --------------------------------------------------------------------------- centro / profundidade
@pytest.fixture
def rede():
    """dep1 -recebeu- emp A -recebeu- dep2 ; dep2 -emenda- mun ; ambos no partido ABC."""
    return [
        F("deputado", "1", nome="Ana", partido="ABC", uf="MG"),
        F("deputado", "2", nome="Beto", partido="ABC", uf="SP"),
        F("deputado", "3", nome="Carla", partido="XYZ", uf="SP"),
        F("despesa_ceap", "a", deputado_id="1", cnpj="11111111000111", fornecedor="A", valor=10.0),
        F("despesa_ceap", "b", deputado_id="2", cnpj="11111111000111", fornecedor="A", valor=20.0),
        F("despesa_ceap", "c", deputado_id="3", cnpj="33333333000133", fornecedor="C", valor=30.0),
        F("emenda", "e", deputado_id="2", ano="2024", valor_empenhado=5.0, municipio_ibge="3106200"),
    ]


def test_centro_profundidade_1_traz_so_vizinhos_diretos(rede):
    nodes, edges = build_graph(rede, [], centro="deputado:1", profundidade=1)
    assert ids(nodes) == {"deputado:1", "partido:ABC", "empresa:11111111000111"}
    assert all(e.origem in ids(nodes) and e.destino in ids(nodes) for e in edges)


def test_centro_profundidade_2_expande_e_profundidade_0_so_o_centro(rede):
    nodes2, _ = build_graph(rede, [], centro="deputado:1", profundidade=2)
    assert ids(nodes2) == {"deputado:1", "partido:ABC", "empresa:11111111000111", "deputado:2"}
    nodes0, edges0 = build_graph(rede, [], centro="deputado:1", profundidade=0)
    assert ids(nodes0) == {"deputado:1"} and edges0 == []


def test_centro_inexistente_levanta_keyerror(rede):
    with pytest.raises(KeyError):
        build_graph(rede, [], centro="deputado:999")


def test_profundidade_negativa_e_invalida(rede):
    with pytest.raises(ValueError):
        build_graph(rede, [], centro="deputado:1", profundidade=-1)


def test_sem_centro_devolve_grafo_completo(rede):
    nodes, _ = build_graph(rede, [])
    assert {"deputado:3", "municipio:3106200", "empresa:33333333000133"} <= ids(nodes)


def test_filtro_de_relacoes_restringe_a_travessia(rede):
    nodes, edges = subgrafo(*project(rede, []), "deputado:1", 2, relacoes={"recebeu"})[:2]
    assert ids(nodes) == {"deputado:1", "empresa:11111111000111", "deputado:2"}
    assert {e.relacao for e in edges} == {"recebeu"}


def test_relacao_desconhecida_levanta_valueerror(rede):
    with pytest.raises(ValueError):
        subgrafo(*project(rede, []), "deputado:1", 1, relacoes={"inventada"})
    assert "votou_com" in RELACOES


def test_limite_de_nos_trunca_e_sinaliza(rede):
    nodes, edges, truncado = subgrafo(*project(rede, []), "deputado:1", 2, max_nos=3)
    assert truncado is True
    assert len(nodes) == 3 and "deputado:1" in ids(nodes)
    assert all(e.origem in ids(nodes) and e.destino in ids(nodes) for e in edges)
    _, _, truncado = subgrafo(*project(rede, []), "deputado:1", 2, max_nos=100)
    assert truncado is False


def test_saida_e_deterministica(rede):
    a = build_graph(rede, [], centro="deputado:2", profundidade=2)
    b = build_graph(list(reversed(rede)), [], centro="deputado:2", profundidade=2)
    assert [n.id for n in a[0]] == [n.id for n in b[0]]
    assert [(e.origem, e.destino, e.relacao) for e in a[1]] == [
        (e.origem, e.destino, e.relacao) for e in b[1]]


# --------------------------------------------------------------------------- backlinks
def test_backlinks_respeitam_a_direcao_da_aresta(rede):
    """empresa --recebeu--> deputado: ninguém aponta para a empresa nesta rede."""
    nodes, edges = project(rede, [])
    assert backlinks("empresa:11111111000111", nodes, edges) == []


def test_backlinks_de_empresa_incluem_socios_e_doadores(rede):
    rede.append(F("socio", "s", cnpj="11111111000111", nome="Maria", cpf_cnpj="12345678901",
                  qualificacao="Sócio"))
    nodes, edges = project(rede, [])
    bl = backlinks("empresa:11111111000111", nodes, edges)
    assert [(b.no.tipo, b.no.rotulo, b.aresta.relacao) for b in bl] == [
        ("pessoa", "Maria", "socio_de")]


def test_backlinks_do_partido_sao_os_deputados_filiados(rede):
    nodes, edges = project(rede, [])
    bl = backlinks("partido:ABC", nodes, edges)
    assert [(b.no.id, b.aresta.relacao) for b in bl] == [
        ("deputado:1", "filiado_a"), ("deputado:2", "filiado_a")]
    assert all(b.no.tipo == "deputado" for b in bl)


def test_backlinks_do_deputado_incluem_empresas_que_o_receberam(rede):
    nodes, edges = project(rede, [])
    bl = backlinks("deputado:1", nodes, edges)
    assert [(b.no.id, b.aresta.relacao) for b in bl] == [("empresa:11111111000111", "recebeu")]


def test_backlinks_de_relacao_simetrica_valem_nos_dois_sentidos():
    fs = [F("deputado", d, nome=d, partido="P", uf="MG") for d in ("1", "2")]
    fs += _votacoes(8) + _votos("1", ["Sim"] * 8) + _votos("2", ["Sim"] * 8)
    nodes, edges = project(fs, [])
    assert [b.no.id for b in backlinks("deputado:1", nodes, edges) if b.aresta.relacao == "votou_com"] == ["deputado:2"]
    assert [b.no.id for b in backlinks("deputado:2", nodes, edges) if b.aresta.relacao == "votou_com"] == ["deputado:1"]


def test_backlinks_de_no_inexistente_levanta_keyerror(rede):
    nodes, edges = project(rede, [])
    with pytest.raises(KeyError):
        backlinks("deputado:999", nodes, edges)


def test_normaliza_nome_acompanha_a_do_motor():
    from engine.predicates.circuito import normaliza_nome as do_motor
    from graph import normaliza_nome
    for nome in ("  João  da Sílva ", "MARIA", "", None, "Zoë  Ñandú"):
        assert normaliza_nome(nome) == do_motor(nome)


# --------------------------------------------------------------------------- export de schemas
def test_export_schemas_gera_um_json_por_modelo_e_manifesto(tmp_path):
    import json

    from contracts import CONTRACT_VERSION
    from scripts.export_schemas import export

    escritos = export(tmp_path)
    nomes = {p.name for p in escritos}
    assert {"Finding.json", "Explanation.json", "GraphNode.json", "GraphEdge.json", "Fact.json",
            "Nivel.json", "PerfilDeputado.json", "GrafoResposta.json", "PerguntarResposta.json",
            "ComparacaoResposta.json", "PaginaDeputados.json", "Problem.json",
            "index.json"} <= nomes
    finding = json.loads((tmp_path / "Finding.json").read_text())
    assert finding["title"] == "Finding"
    assert {"id", "deputado_id", "cf", "nivel", "evidencias", "guardrails_aplicados"} <= set(
        finding["required"])  # modo serialização: campos com default também são obrigatórios
    assert json.loads((tmp_path / "Nivel.json").read_text())["enum"] == [
        "alta", "media", "indicio", "inconclusivo"]
    edge = json.loads((tmp_path / "GraphEdge.json").read_text())
    assert set(edge["properties"]) == {"origem", "destino", "relacao", "peso", "cf", "evidencia_ids"}
    manifesto = json.loads((tmp_path / "index.json").read_text())
    assert manifesto["contract_version"] == CONTRACT_VERSION
    assert "Finding" in manifesto["schemas"]


# --------------------------------------------------------------------------- CPF pseudonimizado (hmac:)
def _doador_e_socio(base, hash_doador: str, hash_socio: str):
    base = base + [
        F("candidatura", "sq1", ano="2022", nome="Ana", cargo="DEPUTADO FEDERAL", uf="MG",
          partido="ABC", deputado_id="1"),
        F("doacao", "r2", sq_candidato="sq1", doador_nome="Maria Souza",
          doador_cpf_cnpj=hash_doador, valor=300.0, tipo_doador="PF"),
        F("socio", "11111111000111:MARIA", cnpj="11111111000111", nome="Maria Souza",
          cpf_cnpj=hash_socio, qualificacao="Sócio"),
    ]
    return build_graph(base, [])


def test_hmac_igual_funde_doador_e_socio_sem_expor_o_hash(base):
    h = "hmac:9f8e7d6c5b4a39281706f5e4d3c2b1a0"
    nodes, edges = _doador_e_socio(base, h, h)
    pessoas = [n for n in nodes if n.tipo == "pessoa"]
    assert len(pessoas) == 1 and pessoas[0].rotulo == "Maria Souza"
    assert edges_of(edges, "doou")[0].origem == edges_of(edges, "socio_de")[0].origem
    assert edges_of(edges, "socio_de")[0].cf == 1.0
    assert "9f8e7d6c" not in str(nodes) + str(edges)


def test_hmac_diferente_nao_funde_mesmo_com_o_mesmo_nome(base):
    nodes, _ = _doador_e_socio(base, "hmac:aaaa1111aaaa1111", "hmac:bbbb2222bbbb2222")
    assert len([n for n in nodes if n.tipo == "pessoa"]) == 2


def test_hmac_so_com_digitos_nao_vira_falso_cpf_nem_cnpj(base):
    """Um hash cujo hex tem 11 (ou 14) dígitos decimais continua sendo só um identificador."""
    h11, h14 = "hmac:12345678901", "hmac:12345678901234"
    nodes, edges = _doador_e_socio(base, h11, h11)
    assert len([n for n in nodes if n.tipo == "pessoa"]) == 1
    assert "12345678901" not in str(nodes) + str(edges)
    # sócio com 14 dígitos no hash não é tratado como sócio PJ (não é pulado)
    nodes, edges = _doador_e_socio(base, h14, h14)
    assert len(edges_of(edges, "socio_de")) == 1
    # e um hash não pode virar CNPJ de doador PJ
    base = [*base, F("candidatura", "sq1", ano="2022", nome="Ana", cargo="DEPUTADO FEDERAL",
                     uf="MG", partido="ABC", deputado_id="1"),
            F("doacao", "r9", sq_candidato="sq1", doador_nome="X", doador_cpf_cnpj=h14,
              valor=1.0, tipo_doador="PJ")]
    nodes, _ = build_graph(base, [])
    assert not any(n.id == "empresa:12345678901234" for n in nodes)
