# ADR-005 — Exceção à regra de direção de dependência
Status: Proposto · 2026-11-22

## Contexto
`docs/mapa-do-repositorio.md` define `sources → ingest → repo → engine → graph → api → web`. No código há duas importações que parecem
violá-la: `ingest/resolve` importa `repo.links` (`EntityLink`, `Ambiguidade`) e `engine/run.py` importa `repo.store.Store`.

Lista completa das importações de `repo` fora de `repo/`, `api/` e `scripts/` (conferida por `grep` no código):

| Arquivo | Importa | Papel |
|---|---|---|
| `ingest/resolve/{candidatura,emenda,pep,cnpj,comum}.py` | `repo.links` | tipos dos links de entidade que o `repo` persiste |
| `ingest/pipeline.py:35` | `repo.store.Store` | ponto de entrada (CLI) da ingestão: grava fatos e links |
| `ingest/deploy_check.py:31` | `repo.store.Store` | CLI de verificação antes de publicar: só lê o banco |
| `ingest/varredura.py:78` | `repo.store.Store` | CLI da varredura de CPF na base pública: só lê o banco |
| `engine/run.py:17` | `repo.store.Store` | ponto de entrada (CLI) do motor: lê fatos e grava findings |
| `sources/base.py`, `sources/manifest.py` | `repo.proveniencia` | caminho do bruto e leitura do manifesto, compartilhados com a API (ADR-009) |

## Decisão
- Os pontos de entrada em `ingest/` (`pipeline`, `deploy_check`, `varredura`) e `engine/run.py` são CLIs: abrem o `Store` para ler ou gravar. O núcleo de cada camada não importa `repo.store`.
- A regra descreve o **fluxo de dados**, não proíbe toda importação: `ingest` produz links que o `repo` persiste, então usa os
  tipos de `repo/links.py`; `engine/run.py` é o ponto de entrada (CLI) que lê e grava no `Store`. O núcleo do motor
  (`forward`, `backward`, `certainty`, `predicates`) continua sem importar `repo`.
- `ingest` **não** importa `engine` (por isso `normaliza_nome` é copiado em `ingest/resolve/comum.py`).
- Plano: mover `EntityLink` e `Ambiguidade` para `contracts/` (exige bump de `CONTRACT_VERSION`) e deixar `engine/run.py`
  como script fora do pacote do motor; então a exceção deixa de existir.

## Consequências
As exceções conhecidas são as da tabela acima, todas documentadas e sem ciclo de importação. Novas exceções exigem ADR.
