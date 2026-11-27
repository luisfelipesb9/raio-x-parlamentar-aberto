"""Uso: python -m publicar --origem BANCO_PSEUDONIMIZADO --destino ARQUIVO_PUBLICO

A origem é o banco já pseudonimizado (`--pseudonimizar`) e com findings (`make infer`). O destino é
um arquivo novo (nunca sobrescreve). Exige o mesmo `RAIO_X_ID_SALT` da pseudonimização no ambiente.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from graph import SalAusenteError
from publicar.build import PublicacaoErro, publicar


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m publicar", description=__doc__.split("\n\n")[0])
    ap.add_argument("--origem", type=Path, required=True,
                    help="banco pseudonimizado, com findings (somente leitura)")
    ap.add_argument("--destino", type=Path, required=True,
                    help="arquivo público a criar (não pode existir)")
    args = ap.parse_args(argv)
    try:
        r = publicar(args.origem, args.destino)
    except (PublicacaoErro, SalAusenteError) as erro:
        print(f"publicar: {erro}", file=sys.stderr)
        raise SystemExit(1) from None
    print(f"{r.destino}: {r.n_fatos_publicados} de {r.n_fatos_origem} fatos, {r.n_findings} findings, "
          f"{r.n_nos} nós e {r.n_arestas} arestas, {r.bytes_destino / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
