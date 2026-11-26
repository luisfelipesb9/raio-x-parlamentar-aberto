"""Diagnóstico do resultado inconclusivo no encadeamento regressivo (ADR-007, Diagnostico).

Cobre a R01 (alinhado_governo): votos de menos, taxa abaixo do limiar e "nenhuma regra se aplica".
O diagnóstico só descreve; nunca muda o CF nem a decisão de nenhuma regra.
"""
from __future__ import annotations

import pytest

from contracts import Fact
from engine import backward
from engine.factbase import FactBase
from engine.rules import load_rules


def F(tipo, chave, /, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def votos(dep: str, n_sim: int, n_nao: int, *, prefixo: str = "v", orientacao: str = "Sim"):
    """`n_sim` votos iguais à orientação do governo e `n_nao` contrários, em votações nominais."""
    contra = "Não" if orientacao == "Sim" else "Sim"
    fs = []
    for i in range(n_sim + n_nao):
        vid = f"{prefixo}{i}"
        fs.append(F("votacao", vid, nominal=True, orientacao_governo=orientacao))
        fs.append(F("voto", f"{vid}:{dep}", votacao_id=vid, deputado_id=dep,
                    voto=orientacao if i < n_sim else contra))
    return fs


def prova_r01(fatos, dep):
    return backward.prove("alinhado_governo", dep, FactBase(fatos), load_rules())


def passo_r01(ans):
    return next(p for p in ans.trilha if p.regra == "R01")


# --------------------------------------------------------------------------- R01
def test_sem_nenhum_voto_e_dados_insuficientes_sem_taxa():
    ans = prova_r01(votos("1", 12, 0) + [F("deputado", "2", nome="Sem voto")], "2")
    d = passo_r01(ans).diagnostico
    assert d is not None and d.motivo == "dados_insuficientes"
    assert d.detalhes == {"n_votos_validos": 0, "minimo_votos": 10}


def test_nove_votos_validos_e_dados_insuficientes_com_taxa_calculada():
    ans = prova_r01(votos("1", 9, 0), "1")  # 100% de 9 votos: ainda abaixo do mínimo (10)
    d = passo_r01(ans).diagnostico
    assert d.motivo == "dados_insuficientes"
    assert d.detalhes == {"n_votos_validos": 9, "minimo_votos": 10, "taxa": 1.0}
    assert ans.cf == 0.0


def test_abstencao_e_votacao_sem_orientacao_nao_contam_como_voto_valido():
    fs = votos("1", 9, 0)
    fs += [F("votacao", "x1", nominal=True, orientacao_governo="Sim"),
           F("voto", "x1:1", votacao_id="x1", deputado_id="1", voto="Abstenção"),
           F("votacao", "x2", nominal=True, orientacao_governo=None),
           F("voto", "x2:1", votacao_id="x2", deputado_id="1", voto="Sim"),
           F("votacao", "x3", nominal=True, orientacao_governo="Liberado"),
           F("voto", "x3:1", votacao_id="x3", deputado_id="1", voto="Sim")]
    d = passo_r01(prova_r01(fs, "1")).diagnostico
    assert d.motivo == "dados_insuficientes" and d.detalhes["n_votos_validos"] == 9


def test_votacao_simbolica_nao_conta_para_o_diagnostico():
    fs = votos("1", 9, 0)  # guardrail R02 descarta o voto de votação simbólica
    fs += [F("votacao", "s1", nominal=False, orientacao_governo="Sim"),
           F("voto", "s1:1", votacao_id="s1", deputado_id="1", voto="Sim")]
    d = passo_r01(prova_r01(fs, "1")).diagnostico
    assert d.motivo == "dados_insuficientes" and d.detalhes["n_votos_validos"] == 9


def test_votos_suficientes_e_taxa_baixa_e_abaixo_do_limiar():
    ans = prova_r01(votos("1", 9, 8), "1")  # 9/17 = 0,529
    d = passo_r01(ans).diagnostico
    assert d.motivo == "abaixo_do_limiar"
    assert d.detalhes == {"n_votos_validos": 17, "minimo_votos": 10, "taxa": 0.529,
                          "limiar": 0.7}
    assert ans.cf == 0.0


def test_exatamente_no_minimo_de_votos_ja_e_abaixo_do_limiar_e_nao_insuficiente():
    d = passo_r01(prova_r01(votos("1", 5, 5), "1")).diagnostico  # 10 votos, taxa 0,5
    assert d.motivo == "abaixo_do_limiar" and d.detalhes["n_votos_validos"] == 10


def test_quando_a_regra_dispara_nao_ha_diagnostico():
    ans = prova_r01(votos("1", 12, 0), "1")
    passo = passo_r01(ans)
    assert passo.cf > 0 and passo.diagnostico is None


def test_diagnostico_nao_muda_cf_nem_findings():
    fs = votos("1", 9, 8) + votos("2", 12, 0, prefixo="w")
    inconclusivo, dispara = prova_r01(fs, "1"), prova_r01(fs, "2")
    assert (inconclusivo.cf, inconclusivo.finding_ids) == (0.0, [])
    assert (dispara.cf, dispara.finding_ids) == (0.665, ["R01:2"])  # 0.95 x 0.7 (12 < 30 votos)


# --------------------------------------------------------------------------- outras regras
def test_objetivo_sem_regra_e_sem_regra_aplicavel():
    ans = backward.prove("inexistente", "1", FactBase([]), [])
    d = ans.trilha[0].diagnostico
    assert d is not None and d.motivo == "sem_regra_aplicavel" and d.detalhes == {}


def test_regra_sem_diagnosticador_que_nao_disparou_fica_sem_diagnostico_e_com_a_nota():
    ans = backward.prove("risco_integridade", "1", FactBase([F("deputado", "1")]), load_rules())
    assert ans.cf == 0.0
    passos = [p for p in ans.trilha if p.regra is not None]
    assert passos and all(p.cf == 0 for p in passos)
    assert all(p.diagnostico is None for p in passos)
    assert {p.nota for p in passos} == {"condições não satisfeitas"}


def test_regra_composta_mantem_a_nota_de_sub_objetivos_e_diagnostico_none():
    ans = backward.prove("merece_atencao_fiscalizacao", "1", FactBase([F("deputado", "1")]),
                         load_rules())
    r09 = next(p for p in ans.trilha if p.regra == "R09")
    assert r09.cf == 0.0 and r09.diagnostico is None
    assert r09.nota == "sub-objetivos: risco_integridade=0.0"


def test_ciclo_fica_sem_diagnostico_e_mantem_a_nota():
    from engine.rules import Rule
    regras = [Rule(id="RA", nome="a", conclui="a", requer=["b"], cf=0.8),
              Rule(id="RB", nome="b", conclui="b", requer=["a"], cf=0.8)]
    ans = backward.prove("a", "1", FactBase([]), regras)
    ciclo = next(p for p in ans.trilha if "ciclo" in p.nota)
    assert ciclo.diagnostico is None
    assert ciclo.nota == "ciclo detectado: a -> b -> a"


def test_taxa_logo_abaixo_do_limiar_nao_e_arredondada_para_cima():
    """B2: 0,6996 não pode virar 0,7 antes de comparar com o limiar (0,7)."""
    from engine.predicates.core import diagnostico_governismo
    fs = votos("1", 6996, 3004)  # 6996/10000 = 0,6996 -> abaixo de 0,7
    d = diagnostico_governismo(FactBase(fs), {"minimo_votacoes": 10, "limiar": 0.7}, "1")
    assert d is not None and d.motivo == "abaixo_do_limiar"
    assert d.detalhes["taxa"] == 0.7  # só a exibição é arredondada
    assert d.detalhes["limiar"] == 0.7


def test_taxa_exatamente_no_limiar_nao_tem_diagnostico():
    from engine.predicates.core import diagnostico_governismo
    d = diagnostico_governismo(FactBase(votos("1", 7, 3)), {"minimo_votacoes": 10, "limiar": 0.7}, "1")
    assert d is None


def test_passo_com_cf_positivo_nunca_tem_diagnostico():
    fs = [F("despesa_ceap", f"n{d}", deputado_id=str(d), cnpj=f"0000000000000{d}",
            valor=1000 + d * 10, categoria="c", data="2025-02-10") for d in range(1, 8)]
    fs.append(F("despesa_ceap", "n99", deputado_id="7", cnpj="00000000000007", valor=50000,
                categoria="c", data="2025-02-11"))
    ans = backward.prove("merece_atencao_fiscalizacao", "7", FactBase(fs), load_rules())
    assert ans.cf == 0.4
    assert all(p.diagnostico is None for p in ans.trilha if p.cf > 0)


def test_nota_legada_continua_igual():
    """O web compara a nota em texto (Perguntar.tsx); o diagnóstico é um campo a mais."""
    passo = passo_r01(prova_r01(votos("1", 9, 8), "1"))
    assert passo.nota == "condições não satisfeitas"


# --------------------------------------------------------------------------- consistência da regra
def test_limiar_do_diagnostico_e_o_mesmo_da_condicao_da_r01():
    r01 = next(r for r in load_rules() if r.id == "R01")
    assert r01.se == f"taxa_governismo >= {r01.parametros['limiar']}"
    assert r01.parametros["minimo_votacoes"] == 10


@pytest.mark.parametrize("n_sim,n_nao,motivo", [(0, 0, "dados_insuficientes"),
                                                (4, 5, "dados_insuficientes"),
                                                (4, 6, "abaixo_do_limiar"),
                                                (6, 4, "abaixo_do_limiar")])
def test_fronteiras_do_motivo(n_sim, n_nao, motivo):
    fs = votos("1", n_sim, n_nao) + [F("deputado", "1", nome="x")]
    assert passo_r01(prova_r01(fs, "1")).diagnostico.motivo == motivo
