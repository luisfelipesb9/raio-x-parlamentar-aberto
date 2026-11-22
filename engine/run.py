"""Roda o motor sobre o banco e materializa findings. Uso: python -m engine.run"""
from __future__ import annotations

from engine import forward
from engine.factbase import FactBase
from engine.rules import load_rules
from repo.store import Store


def main() -> None:
    store = Store()
    res = forward.run(FactBase(store.load_facts()), load_rules())
    store.save_findings(res.findings, res.explanations)
    print(f"{len(res.findings)} findings · guardrails: {res.guardrail_log}")


if __name__ == "__main__":
    main()
