# api/  (Pedro, fase 2)
FastAPI **somente leitura** (só GET). Nunca chama serviço externo. Respostas = tipos de `contracts/`
+ envelopes em `api/schemas.py` (exportados para o web por `scripts/export_schemas.py`).

Subir: `make dev` (`uvicorn api.main:app`). Banco: env `RAIO_X_DB` (padrão `data/raio_x.duckdb`);
abre em modo somente leitura (`Store(path, read_only=True)`); se não existir → 503 (a API nunca cria banco). CORS: só GET; origens em `RAIO_X_CORS_ORIGINS` (vírgulas; `*` é ignorado), padrão só `http://localhost:3000`.
Erros: RFC 7807 (`application/problem+json`); 404 claros; 422 para parâmetro inválido; 500 genérico
(stack só no log). Docs interativas em `/docs`.

| endpoint | resposta |
|---|---|
| `GET /saude` | `Saude` `{status, contract_version, n_deputados, n_findings, banco: ok/ausente/erro, pseudonimizado}`; **503** com o mesmo corpo quando `status=degradado`, sem caminho; `pseudonimizado=true` = nenhum CPF íntegro de terceiro (doador, sócio, PEP, despesa PF) no banco |
| `GET /deputados?q=&uf=&partido=&page=&page_size=` (≤100) | `PaginaDeputados` (ordem alfabética sem acento) |
| `GET /deputados/{id}` | `PerfilDeputado` (+ resumo por categoria) |
| `GET /deputados/{id}/findings` | `list[Finding]` (cf desc) |
| `GET /deputados/{id}/metricas` | `MetricasDeputadoResposta`: `n_votos`, `n_votos_validos`, janela de votos e os `valores` do finding de cada regra de inferência (`finding_id: null` quando a regra não gerou finding); 404 se o deputado não existe |
| `GET /cobertura` | `CoberturaResposta`: janela das votações, agregado por fonte (tipos, nº de fatos, menor/maior `coletado_em`), nº de deputados e de findings |
| `GET /findings/{id}/explicar` | `Explanation` |
| `GET /grafo?centro=deputado:ID&profundidade=0..2&relacoes=a,b` | `GrafoResposta` (≤300 nós, `truncado`) |
| `GET /grafo/backlinks/{node_id}` | `BacklinksResposta` |
| `GET /perguntar?deputado=ID&objetivo=risco_integridade` | `PerguntarResposta` (CF + trilha da prova regressiva) |
| `GET /comparar?a=ID&b=ID` | `ComparacaoResposta` (perfis, afinidade de votos, nós em comum) |

Cache: grafo/índices são montados uma vez por processo. **Pare a API antes de `make ingest` /
`make infer`** (o DuckDB não deixa outro processo escrever com a API aberta) e suba de novo depois.
LGPD: nenhuma resposta traz CPF nem campo `cpf*` (testado varrendo todos os endpoints); nós `pessoa`
com CPF mascarado não carregam nome. `RAIO_X_ID_SALT` é o sal dos ids de pessoa e é obrigatório: a API não sobe sem ele (não há sal padrão).
Dependências: `fastapi`, `uvicorn` (e `httpx` para testes) — ver `pyproject.toml`.

`/perguntar`: um único `forward.run` (todas as regras, guardrails aplicados) por processo, passado a
`backward.prove(..., resultado=)`. Um passo da trilha sem conclusão (`cf = 0`) pode trazer `diagnostico`
`{motivo, detalhes}`: `dados_insuficientes` (menos votos válidos que o mínimo; `n_votos_validos`,
`minimo_votos`, `taxa` se calculável), `abaixo_do_limiar` (`n_votos_validos`, `minimo_votos`, `taxa`,
`limiar`) ou `sem_regra_aplicavel` (só quando nenhuma regra conclui o objetivo). Só a R01 tem
diagnosticador; passo de regra sem diagnosticador, regra composta (R09) ou ciclo vem com
`diagnostico: null` e mantém a `nota` (ex.: "sub-objetivos: ..."). Para outra regra, registre um com
`@diagnostico("<predicado>")`. O campo `nota` (texto) não mudou.

### Cobertura e métricas
- **Janela de votos** (`JanelaVotos`): `inicio`/`fim` = menor e maior `data` dos fatos `votacao`;
  `n_votacoes_nominais` = votações com `nominal = true` (as que têm voto individual);
  `n_votacoes_com_orientacao` = votações em que o governo orientou **Sim ou Não** (a única orientação que a
  R01 usa; "Liberado", vazio e ausente não contam).
