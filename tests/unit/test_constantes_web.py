"""As constantes da R01 que o web repete (texto da página /fontes) não podem divergir do YAML da regra."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
YAML_R01 = RAIZ / "knowledge" / "rules" / "R01_governismo.yaml"
VERIFICACAO_TS = RAIZ / "web" / "src" / "lib" / "verificacao.ts"


def _constante_ts(nome: str) -> float:
    """Valor numérico de `export const NOME = 0.95;` em verificacao.ts."""
    texto = VERIFICACAO_TS.read_text(encoding="utf-8")
    achado = re.search(rf"export\s+const\s+{nome}\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*;", texto)
    assert achado, f"constante exportada {nome} não encontrada em {VERIFICACAO_TS.name}"
    return float(achado.group(1))


def _r01() -> dict:
    return yaml.safe_load(YAML_R01.read_text(encoding="utf-8"))


def _penalidade_poucos_votos(regra: dict) -> tuple[float, int]:
    """(fator, limite) da penalidade `n_votacoes < N` da R01."""
    for p in regra["penalidades"]:
        achado = re.fullmatch(r"\s*n_votacoes\s*<\s*(\d+)\s*", str(p["se"]))
        if achado:
            return float(p["fator"]), int(achado.group(1))
    raise AssertionError("a R01 não tem mais a penalidade 'n_votacoes < N'")


def test_cf_base_do_web_igual_ao_yaml():
    assert _constante_ts("R01_CF_BASE") == _r01()["cf"]


def test_limiar_do_web_igual_ao_yaml():
    regra = _r01()
    achado = re.fullmatch(r"\s*taxa_governismo\s*>=\s*([0-9.]+)\s*", regra["se"])
    assert achado, "condição da R01 mudou de forma; ajuste este teste"
    assert float(achado.group(1)) == regra["parametros"]["limiar"]
    assert _constante_ts("R01_LIMIAR") == regra["parametros"]["limiar"]


def test_fator_da_penalidade_do_web_igual_ao_yaml():
    fator, _ = _penalidade_poucos_votos(_r01())
    assert _constante_ts("R01_FATOR_POUCOS_VOTOS") == fator


def test_limite_da_penalidade_do_web_igual_ao_yaml():
    _, limite = _penalidade_poucos_votos(_r01())
    assert _constante_ts("R01_VOTOS_PARA_SEM_PENALIDADE") == limite
