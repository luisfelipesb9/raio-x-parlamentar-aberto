# HANDOFF — estado real do projeto

Última revisão: 2026-11-22. Divisão original: fundação e raciocínio (Luis) e produto (Pedro Rodrigues).

## Como rodar
```
make setup && make test          # testes Python (pytest); web: `pnpm test` (unit) e `pnpm e2e` (Playwright), em web/
make sample                      # ingere 20 deputados de MG (votações de fev–mar/2025, CEAP do arquivo de 2024, TSE 2022) + roda o motor -> data/sample/raio_x_sample.duckdb
make verifica                    # confere governismo e CEAP contra os brutos (ver "Cobertura e verificação")
RAIO_X_DB=data/sample/raio_x_sample.duckdb make dev    # API em http://localhost:8000 (/docs)
cd web && pnpm install && pnpm dev                     # web em http://localhost:3000
```

## Status por componente
| Componente | Status |
|---|---|
| contracts/ (Fact, Finding, Explanation, Graph) v0.2.0 | pronto |
| sources/: camara, ceap, cgu, tse, opensanctions, rfb | prontos, com testes de fixture |
| ingest/pipeline + ingest/resolve (candidatura, emenda, pep, cnpj) | pronto; links com CF e tabela de ambiguidades |
| repo/ DuckDB (`Store`, `read_only`, migrations 001/002) | pronto |
| engine: CF MYCIN, loader YAML, forward, backward com `requer` e detecção de ciclo, explain | pronto |
| Regras R01–R09 e R06b | prontas (R09 só no regressivo) |
| graph/ (projeção, subgrafo, backlinks, afinidade de votos) | pronto |
| api/ (endpoints GET somente leitura, ver `api/README.md`; RFC 7807, cache por impressão digital do banco) | pronto |
| DB de amostra (`data/sample/raio_x_sample.duckdb`) | pronto, gerado por `make sample` |
| web/ (ficha, grafo Cytoscape, perguntar/comparar, glossário) | **pronto**: rotas em `web/src/app` (busca, ficha, grafo, perguntar, comparar, glossário, fontes); lint/test/build e e2e Playwright em desktop e 375px; identidade visual "raio-x" em `web/DESIGN.md` |
| Relatório e roteiro de apresentação | `docs/relatorio/` (este commit) |

