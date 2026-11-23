## O quê e por quê
<!-- 1–3 frases -->

## Ciclo OODA desta mudança
- **Observe:** o que vi (dado, bug, métrica, feedback de leigo)
- **Orient:** impacto e riscos (LGPD, guardrails, contratos, performance)
- **Decide:** abordagem escolhida (e ADR se mexeu em `contracts/`)
- **Act:** o que mudou

## Checklist
- [ ] `make test` e `uv run ruff check .` verdes
- [ ] `cd web && pnpm lint && pnpm test && pnpm build` (se mexeu no web) e `pnpm e2e`
- [ ] Nenhum CPF real de terceiros em arquivo versionado
- [ ] Guardrails intactos (simbólica, presunção de inocência, CF ≤ 0,4 para indício, aviso "não é acusação")
- [ ] Docs/HANDOFF atualizados se mudou comportamento
