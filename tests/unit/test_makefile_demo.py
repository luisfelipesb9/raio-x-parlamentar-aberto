"""`make dev-demo` precisa subir a API da demonstração sem configuração manual: sal do seed_demo,
banco da demo e aviso claro se o banco ainda não existir."""
from pathlib import Path

from scripts.seed_demo import DB_DEMO, SAL_DEMO

BANCO_DEMO = "data/sample/raio_x_demo.duckdb"
MAKEFILE = (Path(__file__).resolve().parents[2] / "Makefile").read_text(encoding="utf-8")


def _alvo(nome: str) -> str:
    linhas = MAKEFILE.splitlines()
    ini = next(i for i, ln in enumerate(linhas) if ln.startswith(f"{nome}:"))
    corpo = []
    for ln in linhas[ini + 1:]:
        if not ln.startswith(("\t", " ")):
            break
        corpo.append(ln)
    return "\n".join(corpo)


def test_dev_demo_usa_o_sal_e_o_banco_do_seed_demo():
    alvo = _alvo("dev-demo")
    assert f"RAIO_X_ID_SALT={SAL_DEMO}" in alvo
    assert DB_DEMO.as_posix().endswith(BANCO_DEMO)
    assert f"RAIO_X_DB={BANCO_DEMO}" in alvo
    assert "api.main:app" in alvo and "--reload" in alvo


def test_dev_demo_avisa_se_o_banco_nao_existir():
    alvo = _alvo("dev-demo")
    assert "make seed-demo" in alvo
    assert "exit 1" in alvo


def test_dev_demo_esta_declarado_como_phony():
    assert "dev-demo" in MAKEFILE.splitlines()[0]