## O que falta
1. **web/**: concluído (ver tabela). Resta apenas validação com leigos.
2. **R05**: agora tem dados (`make sample` usa `--incluir-proposicoes`): 10 findings.
3. **CPF do deputado**: resolvido. `CamaraSource.fetch(detalhar_deputados=...)` (flag `--detalhar-deputados`, já em `make sample`) busca `GET /deputados/{id}`; na amostra 20/20 candidaturas ligam por CPF (cf 1,0) e 20/20 PEP por CPF (0,95).
4. **Calibração**: CFs das regras e limiares (z=3,5; razão 3; etc.) são escolhas do especialista, **não** calibradas
   com dados rotulados (ver relatório, seção de limitações).
5. Validação com leigos (plano, passo 9): não feita. Comparação externa: parcial, só a R01
   (`docs/relatorio/comparacao-externa.md`).
6. Fato `processo` (guardrail R08) ainda sem fonte: o guardrail existe, mas nenhum plugin produz `processo`.
7. **Pendência da ADR-011, não implementada:** `make verifica` no banco público enxuto. O banco público não tem as despesas cruas, então
   `verifica` roda só na origem pseudonimizada. Falta fazê-lo, no público, conferir que findings, contagens (`publicacao_meta`) e ausência de
   CPF batem com a origem (hash `origem_sha256` já está registrado). Também pendente: repetir o teste de escala com dados nacionais reais
   (`docs/ampliacao/medicoes.md`, seção 5, é sintético).

## Resultados na amostra (40 findings no relatório; 38 na base publicada em 26/11/2026)
Nota: a base publicada em 26/11/2026 foi recoletada (CEAP, CGU e OpenSanctions baixados de novo) e deu 38 findings (R01 14, R03 2, R04 3, R05 10, R07 9); `make verifica` confere 44 de 44 contra o bruto. Os números abaixo são os do relatório (coleta anterior).
R01: 14 · R03: 2 · R04: 5 · R05: 10 · R07: 9 (CF médio 0,384 = 0,6 × 0,8 do link por nome × 0,8 Pix) · R02 removeu 121 votações simbólicas e R08 0 processos (guardrails, sem finding). Objetivo da R05: `pontuacao_producao_legislativa`. R06 e R06b: 0 com `--limite-rfb 50` (com 300 surge 1 R06b: o zero era cobertura, não ausência). **R06 confirmado não dispara com dados da RFB**: o QSA vem sempre mascarado (617 sócios mascarados, 96 sem CPF, 0 íntegros), então só a R06b é alcançável.
Escopo da amostra: 2.083 emendas ligadas (o total global da CGU é 37.297 ligadas de 77.113), 1.008 doações, 17.060 votos_municipio.

## Cobertura e verificação
- **Endpoints** (somente leitura, ver `api/README.md`): `GET /cobertura` (janela das votações, agregado por fonte com
  menor/maior `coletado_em`, nº de deputados e findings) e `GET /deputados/{id}/metricas` (votos do deputado e `valores` de
  cada regra; 404 se o deputado não existe). `/perguntar` agora traz `diagnostico` nos passos sem conclusão
  (`dados_insuficientes`, `abaixo_do_limiar`, `sem_regra_aplicavel`; só a R01 tem diagnosticador; regra composta, ciclo e regra sem
  diagnosticador ficam com `diagnostico: null` e mantêm a `nota`; `sem_regra_aplicavel` só quando nenhuma regra conclui o objetivo).
- **Manifest** `data/raw/manifest.json`: sha256, tamanho e data de cada arquivo bruto, gravado por `save_raw`/`registrar_raw`.
  `Evidence.coletado_em` vem do fato; `Evidence.sha256_bruto` só quando a fonte tem UM arquivo no manifest (Câmara, CGU e RFB
  têm vários e ficam sem hash). Findings gravados antes disso são completados pela API na leitura, lendo só o manifesto
  (exceção documentada no ADR-009; o hash é o do manifesto atual, e `python -m engine.run --raw PASTA` o grava na evidência na hora da inferência).
- **`make verifica`** (`scripts/verifica.py`): recalcula, sem usar o motor, o governismo e o total CEAP de cada deputado do
  banco a partir dos brutos e confronta com banco e findings; confere o manifest. Opções via `ARGS=`, por exemplo
  `make verifica ARGS="--gerar-manifesto"`: `--gerar-manifesto` (manifest retroativo para brutos que já existiam,
  `origem: retroativo`), `--online` (amostra a contagem de votos na API da Câmara; desligado por padrão), `--raw PASTA`,
  `--saida ARQUIVO.md`. Escreve `docs/relatorio/verificacao.md`; sai com código 1 se houver divergência.
  Sem `data/raw/manifest.json` (instalação limpa), o manifesto vira UMA linha "não verificado" ("manifesto ausente: rode com
  `--gerar-manifesto`") e não reprova; arquivo fora de um manifesto que existe continua sendo divergência. Com mais de um
  `camara_<início>_<fim>.json`, usa o que cobre a janela das votações do banco e avisa se não houver como decidir.
  Última rodada na amostra: 44 conferências, 0 divergências; ela exigiu `--gerar-manifesto` (a conferência `--online`
  não foi executada).

## Operação e privacidade
- A base de amostra **não é versionada**: contém CPF de terceiros (minimização, LGPD). Gere com `make sample`.
- **Pare a API antes de `make ingest` / `make infer`**: o DuckDB trava o arquivo para escrita enquanto a API o mantém aberto.

## Privacidade e deploy
- `--pseudonimizar` troca CPF por HMAC-SHA256 (`hmac:<32 hex>`, sal em `RAIO_X_ID_SALT`); `doador_cpf_visivel` preserva a R06b; CPF de fornecedor PF dentro de `despesa_ceap.fornecedor` (36 casos) também é substituído. Ver ADR-006.
- `make sample-publico` gera `data/sample/raio_x_publico.duckdb` e roda a varredura (`ingest.varredura`): 0 CPFs íntegros (controle positivo: 752). A varredura **não** cobre `data/raw`.
- API: `/saude`, forward pré-calculado no `/perguntar`; `vercel.json` + `api/index.py` (publicado na Vercel).

## Deploy (publicado em 2026-11-26, Vercel Hobby, dois projetos)
- Site: https://raio-x-parlamentar.vercel.app (projeto `raio-x-parlamentar`, Root Directory `web`, Node 22; **deploy automático
  pelo GitHub a cada merge na `main`**)
- API: https://raio-x-parlamentar-api.vercel.app/saude (projeto `raio-x-parlamentar-api`, raiz do repositório; **deploy
  automático pelo GitHub DESLIGADO**, porque o git não leva a base: só a CLI publica)
- Variáveis do site: `API_URL` e `NEXT_PUBLIC_API_URL` (endereço da API), `NEXT_PUBLIC_SITE_URL` (endereço do site, base do canonical).
  Variáveis da API: `RAIO_X_DB`, `RAIO_X_ID_SALT` (segredo), `RAIO_X_CORS_ORIGINS` (endereço do site).

**O git não leva a base** (`data/` é ignorado): deploy automático pelo GitHub sobe a API sem banco. Publique pela
CLI, **de dentro da pasta que está sendo publicada** (rodando de outra pasta, a CLI lê o `vercel.json` errado).

**Nunca remova `"framework"` dos `vercel.json`.** Sem ele, um projeto novo cai no preset "Other", que serve os
arquivos da árvore como estáticos (código-fonte baixável) e não monta as rotas da API.

1. `RAIO_X_ID_SALT=<segredo> make sample-publico` (a varredura precisa sair 0; gera a origem pseudonimizada em
   `$TMPDIR/raio_x_publico_origem.duckdb` (ou `/tmp`; mude com `ORIGEM=...`; fora da árvore, de propósito) e, por `make publicar`, o banco enxuto `data/sample/raio_x_publico.duckdb`,
   ADR-011). `make verifica` roda sobre a origem
   (`RAIO_X_DB=$TMPDIR/raio_x_publico_origem.duckdb`), porque o banco enxuto não tem as despesas cruas. Guarde o sal fora do repositório
   e use sempre o mesmo, senão os ids pseudonimizados mudam a cada atualização.
2. Em um clone limpo, copie só `data/sample/raio_x_publico.duckdb` e rode `make deploy-check` (reprova se houver
   outro `.duckdb` na árvore).
3. API (raiz): `vercel link`; envs `RAIO_X_DB=data/sample/raio_x_publico.duckdb`, `RAIO_X_ID_SALT`,
   `RAIO_X_CORS_ORIGINS=<url do web>`. `vercel deploy --dry --json` deve listar a base e nenhum outro arquivo de
   `data/`. No primeiro deploy do projeto, `vercel deploy --prod` (só pode ser de produção). **Nas atualizações**,
   `vercel deploy` (preview, abre logado na Vercel), conferir `/saude` e só então `vercel deploy --prod`.
4. Web (`cd web`): `vercel link`; envs `NEXT_PUBLIC_API_URL=<url da API>` e `NEXT_PUBLIC_SITE_URL=<url do site>`;
   `vercel deploy --prod`. Se a URL do site só for conhecida agora, grave-a em `RAIO_X_CORS_ORIGINS` e republique a API.
   **`RAIO_X_ID_SALT` é obrigatório na API** (sem valor padrão): sem a env a função falha na subida com mensagem
   explicando como defini-la. Confira que ela existe nos ambientes Production e Preview antes de qualquer deploy.
5. Conferir: `/saude` (`status: ok`, `pseudonimizado: true`); `<url da API>/pyproject.toml` deve dar 404.

Validado em produção (2026-11-26): `/saude` ok (contrato 0.2.0, 20 deputados, 38 findings; a base foi recoletada nesse dia, veja a nota em "Resultados na amostra"), DuckDB read-only na função Python,
CORS do site, ficha com "Como sabemos disso?", grafo e "perguntar" no navegador, também em emulação de celular
(375 px, sem rolagem horizontal). **Falta** o teste em um celular de verdade. Os CPFs são pseudonimizados, mas os nomes continuam na base (ADR-006). Mapa de
relações: o painel mostra as ligações nos dois sentidos e os municípios usam o nome da votação do TSE (2 de 185
seguem como código). Falta: cadastro da Receita no painel (só 36 das 1.598 empresas o têm) e link para a fonte oficial.

## Windows
- `make test` passa sem ajustes de encoding ou fuso (`tzdata` entrou como dependência só no Windows).
- Sem `make` instalado, rode os comandos do `Makefile` direto com `uv run ...`.
- Clone em um caminho curto (caminho longo falha com "Filename too long").

E2E no Windows (2026-11-24), no Edge instalado (`channel: "msedge"`), com a amostra completa: 50 casos aprovados e
2 pulados de propósito (desktop e 375px). Não foi uma única rodada limpa: em paralelo houve timeouts (máquina
sobrecarregada ou suspensa); com `--workers=1` restaram 3 falhas do mesmo tipo, resolvidas com `--last-failed`
(2 passaram, 1 é pulo intencional).

## Fonte RFB indisponível
Se a BrasilAPI responder 5xx ou timeout para um CNPJ mesmo após as tentativas, ele vai para a chave `indisponiveis`
(com aviso no log e no relatório do pipeline, em `rfb.indisponiveis`) e o lote segue; a empresa fica sem dados da
Receita. Com 3 CNPJs seguidos sem resposta a ingestão aborta (queda do serviço ou da rede). 429 persistente e 4xx
continuam abortando.

## Regra de ouro
Não alterar `contracts/` sem ADR (ver `docs/adr/`). Regras novas: YAML + predicado em `engine/predicates/`.
