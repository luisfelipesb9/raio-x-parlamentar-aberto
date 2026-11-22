# ADR-001 — Fundação do projeto
Status: aceito · 2026-11-22

## Contexto
Nenhum open source ativo cobre "tudo de um político + correlação". Serenata (só CEAP), Parlametria
(arquivado 02/2023), Basômetro (parado 2020), Perfil Político (inativo).

## Decisão
- Construir do zero, reaproveitando metodologias desses projetos como fonte de conhecimento.
- Escopo MVP: deputados federais (Câmara API v2, CEAP, TSE, CGU, CEIS/CNEP, OpenSanctions).
- Python 3.11 + DuckDB + regras YAML + motor próprio (didático, explicável) em vez de CLIPS/Experta.
- Fatores de certeza MYCIN para incerteza; guardrails como regras de prioridade alta.
- Contratos Pydantic versionados como fronteira entre camadas e entre os dois desenvolvedores.

## Consequências
Motor simples de auditar e apresentar; escala de dados limitada ao DuckDB até migrar `repo/`.
