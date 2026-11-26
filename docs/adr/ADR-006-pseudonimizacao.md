# ADR-006 — Pseudonimização da base pública
Status: Aceito · 2026-11-22

## Contexto
A base de amostra contém CPF de terceiros (doadores, sócios, fornecedores PF). Publicá-la violaria a minimização da LGPD,
mas a R06b depende de comparar CPFs parcialmente visíveis.

## Decisão
- `--pseudonimizar` (pipeline) substitui CPF íntegro por `hmac:<32 hex>` = HMAC-SHA256 com sal secreto `RAIO_X_ID_SALT`: mesmo CPF, mesmo
  pseudônimo (preserva junções), sem reversão sem o sal.
- `doador_cpf_visivel` guarda só os dígitos visíveis compatíveis para a R06b continuar funcionando.
- CPF de fornecedor PF embutido em `despesa_ceap.fornecedor` (36 casos) também é substituído.
- `make sample-publico` gera `data/sample/raio_x_publico.duckdb` e roda `ingest.varredura`: 0 CPFs íntegros, com controle positivo de 752 na base não pseudonimizada.

## Limites
- A varredura **não** cobre `data/raw` (bruto local, nunca versionado/publicado).
- Pseudonimização não é anonimização: quem tem o sal ou um CPF candidato pode reidentificar por força bruta (espaço de CPF é pequeno); o sal precisa ficar fora do repositório.
- Nomes continuam na base (são dados de fontes públicas); a exposição de nome de PF sem identidade confirmada é tratada no grafo e na R06b (ADR-003).

## Consequências
Base pública segura para o deploy da API; R06b preservada. Rotacionar o sal invalida pseudônimos antigos.
