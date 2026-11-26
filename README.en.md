# Raio-X Parlamentar (summary in English)

An expert system that gathers what is public about Brazilian federal deputies (votes, bills, expenses,
amendments, campaign donations, companies, sanctions) and explains it in plain Portuguese. Each
conclusion shows how it was derived and how certain it is (certainty factors, forward and backward
chaining, rules in YAML). The code is MIT licensed.

> **This is not an accusation; it is what public data shows.** Pending lawsuits are never treated as
> guilt (guardrail R08) and symbolic votes are never counted as individual votes (guardrail R02).

## Quick start
Requirements: Python 3.12 with uv, Node 22 with pnpm 12.
```
make setup
make demo    # fictional data, offline (see docs/demo.md)
make test
```
Then `make dev` (API) and `cd web && pnpm install && pnpm dev` (site).

Full documentation is in Portuguese: see the [main README](README.md).
