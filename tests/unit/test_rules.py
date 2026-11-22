import pytest

from engine import backward, forward
from engine.factbase import FactBase
from engine.rules import load_rules
from engine.safe_expr import evaluate


def run(fs):
    return forward.run(FactBase(fs), load_rules())


def test_base_de_conhecimento_carrega():
    ids = [r.id for r in load_rules()]
    assert ids[0] == "R02"  # guardrail roda primeiro
    assert set(ids) == {"R01", "R02", "R03", "R04"}


def test_r01_governismo_positivo_e_negativo(fatos_votacao):
    res = run(fatos_votacao)
    gov = {f.deputado_id: f for f in res.findings if f.regra == "R01"}
    assert "1" in gov and gov["1"].valores["taxa_pct"] == 100
    assert "2" not in gov  # 50% < 70%
    assert gov["1"].cf == round(0.95 * 0.7, 3)  # penalidade poucas votações


def test_r02_guardrail_simbolica_nao_vira_voto(fatos_votacao):
    res = run(fatos_votacao)
    assert "R02" in res.guardrail_log
    for f in res.findings:
        assert all(e.id_oficial != "s1" for e in f.evidencias)


def test_r03_fornecedor_sancionado(fatos_ceap):
    res = run(fatos_ceap)
    hits = {f.deputado_id for f in res.findings if f.regra == "R03"}
    assert hits == {"3"}  # dep 4: sanção já expirada


def test_r04_outlier(fatos_ceap):
    res = run(fatos_ceap)
    out = [f for f in res.findings if f.regra == "R04"]
    assert [f.deputado_id for f in out] == ["7"]
    assert "combustivel" in out[0].conclusao


def test_explicacao_tem_trilha(fatos_ceap):
    res = run(fatos_ceap)
    f = next(f for f in res.findings if f.regra == "R03")
    ex = res.explanations[f.id]
    assert ex.como[-1].regra == "R03" and ex.por_que and ex.limitacoes


def test_backward_prova_objetivo(fatos_ceap):
    ans = backward.prove("risco_integridade", "7", FactBase(fatos_ceap), load_rules())
    assert ans.regras_usadas == ["R04"] and ans.cf > 0


def test_safe_expr_bloqueia_codigo():
    with pytest.raises(ValueError):
        evaluate("__import__('os')", {})
