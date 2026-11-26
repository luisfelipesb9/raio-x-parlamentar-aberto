"""Makefile: `make publicar` e o novo passo de `make sample-publico` (ADR-011)."""
from pathlib import Path

MAKEFILE = (Path(__file__).resolve().parents[2] / "Makefile").read_text(encoding="utf-8")
ORIGEM = "data/sample/raio_x_publico_origem.duckdb"
PUBLICO = "data/sample/raio_x_publico.duckdb"


def _alvo(nome: str) -> str:
    linhas = MAKEFILE.splitlines()
    ini = next(i for i, ln in enumerate(linhas) if ln.startswith(f"{nome}:"))
    corpo = []
    for ln in linhas[ini + 1:]:
        if not ln.startswith(("\t", " ")):
            break
        corpo.append(ln)
    return "\n".join(corpo)


def test_publicar_chama_o_modulo_com_origem_e_destino_padrao():
    alvo = _alvo("publicar")
    assert "python -m publicar" in alvo and "--origem $(ORIGEM)" in alvo and "--destino $(DESTINO)" in alvo
    assert f"ORIGEM ?= {ORIGEM}" in MAKEFILE and f"DESTINO ?= {PUBLICO}" in MAKEFILE


def test_publicar_esta_declarado_como_phony():
    assert "publicar" in MAKEFILE.splitlines()[0].split()


def test_sample_publico_gera_a_origem_pseudonimizada_e_termina_em_publicar():
    alvo = _alvo("sample-publico")
    assert f"--pseudonimizar --db {ORIGEM}" in alvo
    assert f"RAIO_X_DB={ORIGEM} uv run python -m engine.run" in alvo
    assert f"python -m ingest.varredura --db {ORIGEM}" in alvo
    assert alvo.rstrip().splitlines()[-1].strip() == "$(MAKE) publicar"
    assert f"--db {PUBLICO}" not in alvo  # o arquivo público só nasce em `publicar`
