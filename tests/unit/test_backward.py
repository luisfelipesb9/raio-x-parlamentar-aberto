"""Encadeamento regressivo com sub-objetivos, detecção de ciclo e trilha."""
import pytest
from pydantic import ValidationError

from contracts import Fact
from engine import backward
from engine.factbase import FactBase
from engine.rules import Rule, load_rules


def F(tipo, chave, /, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def composta(id_, conclui, requer, cf=0.8):
    return Rule(id=id_, nome=id_, conclui=conclui, requer=requer, cf=cf)


@pytest.fixture
def ceap_dep7(fatos_ceap):
    return FactBase(fatos_ceap)


def test_r09_composta_prova_atencao_via_subobjetivo_risco_integridade(ceap_dep7):
    ans = backward.prove("merece_atencao_fiscalizacao", "7", ceap_dep7, load_rules())
    assert ans.cf == 0.4  # R09 0.8 × risco_integridade 0.5 (só R04 dispara para o dep 7)
    assert "R09" in ans.regras_usadas and "R04" in ans.regras_usadas


def test_cf_do_subobjetivo_e_mycin_entre_regras_e_composta_usa_o_minimo():
    # R03 (0.9) e R04 (cf_dep3) combinados; composta multiplica pelo mínimo dos sub-objetivos
    regras = [composta("RX", "alvo", ["a", "b"], cf=0.5),
              Rule(id="A1", nome="a1", conclui="a", predicado="fornecedor_sancionado", cf=0.9),
              Rule(id="B1", nome="b1", conclui="b", predicado="outlier_ceap", cf=0.5,
                   parametros={"minimo_deputados": 5}, se="z_max > 3.5")]
    fs = []
    for d in range(1, 8):
        fs.append(F("despesa_ceap", f"n{d}", deputado_id=str(d), cnpj=f"0000000000000{d}",
                    valor=1000 + d * 10, categoria="c", data="2025-02-10"))
    fs.append(F("despesa_ceap", "n99", deputado_id="7", cnpj="00000000000007", valor=50000,
                categoria="c", data="2025-02-11"))
    fs.append(F("sancao", "s1", cnpj="00000000000007", cadastro="CEIS", inicio="2025-01-01",
                fim=None))
    ans = backward.prove("alvo", "7", FactBase(fs), regras)
    assert backward.prove("a", "7", FactBase(fs), regras).cf == 0.9
    assert backward.prove("b", "7", FactBase(fs), regras).cf == 0.5
    assert ans.cf == 0.25  # 0.5 × min(0.9, 0.5)


def test_subobjetivo_sem_prova_derruba_a_composta(fatos_ceap):
    # dep 1 não é outlier nem tem sanção: risco_integridade = 0 => composta = 0
    ans = backward.prove("merece_atencao_fiscalizacao", "1", FactBase(fatos_ceap), load_rules())
    assert ans.cf == 0.0 and ans.regras_usadas == []


def test_trilha_mostra_arvore_de_prova(ceap_dep7):
    ans = backward.prove("merece_atencao_fiscalizacao", "7", ceap_dep7, load_rules())
    objs = [(p.profundidade, p.objetivo, p.regra) for p in ans.trilha]
    assert objs[0] == (0, "merece_atencao_fiscalizacao", "R09")
    assert (1, "risco_integridade", "R04") in objs


def test_ciclo_nao_trava_e_e_registrado():
    regras = [composta("RA", "a", ["b"]), composta("RB", "b", ["a"])]
    ans = backward.prove("a", "1", FactBase([]), regras)
    assert ans.cf == 0.0
    assert any("ciclo" in p.nota for p in ans.trilha)


def test_ciclo_nao_impede_outro_caminho_valido(fatos_ceap):
    regras = [composta("RA", "risco_integridade", ["risco_integridade"]),  # auto-referência
              *[r for r in load_rules() if r.id in ("R04",)]]
    ans = backward.prove("risco_integridade", "7", FactBase(fatos_ceap), regras)
    assert ans.cf > 0 and "R04" in ans.regras_usadas
    assert any("ciclo" in p.nota for p in ans.trilha)


def test_objetivo_sem_regra_devolve_zero_e_trilha_explicativa():
    ans = backward.prove("inexistente", "1", FactBase([]), [])
    assert ans.cf == 0.0 and "sem regra" in ans.trilha[0].nota


def test_rule_composta_nao_pode_ter_predicado_e_requer_ao_mesmo_tempo():
    with pytest.raises(ValidationError):
        Rule(id="RZ", nome="z", conclui="z", requer=["x"], predicado="outlier_ceap")
    with pytest.raises(ValidationError):
        Rule(id="RZ", nome="z", conclui="z")  # nem predicado nem requer


def test_guardrails_continuam_valendo_no_regressivo(fatos_votacao):
    ans = backward.prove("alinhado_governo", "2", FactBase(fatos_votacao), load_rules())
    assert ans.cf == 0.0  # dep 2: 50% nominal; o voto simbólico não pode inflar a taxa


def test_mycin_entre_duas_regras_do_mesmo_objetivo(fatos_ceap):
    fs = fatos_ceap + [F("sancao", "ceis7", cnpj="00000000000007", cadastro="CEIS",
                         inicio="2025-01-01", fim=None)]
    ans = backward.prove("risco_integridade", "7", FactBase(fs), load_rules())
    assert ans.regras_usadas == ["R03", "R04"]
    assert ans.cf == 0.95  # MYCIN: 0.9 + 0.5·(1−0.9)


def test_composta_rejeita_se_e_penalidades():
    with pytest.raises(ValidationError):
        Rule(id="RZ", nome="z", conclui="z", requer=["x"], se="x > 1")
    with pytest.raises(ValidationError):
        Rule(id="RZ", nome="z", conclui="z", requer=["x"],
             penalidades=[{"se": "x > 1", "fator": 0.5, "motivo": "m"}])


def test_resultado_ja_calculado_e_equivalente_e_evita_novo_forward(ceap_dep7, monkeypatch):
    from engine import forward
    regras = load_rules()
    esperado = backward.prove("merece_atencao_fiscalizacao", "7", FactBase(ceap_dep7.of(
        "despesa_ceap")), regras)
    res = forward.run(ceap_dep7, regras)  # roda UMA vez, com todas as regras

    def proibido(*a, **k):
        raise AssertionError("forward.run não deveria ser chamado")

    monkeypatch.setattr(backward.forward, "run", proibido)
    ans = backward.prove("merece_atencao_fiscalizacao", "7", ceap_dep7, regras, resultado=res)
    assert (ans.cf, ans.regras_usadas, ans.finding_ids) == \
        (esperado.cf, esperado.regras_usadas, esperado.finding_ids)
    assert [(p.objetivo, p.regra, p.cf) for p in ans.trilha] == \
        [(p.objetivo, p.regra, p.cf) for p in esperado.trilha]
    assert ans.cf == 0.4
