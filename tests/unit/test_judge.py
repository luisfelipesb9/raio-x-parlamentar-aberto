"""engine/judge.py (ADR-008): só o NullJudge existe; determinístico, sem rede, sem chave de API."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine import judge
from engine.judge import Decisao, Judge, NullJudge, get_judge
from engine.rules import load_rules

OBJETIVOS = ["alinhado_governo", "risco_integridade", "concentracao_eleitoral_emendas",
             "pontuacao_producao_legislativa", "merece_atencao_fiscalizacao"]


def test_as_cinco_opcoes_de_teste_sao_os_objetivos_reais_do_perguntar():
    reais = sorted({r.conclui for r in load_rules() if r.tipo == "inferencia" and r.conclui})
    assert reais == sorted(OBJETIVOS)


@pytest.mark.parametrize("pergunta,esperado", [
    ("O deputado vota com o governo?", "alinhado_governo"),
    ("ele é governista?", "alinhado_governo"),
    ("Há risco de integridade nos gastos com fornecedor sancionado?", "risco_integridade"),
    ("As emendas se concentram em poucos municípios?", "concentracao_eleitoral_emendas"),
    ("Qual a produção legislativa? Quantos projetos de autoria dele?", "pontuacao_producao_legislativa"),
    ("Merece atenção da fiscalização?", "merece_atencao_fiscalizacao"),
    ("EMENDAS PIX", "concentracao_eleitoral_emendas"),  # caixa e acento não importam
    ("Producao legislativa", "pontuacao_producao_legislativa"),
])
def test_null_judge_casa_palavras_chave_com_o_objetivo(pergunta, esperado):
    d = NullJudge().decidir(pergunta, OBJETIVOS)
    assert d.opcao == esperado
    assert 0 < d.probabilidade <= 1 and 0 < d.confianca <= 1


@pytest.mark.parametrize("pergunta", ["", "   ", "qual a cor do céu?", "bom dia"])
def test_sem_palavra_conhecida_nao_decide(pergunta):
    assert NullJudge().decidir(pergunta, OBJETIVOS) == Decisao(None, 0.0, 0.0)


def test_empate_nao_decide():
    # uma palavra de cada objetivo: não há vencedor
    d = NullJudge().decidir("governo e emendas", OBJETIVOS)
    assert d.opcao is None and d.confianca == 0.0


def test_so_escolhe_dentre_as_opcoes_oferecidas():
    d = NullJudge().decidir("vota com o governo e tem emendas", ["concentracao_eleitoral_emendas"])
    assert d.opcao == "concentracao_eleitoral_emendas"
    assert NullJudge().decidir("vota com o governo", ["risco_integridade"]).opcao is None
    assert NullJudge().decidir("vota com o governo", []).opcao is None


def test_opcao_desconhecida_sem_palavras_nao_decide():
    assert NullJudge().decidir("qualquer coisa", ["opcao_nova"]).opcao is None


def test_e_deterministico():
    j = NullJudge()
    assert [j.decidir("risco de integridade", OBJETIVOS) for _ in range(3)] == \
        [j.decidir("risco de integridade", OBJETIVOS)] * 3


def test_null_judge_cumpre_o_protocolo():
    assert isinstance(NullJudge(), Judge)


# --------------------------------------------------------------------------- fábrica
def test_padrao_e_null(monkeypatch):
    monkeypatch.delenv("RAIO_X_JUDGE", raising=False)
    assert isinstance(get_judge(), NullJudge)


@pytest.mark.parametrize("valor", ["null", "NULL", " null ", ""])
def test_null_explicito_ou_vazio(monkeypatch, valor):
    monkeypatch.setenv("RAIO_X_JUDGE", valor)
    assert isinstance(get_judge(), NullJudge)


def test_jev_ainda_nao_esta_implementado_e_o_erro_e_claro(monkeypatch):
    monkeypatch.setenv("RAIO_X_JUDGE", "jev")
    with pytest.raises(NotImplementedError, match="jev.*não implementado"):
        get_judge()


def test_valor_desconhecido_e_erro(monkeypatch):
    monkeypatch.setenv("RAIO_X_JUDGE", "outro")
    with pytest.raises(ValueError, match="RAIO_X_JUDGE"):
        get_judge()


def test_fabrica_aceita_ambiente_explicito():
    assert isinstance(get_judge({"RAIO_X_JUDGE": "null"}), NullJudge)
    with pytest.raises(NotImplementedError):
        get_judge({"RAIO_X_JUDGE": "jev"})


def test_modulo_nao_tem_rede_nem_chave_de_api():
    fonte = Path(judge.__file__).read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    importados = {n.module.split(".")[0] for n in ast.walk(arvore) if isinstance(n, ast.ImportFrom) and n.module} | \
                 {a.name.split(".")[0] for n in ast.walk(arvore) if isinstance(n, ast.Import) for a in n.names}
    assert not importados & {"httpx", "requests", "urllib", "socket", "aiohttp", "api", "web"}
    assert "API_KEY" not in fonte.upper().replace("CHAVE DE API", "")