- **Fontes** (`FonteCobertura`): agregado dos fatos por `fonte`. `coletado_em_*` é o momento em que o dado
  entrou na base (não a data do dado), em UTC.
- **Votos do deputado**: `n_votos` = votos em votação nominal; `n_votos_validos` = os que a R01 conta
  (Sim/Não numa votação com orientação Sim/Não). É a mesma regra de `engine.predicates.core._votos_validos`,
  escrita em SQL em `Store.contagem_votos`; um teste confere que as duas dão o mesmo número.
- **`metricas_por_regra`**: os `valores` do finding da regra. Só vão números e textos; listas viram a
  quantidade (`cnpjs` → `n_cnpjs`); valores nulos, objetos e booleanos (flags do motor, como `confirmado_por_cpf`
da R06) ficam de fora e continuam em `/deputados/{id}/findings`.
- Uma consulta por processo (como o snapshot): dado novo exige reiniciar a API.

## Deploy na Vercel (publicado; ver "Deploy" em `docs/HANDOFF.md`)
Dois projetos Vercel a partir deste repositório:

| projeto | pasta publicada | framework |
|---|---|---|
| API (este) | raiz do repo (`.`) | FastAPI (`vercel.json`) |
| Web | `web/` | Next.js (`web/vercel.json`) |

**Root Directory:** pela CLI (como foi publicado), deixe `.` nos dois projetos e rode os comandos de dentro da pasta
publicada. Só no deploy pelo Git o projeto web usa Root Directory `web/`. Combinar os dois faz a CLI procurar
`web/web`.

A raiz não tem `package.json`, então não conflita com o `web/`. Arquivos: `api/index.py` (exporta `app`),
`vercel.json` (`framework: fastapi`, obrigatório, e `functions` com `maxDuration` e `excludeFiles`),
`.vercelignore` (tira web/tests/docs/ e tudo de `data/`, **exceto `data/sample/raio_x_publico.duckdb`**). Dependências vêm do `pyproject.toml`/`uv.lock`
(grupo `dev` não entra); não precisa de `requirements.txt`.

Passo a passo:
1. Banco: **somente a base pseudonimizada** — `RAIO_X_ID_SALT=<segredo> make sample-publico`, que gera
   `data/sample/raio_x_publico.duckdb` e roda a varredura (precisa sair 0). NUNCA publique
   `raio_x_sample.duckdb` nem `raio_x.duckdb` (CPF de terceiros); `.vercelignore` só deixa passar a base pública. Ela é
   ignorado pelo git (`data/*`), então deploy por Git NÃO leva o banco: use o CLI a partir da raiz
   (passo 4), que envia os arquivos locais respeitando `.vercelignore`.
2. `vercel link` na raiz (projeto novo "raio-x-api", Root Directory `.`).
3. Variáveis de ambiente (Production/Preview), via dashboard ou `vercel env add`:
   - `RAIO_X_DB`: caminho do banco no bundle, relativo à raiz do projeto (`data/sample/raio_x_publico.duckdb`).
   - `RAIO_X_ID_SALT`: sal dos ids de pessoa (segredo; qualquer string longa e fixa). **Obrigatório**: sem ele a API falha na subida.
   - `RAIO_X_CORS_ORIGINS`: origem do web, ex. `https://raio-x-web-delta.vercel.app` (vírgulas; sem `*`).
4. Primeiro deploy de um projeto: `vercel deploy --prod` (só pode ser de produção). Nos seguintes: `vercel deploy`
   (preview, abre logado na Vercel), conferir `/saude` e só então `--prod`.
   Em todos, conferir `GET <url>/saude` (`banco: ok`) e `/docs`.
5. Projeto web: `cd web`, `vercel link`, apontar `NEXT_PUBLIC_API_URL` para o domínio do passo 4.

Local equivalente: `uv run uvicorn api.index:app`.
Limites/riscos: banco é aberto read-only (o filesystem da função é somente leitura), sem
atualização em tempo de execução: dado novo = novo deploy. Bundle < 500 MB (DuckDB ~40 MB + banco).
Validado em produção em 2026-11-25. A entrada é declarada em `[tool.vercel]` no `pyproject.toml`.
