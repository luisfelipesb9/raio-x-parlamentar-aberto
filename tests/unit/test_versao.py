"""A versão do projeto é uma só: pyproject, API, pacote web, lockfile Python, CITATION e CHANGELOG."""
import json
import re
import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ALVO = "0.3.0"


def _pyproject() -> str:
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def test_pyproject_na_versao_alvo():
    assert _pyproject() == ALVO


def test_pacote_web_na_mesma_versao():
    pacote = json.loads((RAIZ / "web" / "package.json").read_text(encoding="utf-8"))
    assert pacote["version"] == _pyproject()


def test_lockfile_python_na_mesma_versao():
    lock = tomllib.loads((RAIZ / "uv.lock").read_text(encoding="utf-8"))
    [projeto] = [p for p in lock["package"] if p["name"] == "raio-x-parlamentar"]
    assert projeto["version"] == _pyproject()


def test_citation_e_changelog_na_mesma_versao():
    citation = (RAIZ / "CITATION.cff").read_text(encoding="utf-8")
    assert re.search(rf"^version: {re.escape(_pyproject())}$", citation, re.MULTILINE)
    assert f"## [{_pyproject()}]" in (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")


def test_api_anuncia_a_versao_do_projeto(monkeypatch):
    pytest.importorskip("fastapi")
    from api.main import create_app

    monkeypatch.setenv("RAIO_X_ID_SALT", "sal-de-teste")
    assert create_app().version == _pyproject()
