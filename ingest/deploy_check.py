"""Confere o que seria enviado ao ar: só a base pública, e limpa de CPF íntegro de terceiros.

Falha (exit 1) se: a base pública não existe ou tem CPF íntegro de terceiro; ou existe QUALQUER
outro `*.duckdb` / `*.duckdb.wal` na árvore (a base de trabalho tem CPF íntegro). Ignora
.git, .venv, node_modules, .next e caches.

Uso: python -m ingest.deploy_check [--raiz .] [--publico data/sample/raio_x_publico.duckdb]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PUBLICO = Path("data/sample/raio_x_publico.duckdb")
IGNORAR = {".git", ".venv", "node_modules", ".next", ".pytest_cache", ".ruff_cache",
           "__pycache__"}


def _bancos(raiz: Path) -> list[Path]:
    achados = []
    for pasta, dirs, arquivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in IGNORAR]
        achados += [Path(pasta) / a for a in arquivos if a.endswith((".duckdb", ".duckdb.wal"))]
    return achados


def verificar_envio(raiz: Path | str, publico: Path | str = PUBLICO) -> list[str]:
    from ingest.varredura import varrer_banco
    from repo.store import Store
    raiz = Path(raiz).resolve()
    pub = Path(publico)
    pub = (pub if pub.is_absolute() else raiz / pub).resolve()
    erros = [f"banco fora da base pública no que seria enviado: {p.relative_to(raiz)}"
             for p in sorted(_bancos(raiz)) if p.resolve() != pub]
    if not pub.exists():
        return [f"a base pública não existe: {pub.relative_to(raiz) if pub.is_relative_to(raiz) else pub}",
                *erros]
    achados = varrer_banco(Store(pub, read_only=True))
    if achados:
        erros.append(f"{len(achados)} ocorrência(s) de CPF íntegro de terceiro na base pública "
                     "(rode ingest.varredura para ver onde)")
    return erros


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--publico", default=str(PUBLICO))
    a = ap.parse_args(argv)
    erros = verificar_envio(a.raiz, a.publico)
    for e in erros:
        print(f"REPROVADO: {e}")
    print("deploy-check: " + ("reprovado" if erros else "ok (só a base pública, sem CPF de terceiros)"))
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
