# Raio-X Parlamentar (summary in English)

An expert system that gathers what is public about Brazilian federal deputies (votes, bills, expenses,
amendments, campaign donations, companies, sanctions) and explains it in plain Portuguese. Each
conclusion shows how it was derived and how certain it is (certainty factors, forward and backward
chaining, rules in YAML). The code is MIT licensed.

> **This is not an accusation; it is what public data shows.** Pending lawsuits are never treated as
> guilt (guardrail R08) and symbolic votes are never counted as individual votes (guardrail R02).

## Quick start
Requirements: Python (3.11+ supported, 3.12 recommended) with uv, Node 22 with pnpm 12.
```
make setup
make demo    # builds the fictional database, offline (see docs/demo.md)
make test
```
Then, in two terminals, `make dev-demo` (API on the demo database, with the demo salt already set) and
`cd web && pnpm install && pnpm dev` (site). To serve another database use `make dev` with `RAIO_X_ID_SALT`
and `RAIO_X_DB` set: the API refuses to start without the salt.

Full documentation is in Portuguese: see the [main README](README.md).
