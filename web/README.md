# web/  (Next.js 16, App Router, TypeScript estrito, pnpm)
Telas: busca, ficha do deputado em linguagem simples (com cartões de alerta, semáforo de certeza em texto e botão
"Como sabemos disso?"), mapa de relações (Cytoscape.js + fcose, painel de backlinks, lista alternativa por teclado),
perguntar ao sistema (trilha da prova em árvore), comparar dois deputados e glossário com tooltips.

## Rodar
```
pnpm install
RAIO_X_ID_SALT=<qualquer-string> RAIO_X_DB=data/sample/raio_x_sample.duckdb uv run uvicorn api.main:app --port 8000   # na raiz do repo
pnpm dev                                                                               # http://localhost:3000
```
`NEXT_PUBLIC_API_URL` (padrão `http://localhost:8000`; ver `.env.example`). A API só libera CORS para `http://localhost:3000`.

## Comandos
| comando | o que faz |
|---|---|
| `pnpm gen:types` | gera `src/types/contracts.ts` a partir de `src/types/schemas/*.json` (não editar à mão; os JSON são gerados pelo backend) |
| `pnpm lint` | ESLint (sem `any`) + `tsc --noEmit` |
| `pnpm test` | Vitest (lógica pura: níveis, cliente da API, trilha, grafo, glossário, resumo) |
| `pnpm build` | build de produção |
| `pnpm e2e` | Playwright em `../tests/e2e` (desktop + mobile 375px) contra a API real; sobe API e web sozinho, ou reaproveita 8000/3000 |

Playwright está fixado em 1.63.0 por casar com o Chromium já em cache (`~/Library/Caches/ms-playwright`).
O e2e define `NEXT_PUBLIC_E2E=1` no build, que expõe `window.__raioXCy` (instância do Cytoscape) só para o teste de clique no canvas.

## Identidade visual ("raio-x")
Contrato em `DESIGN.md`. Manrope variável (`next/font/google`), tema escuro "chapa de raio-x" e claro "negatoscópio", um acento por modo.
Elementos: logo/favicon (`src/app/icon.svg`), imagem OG (`src/app/opengraph-image.tsx`), hero com hemiciclo varrido por feixe (SVG+CSS),
números que contam (só dado real da API ou fato do sistema), ticker, vidro e borda luminosa nos cartões, seções reveladas no scroll,
transições de página (View Transitions), hover magnético, holofote e cursor-halo (só ponteiro fino), grafo com brilho nos nós e arestas animadas.
`prefers-reduced-motion: reduce` desliga todos (coberto por `tests/e2e/identidade.spec.ts`).

## Decisões de design
- Nível de certeza **nunca só cor**: texto ("Certeza alta", "Apenas indício"…) + 1 a 4 barras + estilo da borda. Sem verde/vermelho, para não sugerir inocência/culpa.
- Nós do grafo se distinguem por forma e cor; empresa sancionada tem borda dupla; há lista alternativa de nós para teclado/leitor de tela.
- Seções da ficha sem dado na base mostram estado vazio honesto ("não permite concluir nada"), nunca zero disfarçado de "tudo certo".
