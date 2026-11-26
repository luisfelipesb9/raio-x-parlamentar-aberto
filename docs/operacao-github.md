# Operação do repositório no GitHub

Runbook do CI, das dependências e da configuração do repositório para o dia em que ele ficar
público. Tudo o que muda no GitHub está em arquivo versionado (`.github/`, `scripts/gh_publicar.sh`);
o que não tem API estável está listado em [O que continua manual](#o-que-continua-manual).

## CI (`.github/workflows/ci.yml`)

Roda em `push` para `main` e em todo `pull_request` (sem execução dobrada no PR). Permissão padrão
`contents: read`; o job `gitleaks` pede também `pull-requests: read`, porque a action lista os
commits do PR pela API e sem isso o evento `pull_request` dá 403.

| Job | O que garante |
|---|---|
| `python` | `uv sync --locked`, `ruff`, `pytest`, `scripts.checa_pii` (CPF íntegro e segredos versionados) |
| `gitleaks` | segredo no histórico inteiro (`fetch-depth: 0`) |
| `web` | `pnpm install --frozen-lockfile`, `pnpm lint` (eslint + tsc), `pnpm test`, `pnpm build` |
| `seo-smoke` | o que um buscador ou robô de IA recebe **sem JavaScript** (abaixo) |

### `seo-smoke`

`scripts/seo_smoke.py` (só biblioteca padrão) sobe a API sobre o banco de **demonstração fictício**
(`scripts.seed_demo`; sal público `sal-fixo-da-demonstracao`, que só vale para a demo), roda
`pnpm build` com a API no ar, sobe `next start` e faz GETs simples:

| Página | Esperado |
|---|---|
| `/deputado/9900001` | 200, `<h1` e o nome "Alice Fictícia (demo)" no HTML fora de `<script>`, `rel="canonical"` = `NEXT_PUBLIC_SITE_URL` + caminho, JSON-LD válido |
| `/deputado/99999999` | 404 de verdade |
| `/deputados` | 200 e links `href="/deputado/` no HTML |
| `/robots.txt` | 200, cita `GPTBot` e tem `Sitemap:` |
| `/sitemap.xml` | 200 e lista `https://exemplo.test/deputado/9900001` |
| `/llms.txt` | 200, não vazio |
| `/` | 200 e JSON-LD válido |

Saída: `OK`/`FALHA` por checagem com o motivo; código 1 se alguma falhar, 2 se o ambiente não subiu
(porta ocupada, banco da demo ausente, build quebrado). Recusa porta já ocupada para não testar
servidor alheio e mata os processos que iniciou (inclusive em Ctrl+C ou SIGTERM do CI). Timeout do
job: 15 min.

Rodar localmente (portas livres à escolha):

```bash
make seed-demo && pnpm --dir web install
uv run python -m scripts.seo_smoke --api-porta 8103 --site-porta 3103 --build
# contra um site já no ar (precisa servir a ficha demo):
uv run python -m scripts.seo_smoke --so-checar https://preview.exemplo.test --site-publico https://preview.exemplo.test
```

Na `main` de 26/11/2026 o smoke reprova 15 de 17 checagens (só passam o 200 da ficha e o da home): a ficha é renderizada no navegador
(sem `<h1`, nome, canonical ou JSON-LD no HTML), o id inexistente devolve 200, e `/deputados`,
`/robots.txt`, `/sitemap.xml` e `/llms.txt` não existem. O job fica verde quando os PRs de SEO
(a partir do #27) forem mesclados.

## Dependências

`.github/dependabot.yml`: semanal (segunda, 06:00 de Brasília), rótulo `dependencias`, poucos PRs
abertos por vez.

- **github-actions**: todas as actions em **um** PR (grupo `actions`), no máximo 2 abertos.
- **npm (`/web`)**: dev-deps minor/patch em um grupo (`npm-dev-minor-patch`), no máximo 3 abertos.
  Dependências de produção (`next`, `react`...) vêm uma por PR. `@playwright/test` fica fora do
  grupo porque até um minor troca a versão do navegador.
- **uv (raiz)**: minor/patch em um grupo, no máximo 2 abertos.
- **Majors ignorados** (revisão manual): `typescript` (muda opções do tsconfig), `@types/node`
  (acompanha o Node do `.nvmrc`, hoje 22) e `@playwright/test`.

Para fazer um major ignorado: branch própria, `pnpm add -D <pacote>@<versão>`, a mesma bateria
abaixo e PR normal.

### Triagem dos PRs abertos do Dependabot (26/11/2026)

Testes locais em worktree descartável por branch (nada foi enviado para as branches do Dependabot):
`pnpm install --frozen-lockfile && pnpm lint && pnpm test && pnpm build`, mais `tsc -p
tests/e2e/tsconfig.json` (as specs do e2e não entram no `pnpm lint`) e `playwright test --list`.
O `pnpm e2e` não rodou: usa as portas fixas 3000/8000, reaproveita servidor que já estiver nelas
fora do CI e precisa da amostra real (`make sample`), e não faz parte do CI.

| PR | Mudança | Resultado | Veredito |
|---|---|---|---|
| #1 | `astral-sh/setup-uv` 6 → 7 | CI do push verde; v7 só troca o runtime para Node 24 e remove `server-url` (não usado) | **seguro agora**. Do v8 em diante não há tag de major (`@v8` não existe): atualizações futuras precisam da versão completa ou do SHA |
| #2 | `gitleaks/gitleaks-action` 2 → 3 | CI do push verde; v3 só troca o runtime para Node 24, sem mudança de entrada | **seguro agora** (o vermelho do `pull_request` é o 403 que o #9 corrige) |
| #3 | `actions/checkout` 4 → 7 | CI do push verde; o endurecimento novo é para `pull_request_target`, que não usamos | **seguro agora** |
| #4 | `pnpm/action-setup` 4 → 6 | CI do push verde; v6.1 suporta pnpm 12 e continua lendo `packageManager` | **seguro agora** |
| #5 | `actions/setup-node` 4 → 7 | CI do push verde; v7 é ESM e tira o `NODE_AUTH_TOKEN` fictício (não publicamos no npm) | **seguro agora** |
| #6 | `typescript` 5.9.3 → 6.0.3 | install, lint, 162 testes e build verdes; **`tsc -p tests/e2e/tsconfig.json` falha** (TS5101: `baseUrl` obsoleto no TS 6) | **seguro com ajuste**: tirar `"baseUrl": "."` de `tests/e2e/tsconfig.json` (testado: compila no TS 6 e no 5.9, `playwright test --list` acha os 72 testes). Major: entra na política de revisão manual |
| #7 | `@playwright/test` 1.63.0 → 1.65.1 | install, lint, testes, build, tsc do e2e e `--list` verdes | **seguro agora**; o Chromium passa da revisão 1243 para a 1255: quem roda e2e local precisa de `pnpm --dir web exec playwright install chromium` |
| #8 | `@types/node` 22 → 26 | install, lint, testes e build verdes | **adiar**: o runtime é Node 22 (`.nvmrc`, `engines`); tipos do 26 deixam compilar API que não existe no 22. Fechar e subir junto com o `.nvmrc` |

Os PRs #1 a #5 mexem no `ci.yml`: com o `dependabot.yml` novo (grupo `actions`) o Dependabot passa
a abrir um PR só; os individuais podem ser mesclados antes ou fechados para o grupo substituí-los.

## Configuração do repositório: `scripts/gh_publicar.sh`

Para o dia em que o repositório ficar **público**. Padrão **dry-run** (mostra cada chamada e só faz
leituras); aplica só com `--aplicar`. Idempotente. Requer `gh` autenticado com admin no repositório.

```bash
scripts/gh_publicar.sh                                   # dry-run em luisfelipesb9/raio-x-parlamentar-aberto
scripts/gh_publicar.sh owner/repo --aplicar              # aplica
scripts/gh_publicar.sh owner/repo --aplicar --historico-linear
```

| Passo | Chamada | Efeito |
|---|---|---|
| 1 | `PUT /repos/{r}/private-vulnerability-reporting` | botão "Report a vulnerability" em Security (o canal do `SECURITY.md`) |
| 2 | `PATCH /repos/{r}` com `security_and_analysis.secret_scanning` e `secret_scanning_push_protection` = `enabled` | o GitHub procura segredos e **bloqueia o push** que contém um segredo conhecido |
| 3 | `PUT /repos/{r}/vulnerability-alerts` | alertas do Dependabot para dependências vulneráveis |
| 4 | `PUT /repos/{r}/automated-security-fixes` | PRs automáticos de correção de segurança |
| 5 | `PATCH /repos/{r}` com `delete_branch_on_merge: true` | apaga a branch do PR depois do merge |
| 6 | `POST /repos/{r}/labels` (só se `GET .../labels/dependencias` der 404) | cria o rótulo usado pelo `dependabot.yml` |
| 7 | `POST /repos/{r}/rulesets` ou `PUT /repos/{r}/rulesets/{id}` (procura pelo nome "main protegida") | ruleset da branch padrão (abaixo) |

Ruleset "main protegida" (alvo `~DEFAULT_BRANCH`, sem bypass):

- PR obrigatório com **0 aprovações**: são 2 mantenedores e um deles pode ser quem abriu o PR (com
  1 aprovação obrigatória, um PR do único mantenedor disponível ficaria travado). Conversas precisam
  estar resolvidas.
- Checks obrigatórios: `python`, `web`, `gitleaks`, `seo-smoke`, exigidos da app GitHub Actions
  (`integration_id` 15368), para que outro app não satisfaça o check com o mesmo nome. Sem exigir
  branch atualizada (`strict: false`), para não forçar rebase a cada merge.
- Bloqueia force-push (`non_fast_forward`) e deleção da branch.
- Histórico linear só com `--historico-linear` (exige squash ou rebase no merge).

Em repositório **privado** de conta gratuita, os passos 1, 2 e 7 costumam ser recusados (403/404/422):
o script explica a recusa, segue para os outros passos e termina com código 1. Rode de novo depois
de tornar o repositório público.

Rollback: no GitHub, Settings > Rules > Rulesets > "main protegida" > Delete (ou
`gh api -X DELETE repos/{r}/rulesets/{id}`); os demais passos se desligam em Settings > Code security
e Settings > General. Verificação: `gh api repos/{r}/rulesets` e `gh api repos/{r} --jq .security_and_analysis`.

O `seo-smoke` só deve entrar como check obrigatório depois que os PRs de SEO estiverem na `main`
(antes disso ele reprova e travaria todo merge).

## O que continua manual

- **Social preview**: Settings > General > Social preview > Edit > Upload an image (1280×640). Não há
  API pública para isso.
- **Discussions**: Settings > General > Features > Discussions (se o time quiser um canal de dúvidas).
- **Convites** de colaboradores: Settings > Collaborators (cada convite é aceito pela pessoa).
- **Tornar o repositório público**: Settings > General > Danger Zone > Change visibility. Antes:
  `make checa-pii`, gitleaks no histórico e conferência do `docs/HANDOFF.md`.

## Deploy check (`make deploy-check`)

`ingest/deploy_check.py` reprova (código 1) quando:

- a base pública não existe ou tem CPF íntegro de terceiro;
- há outro `*.duckdb`/`*.duckdb.wal` na árvore;
- há `.env`/`.env.*` local na árvore (só `.env.example`, `.env.sample` e `.env.template` passam);
- `RAIO_X_ID_SALT` do ambiente (o mesmo sal que gerou a base pública) está ausente, tem menos de 32
  caracteres ou é um valor público conhecido (`raio-x-v1`, o sal da demo, os sais de teste).

O valor do sal nunca é impresso. Rode com o sal exportado:
`RAIO_X_ID_SALT=<segredo> make deploy-check`. Um sal forte: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
Isso confere a **máquina que gerou a base**; o sal configurado na Vercel tem de ser o mesmo e se
confere no painel (Settings > Environment Variables).
