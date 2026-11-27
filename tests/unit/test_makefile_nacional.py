"""Makefile: `make ingest-nacional` e `make publicar-nacional` (Onda 4, 513 deputados)."""
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MAKEFILE = (RAIZ / "Makefile").read_text(encoding="utf-8")


def _alvo(nome: str) -> str:
    linhas = MAKEFILE.splitlines()
    ini = next(i for i, ln in enumerate(linhas) if ln.startswith(f"{nome}:"))
    corpo = []
    for ln in linhas[ini + 1:]:
        if not ln.startswith(("\t", " ")):
            break
        corpo.append(ln)
    return "\n".join(corpo)


def test_alvos_novos_estao_declarados_como_phony():
    phony = MAKEFILE.splitlines()[0].split()
    assert all(a in phony for a in ("ingest-nacional", "publicar-nacional", "deploy-check-nacional"))


def test_ingest_nacional_ingere_os_513_na_origem_pseudonimizada():
    alvo = _alvo("ingest-nacional")
    assert "python -m ingest.pipeline" in alvo
    for trecho in ("--nacional", "--pseudonimizar", "--db $(ORIGEM_NACIONAL)", "--anos-ceap $(ANOS_CEAP)",
                   "--fonte-votos $(FONTE_VOTOS)", "--janela-inicio $(JANELA_INICIO)",
                   "--janela-fim $(JANELA_FIM)", "--detalhar-deputados", "--incluir-proposicoes",
                   "$(ARGS)"):
        assert trecho in alvo, trecho
    for fonte in ("camara", "ceap", "cgu", "tse", "opensanctions", "rfb"):
        assert fonte in alvo
    assert "--amostra" not in alvo and "--uf " not in alvo  # nacional: sem recorte
    assert "--max-proposicoes" not in alvo and "--max-votacoes" not in alvo  # sem teto
    assert "data/sample" not in alvo  # nunca grava no banco da amostra
    assert "--db $(ORIGEM)" not in alvo  # nem na origem da amostra


def test_publicar_nacional_roda_motor_varredura_e_termina_em_publicar():
    alvo = _alvo("publicar-nacional")
    assert "RAIO_X_DB=$(ORIGEM_NACIONAL) uv run python -m engine.run" in alvo
    assert "python -m ingest.varredura --db $(ORIGEM_NACIONAL)" in alvo
    assert alvo.rstrip().splitlines()[-1].strip() == (
        "$(MAKE) publicar ORIGEM=$(ORIGEM_NACIONAL) DESTINO=$(DESTINO_NACIONAL)")
    assert "ingest.pipeline" not in alvo  # ingerir é demorado e fica em `ingest-nacional`


def test_origem_e_destino_do_nacional_nao_colidem_com_os_da_amostra():
    assert ("ORIGEM_NACIONAL ?= $(or $(TMPDIR),/tmp)/raio_x_nacional_origem.duckdb") in MAKEFILE
    assert "DESTINO_NACIONAL ?= data/nacional/raio_x_publico.duckdb" in MAKEFILE
    assert "raio_x_nacional_origem" not in _alvo("sample-publico")
    assert "ORIGEM_NACIONAL" not in _alvo("publicar") and "DESTINO_NACIONAL" not in _alvo("publicar")


def test_destino_nacional_nao_e_versionado_nem_vai_no_deploy():
    ignore = (RAIZ / ".gitignore").read_text(encoding="utf-8").split()
    assert "data/*" in ignore and "*.duckdb" in ignore  # data/nacional/ e qualquer .duckdb
    vercel = (RAIZ / ".vercelignore").read_text(encoding="utf-8").split()
    assert "data/*" in vercel and "!data/nacional" not in vercel


def test_deploy_check_nacional_aponta_para_o_destino_nacional():
    alvo = _alvo("deploy-check-nacional")
    assert "--publico $(DESTINO_NACIONAL)" in alvo


def test_sample_e_sample_publico_continuam_na_amostra_de_20_de_mg():
    for nome in ("sample", "sample-publico"):
        alvo = _alvo(nome)
        assert "--uf MG" in alvo and "--amostra 20" in alvo and "--max-proposicoes 300" in alvo
        assert "--nacional" not in alvo


@pytest.mark.skipif(shutil.which("make") is None, reason="make não instalado")
def test_dry_run_expande_as_variaveis_e_aceita_sobrescrita():
    r = subprocess.run(["make", "-n", "ingest-nacional", "ANOS_CEAP=2024", "ARGS=--reusar-raw",
                        "ORIGEM_NACIONAL=/tmp/nac_teste.duckdb"],
                       cwd=RAIZ, capture_output=True, text=True, check=True)
    assert "--db /tmp/nac_teste.duckdb" in r.stdout
    assert "--anos-ceap 2024" in r.stdout and "--reusar-raw" in r.stdout


@pytest.mark.skipif(shutil.which("make") is None, reason="make não instalado")
def test_dry_run_publicar_nacional_repassa_origem_e_destino_proprios():
    r = subprocess.run(["make", "-n", "publicar-nacional", "ORIGEM_NACIONAL=/tmp/nac.duckdb",
                        "DESTINO_NACIONAL=/tmp/nac_pub.duckdb"],
                       cwd=RAIZ, capture_output=True, text=True, check=True)
    assert "--origem /tmp/nac.duckdb" in r.stdout and "--destino /tmp/nac_pub.duckdb" in r.stdout
    assert "data/sample/raio_x_publico.duckdb" not in r.stdout
