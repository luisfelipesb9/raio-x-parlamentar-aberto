"""Trava a configuração de deploy da Vercel.

Sem `framework`, um projeto novo cai no preset "Other", que serve os arquivos da árvore como
estáticos (código-fonte baixável). Sem as regras do `.vercelignore`, bancos com CPF ou segredos
locais podem ir no envio. A CLI da Vercel não segue exatamente a semântica do git, por isso o
teste confere as linhas; o envio real se confere com `vercel deploy --dry --json`.
"""
import json
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BASE_PUBLICA = "!data/sample/raio_x_publico.duckdb"


def _linhas(caminho: str) -> list[str]:
    texto = (RAIZ / caminho).read_text(encoding="utf-8")
    return [x.strip() for x in texto.splitlines() if x.strip() and not x.startswith("#")]


@pytest.mark.parametrize(("arquivo", "framework"), [("vercel.json", "fastapi"),
                                                    ("web/vercel.json", "nextjs")])
def test_vercel_json_declara_o_framework(arquivo, framework):
    assert json.loads((RAIZ / arquivo).read_text(encoding="utf-8"))["framework"] == framework


def test_entrada_da_api_declarada_no_pyproject():
    cfg = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    assert cfg["tool"]["vercel"]["entrypoint"] == "api.index:app"


@pytest.mark.parametrize("regra", [".env", ".env.*", ".claude/", "*.duckdb", "*.duckdb.wal",
                                   "data/*", "data/sample/*"])
def test_vercelignore_da_api_exclui(regra):
    assert regra in _linhas(".vercelignore")


def test_vercelignore_so_reabre_a_base_publica():
    linhas = _linhas(".vercelignore")
    assert [x for x in linhas if x.startswith("!")] == ["!data", "!data/sample", BASE_PUBLICA]
    # a regra posterior vence: a base tem de ser reaberta depois das exclusões
    assert linhas.index(BASE_PUBLICA) > max(linhas.index(r) for r in ("*.duckdb", "data/sample/*"))


@pytest.mark.parametrize("regra", [".env", ".env.*"])
def test_vercelignore_do_web_exclui_env(regra):
    assert regra in _linhas("web/.vercelignore")


@pytest.mark.parametrize("arquivo", [".gitignore", "web/.gitignore"])
def test_gitignore_cobre_todo_env_menos_o_exemplo(arquivo):
    linhas = _linhas(arquivo)
    assert linhas.index("!.env.example") > linhas.index(".env*")
