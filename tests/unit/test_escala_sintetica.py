"""scripts/escala_sintetica.py: replica a amostra com chaves e ids distintos (dado SINTÉTICO, só para medir escala)."""
from __future__ import annotations

from collections import Counter

import pytest

from repo.store import Store
from scripts import escala_sintetica as esc
from scripts import seed_demo


@pytest.fixture(scope="module")
def base():
    return seed_demo.montar_fatos()  # 6 deputados fictícios, todos os tipos de fato


def _ids(fatos, tipo):
    return {f.chave for f in fatos if f.tipo == tipo}


def test_replica_ate_o_numero_exato_de_deputados(base):
    fatos = esc.replicar(base, copias=3.5)  # 6 x 3,5 = 21 deputados
    assert len(_ids(fatos, "deputado")) == 21


def test_copia_inteira_mantem_o_original_sem_mexer(base):
    fatos = esc.replicar(base, copias=2)
    originais = {(f.tipo, f.chave): f for f in base}
    assert all(originais[(f.tipo, f.chave)] == f for f in fatos if (f.tipo, f.chave) in originais)
    assert len(fatos) > len(base)


def test_chaves_unicas_por_tipo(base):
    fatos = esc.replicar(base, copias=3.5)
    repetidas = [k for k, n in Counter((f.tipo, f.chave) for f in fatos).items() if n > 1]
    assert repetidas == []


def test_referencias_continuam_resolvendo_dentro_do_conjunto(base):
    fatos = esc.replicar(base, copias=3.5)
    deps, votacoes = _ids(fatos, "deputado"), _ids(fatos, "votacao")
    sq = _ids(fatos, "candidatura")
    for f in fatos:
        if f.tipo in ("voto", "despesa_ceap", "emenda", "autoria"):
            assert f.atributos["deputado_id"] in deps, f
        if f.tipo == "voto":
            assert f.atributos["votacao_id"] in votacoes
        if f.tipo in ("doacao", "votos_municipio"):
            assert f.atributos["sq_candidato"] in sq, f
        if f.tipo == "candidatura":
            assert f.atributos["deputado_id"] in deps


def test_tipos_compartilhados_nao_se_repetem_e_os_por_deputado_crescem(base):
    por_tipo_base, por_tipo = Counter(f.tipo for f in base), Counter(
        f.tipo for f in esc.replicar(base, copias=4))
    for tipo in esc.COMPARTILHADOS:  # votações, proposições e PEP
        assert por_tipo[tipo] == por_tipo_base[tipo]
    for tipo in ("deputado", "voto", "despesa_ceap"):
        assert por_tipo[tipo] == 4 * por_tipo_base[tipo]


def test_replicas_sao_rotuladas_como_sinteticas_e_o_original_nao(base):
    fatos = esc.replicar(base, copias=2)
    nomes = {f.chave: f.atributos["nome"] for f in fatos if f.tipo == "deputado"}
    sinteticos = [n for n in nomes.values() if esc.ROTULO in n]
    assert len(sinteticos) == 6 and len(nomes) == 12
    assert not any(esc.ROTULO in f.atributos["nome"] for f in base if f.tipo == "deputado")


def test_links_sao_replicados_com_as_mesmas_chaves_dos_fatos(base):
    from repo.links import EntityLink
    fatos = esc.replicar(base, copias=2)
    dep0 = next(f for f in base if f.tipo == "deputado").chave
    links = esc.replicar_links([EntityLink("candidatura:x", f"deputado:{dep0}", "cpf", 1.0)], 2)
    assert len(links) == 2 and links[0].destino == f"deputado:{dep0}"
    assert links[1].destino.removeprefix("deputado:") in _ids(fatos, "deputado") - _ids(base, "deputado")


def test_copias_invalidas_sao_recusadas(base):
    for ruim in (0, -1, 0.5):
        with pytest.raises(ValueError, match="copias"):
            esc.replicar(base, copias=ruim)


def test_gerar_origem_grava_fatos_findings_e_rotulo_nos_logs(base, tmp_path):
    logs: list[str] = []
    destino = tmp_path / "sint.duckdb"
    resumo = esc.gerar_origem(base, [], destino, copias=2, log=logs.append)
    s = Store(destino, read_only=True)
    assert s.contagem_por_tipo()["deputado"] == 12 and resumo["deputados"] == 12
    assert len(s.load_findings()) == resumo["findings"] > 0
    s.con.close()
    assert logs and all(linha.startswith("SINTÉTICO") for linha in logs)



# ---------- cada réplica tem as suas empresas (pior caso para o grafo: nada de nó compartilhado) ----------
def test_empresa_socio_e_sancao_sao_replicados_com_cnpj_novo(base):
    por_base, fatos = Counter(f.tipo for f in base), esc.replicar(base, copias=3)
    por_tipo = Counter(f.tipo for f in fatos)
    for tipo in ("empresa", "sancao", "socio"):
        assert por_tipo[tipo] == 3 * por_base[tipo], tipo
    cnpjs = lambda fs: {f.atributos["cnpj"] for f in fs if f.tipo == "despesa_ceap" and f.atributos.get("cnpj")}
    assert len(cnpjs(fatos)) == 3 * len(cnpjs(base))
    sancionados = {f.atributos["cnpj"] for f in fatos if f.tipo == "sancao"}
    assert len(sancionados) == 3 * len({f.atributos["cnpj"] for f in base if f.tipo == "sancao"})


def test_replica_parcial_leva_so_parte_das_empresas(base):
    inteiro = Counter(f.tipo for f in esc.replicar(base, copias=3))
    parcial = Counter(f.tipo for f in esc.replicar(base, copias=2.5))
    assert Counter(f.tipo for f in base)["empresa"] * 2 < parcial["empresa"] < inteiro["empresa"]


def test_links_acompanham_o_cnpj_novo_das_empresas():
    from repo.links import EntityLink
    (_, novo) = esc.replicar_links([EntityLink("despesa_ceap:d1", "empresa:11222333000181", "cnpj", 1.0)], 2)
    assert novo.origem == "despesa_ceap:d1~1" and novo.destino == "empresa:11222333010181"
