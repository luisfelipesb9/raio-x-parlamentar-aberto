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
| `GET /findings/{id}/explicar` | `Explanation` |
| `GET /grafo?centro=deputado:ID&profundidade=0..2&relacoes=a,b` | `GrafoResposta` (≤300 nós, `truncado`) |
| `GET /grafo/backlinks/{node_id}` | `BacklinksResposta` |
| `GET /perguntar?deputado=ID&objetivo=risco_integridade` | `PerguntarResposta` (CF + trilha da prova regressiva) |
| `GET /comparar?a=ID&b=ID` | `ComparacaoResposta` (perfis, afinidade de votos, nós em comum) |

Cache: grafo/índices são montados uma vez por processo. **Pare a API antes de `make ingest` /
`make infer`** (o DuckDB não deixa outro processo escrever com a API aberta) e suba de novo depois.
LGPD: nenhuma resposta traz CPF nem campo `cpf*` (testado varrendo todos os endpoints); nós `pessoa`
com CPF mascarado não carregam nome. `RAIO_X_ID_SALT` troca o sal dos ids de pessoa.
Dependências: `fastapi`, `uvicorn` (e `httpx` para testes) — ver `pyproject.toml`.

`/perguntar`: um único `forward.run` (todas as regras, guardrails aplicados) por processo, passado a
`backward.prove(..., resultado=)`.

## Deploy na Vercel (preparado, NÃO publicado)
Dois projetos Vercel a partir deste repositório:

| projeto | Root Directory | framework |
|---|---|---|
| API (este) | raiz do repo (`.`) | FastAPI (Python, detectado) |
| Web | `web/` | Next.js |

A raiz não tem `package.json`, então não conflita com o `web/`. Arquivos: `api/index.py` (exporta `app`),
`vercel.json` (só `functions` com `maxDuration` e `excludeFiles`), `.vercelignore` (tira web/tests/docs/
data/raw do bundle e **mantém `data/*.duckdb`**). Dependências vêm do `pyproject.toml`/`uv.lock`
(grupo `dev` não entra); não precisa de `requirements.txt`.

Passo a passo:
1. Banco: **somente a base pseudonimizada** — `RAIO_X_ID_SALT=<segredo> make sample-publico`, que gera
   `data/sample/raio_x_publico.duckdb` e roda a varredura (precisa sair 0). NUNCA publique
   `raio_x_sample.duckdb` nem `raio_x.duckdb` (CPF de terceiros); `.vercelignore` só deixa passar a base pública. Ela é
   ignorado pelo git (`data/*`), então deploy por Git NÃO leva o banco: use o CLI a partir da raiz
   (`vercel deploy`, depois `--prod`), que envia os arquivos locais respeitando `.vercelignore`.
2. `vercel link` na raiz (projeto novo "raio-x-api", Root Directory `.`).
3. Variáveis de ambiente (Production/Preview), via dashboard ou `vercel env add`:
   - `RAIO_X_DB`: caminho do banco no bundle, relativo à raiz do projeto (`data/sample/raio_x_publico.duckdb`).
   - `RAIO_X_ID_SALT`: sal dos ids de pessoa (segredo; qualquer string longa e fixa).
   - `RAIO_X_CORS_ORIGINS`: origem do web, ex. `https://raio-x-web.vercel.app` (vírgulas; sem `*`).
4. `vercel deploy`, conferir `GET <url>/saude` (`banco: ok`) e `/docs`.
5. Projeto web: Root Directory `web/`, apontar a variável de URL da API para o domínio do passo 4.

Local equivalente: `uv run uvicorn api.index:app`.
Limites/riscos: banco é aberto read-only (o filesystem da função é somente leitura), sem
atualização em tempo de execução: dado novo = novo deploy. Bundle < 500 MB (DuckDB ~40 MB + banco).
Não validado numa implantação real (nenhum deploy foi feito). Se a Vercel não detectar `api/index.py`,
adicione `[tool.vercel] entrypoint = "api.index:app"` ao `pyproject.toml`.
