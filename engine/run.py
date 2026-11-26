"""Roda o motor sobre o banco e materializa findings.

Uso: python -m engine.run [--db CAMINHO] [--raw PASTA]
  --db   banco (padrão: $RAIO_X_DB ou data/raio_x.duckdb)
  --raw  pasta dos brutos com o manifest.json (padrão: $RAIO_X_RAW ou data/raw); dele vem o
         `sha256_bruto` das evidências (só de fonte com um único arquivo bruto; sem manifesto, fica vazio)
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from engine import forward
from engine.factbase import FactBase
from engine.rules import load_rules
from repo.store import Store
from sources import manifest


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m engine.run", description=__doc__.split("\n")[0])
    ap.add_argument("--db", type=Path, default=None, help="banco DuckDB (padrão: $RAIO_X_DB)")
    ap.add_argument("--raw", type=Path, default=None, help="pasta data/raw (padrão: $RAIO_X_RAW)")
    args = ap.parse_args(argv)
    store = Store(args.db)
    sha = manifest.sha_por_fonte_fato(args.raw or manifest.raw_dir_padrao())
    res = forward.run(FactBase(store.load_facts()), load_rules(), sha_por_fonte=sha)
    store.save_findings(res.findings, res.explanations)
    print(f"{len(res.findings)} findings · guardrails: {res.guardrail_log}")


if __name__ == "__main__":
    main()
