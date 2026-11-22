"""raw → facts. Uso: python -m ingest.pipeline [--fixture caminho.json]"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from repo.store import Store
from sources import REGISTRY


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", default="camara", choices=list(REGISTRY))
    ap.add_argument("--fixture", help="usa JSON bruto local em vez de baixar")
    ap.add_argument("--max-votacoes", type=int, default=30)
    a = ap.parse_args()
    src = REGISTRY[a.fonte]()
    raw = (json.loads(Path(a.fixture).read_text(encoding="utf-8")) if a.fixture
           else src.fetch(max_votacoes=a.max_votacoes))
    facts = src.normalize(raw)
    Store().upsert_facts(facts)
    print(f"{a.fonte}: {len(facts)} fatos gravados")


if __name__ == "__main__":
    main()
