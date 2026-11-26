# ADR-005 — Exceção à regra de direção de dependência
Status: Proposto · 2026-11-22

## Contexto
`docs/mapa-do-repositorio.md` define `sources → ingest → repo → engine → graph → api → web`. No código há duas importações que parecem
violá-la: `ingest/resolve` importa `repo.links` (`EntityLink`, `Ambiguidade`) e `engine/run.py` importa `repo.store.Store`.

## Decisão
- A regra descreve o **fluxo de dados**, não proíbe toda importação: `ingest` produz links que o `repo` persiste, então usa os
  tipos de `repo/links.py`; `engine/run.py` é o ponto de entrada (CLI) que lê e grava no `Store`. O núcleo do motor
  (`forward`, `backward`, `certainty`, `predicates`) continua sem importar `repo`.
- `ingest` **não** importa `engine` (por isso `normaliza_nome` é copiado em `ingest/resolve/comum.py`).
- Plano: mover `EntityLink` e `Ambiguidade` para `contracts/` (exige bump de `CONTRACT_VERSION`) e deixar `engine/run.py`
  como script fora do pacote do motor; então a exceção deixa de existir.

## Consequências
Duas exceções conhecidas e documentadas, sem ciclo de importação. Novas exceções exigem ADR.
