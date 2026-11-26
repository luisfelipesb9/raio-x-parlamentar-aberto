# Plano — "Raio-X Parlamentar": Sistema Especialista sobre deputados federais

## Contexto
Trabalho final de Sistemas Especialistas (Unimontes, BSI). Objetivo: plataforma que documenta **tudo que é público** sobre um deputado federal (mandato, votos, proposições, gastos CEAP, emendas, financiamento TSE, empresas/QSA, sanções/PEP) e **correlaciona** entidades num grafo navegável estilo Obsidian, legível por leigos.

**Existe open source que já faz isso?** Não por completo. Serenata de Amor (só CEAP, execução manual), Parlametria/Leggo (arquivado desde 02/2023), Basômetro (parado desde 2020), Perfil Político (inativo), Radar Parlamentar (só votações). Decisão: **construir do zero reaproveitando coletores ativos** (DadosAbertosBrasil 3.0.1, serenata-toolbox, OpenSanctions br_pep, ETL aphonsoar CNPJ, Base dos Dados) e citar os legados como referência metodológica no relatório.

## Ementa assumida → onde cada conceito aparece no produto
| Conceito de SE | Implementação |
|---|---|
| Base de fatos | DuckDB local normalizado (deputado, votação, voto, proposição, despesa, emenda, doação, empresa, sócio, sanção) |
| Base de conhecimento (regras SE…ENTÃO) | Arquivos YAML versionados em `knowledge/rules/`, separados do código (permite falar em *aquisição de conhecimento*) |
| Motor de inferência | Encadeamento **progressivo** (gera todos os achados após cada ingestão) + **regressivo** (responde "o deputado X tem conflito de interesse?" provando subobjetivos) |
| Incerteza | **Fatores de certeza MYCIN** (CF ∈ [-1,1], combinação CF1+CF2(1-CF1)); penalização por homonímia/CPF mascarado |
| Módulo de explicação | "**Como** cheguei aqui" (trilha de regras + IDs de nota fiscal/emenda/votação) e "**Por que** pergunto/considero isso" |
| Guardrails epistêmicos | Regras que *bloqueiam* conclusões: votação simbólica ≠ voto individual; processo sem trânsito em julgado ≠ culpa; média partidária só como contexto |
| Engenharia do conhecimento | Metodologias de Radar da República, Basômetro, Radar do Voto, Elas no Congresso como "especialistas" fonte; documento de entrevista/validação |

Regras iniciais (da pesquisa): Produção Legislativa Ponderada, Taxa de Governismo, Guardrail Votação Simbólica, Fornecedor Sancionado (CNPJ×CEIS/CNEP), Circuito Doador‑Sócio‑Fornecedor (CF rebaixado se CPF mascarado), Concentração Eleitoral de Emendas, Outlier de CEAP (estilo Rosie), Lacuna de Dados/Presunção de inocência.

## System design

### Princípios (valem para todo o time)
1. **Camadas com dependência em uma direção só**: `sources → ingest → facts → engine → api → web`. Nenhuma camada importa a de cima.
2. **Contratos antes de código**: todo dado que cruza camadas é um schema versionado em `contracts/` (Pydantic → exporta JSON Schema → gera tipos TypeScript para o web). Mudou contrato = ADR + bump de versão.
3. **Conhecimento é dado, não código**: regras em YAML; adicionar regra nova não exige tocar no motor.
4. **Um conector = um arquivo com a mesma interface** (`Source.fetch() → raw`, `Source.normalize(raw) → [Fact]`). Nova fonte (Senado, TCU, município) = novo plugin, sem mexer no resto.
5. **Idempotência e rastreabilidade**: toda linha de fato guarda `fonte`, `id_oficial`, `url`, `coletado_em`, `hash`. Reprocessar não duplica.
6. **Leitura nunca bate em API externa**: só no banco (limites Câmara 100 itens/req, Senado 10 req/s).

### Visão de componentes
```
┌─ sources/ (plugins por órgão) ─┐   raw/ (parquet imutável, data lake local)
│ camara  ceap  tse  cgu  rfb    │──►  ▼
│ opensanctions  ...             │   ingest/pipeline  (normaliza + resolve entidades CPF/CNPJ)
└────────────────────────────────┘     ▼
                                    facts DB  (DuckDB no MVP → PostgreSQL no deploy; mesma camada repo/)
                                       ▼
            knowledge/rules/*.yaml ─► engine/ (forward + backward chaining, CF MYCIN, guardrails)
                                       ▼
                                    findings + explanations (tabelas materializadas)
                                       ▼
                                    api/ (FastAPI, read-only, OpenAPI)  ─►  web/ (Next.js)
                                       ▲
                                    graph/ (projeção nós/arestas para o grafo estilo Obsidian)
```
- **Chaves**: CPF do candidato (TSE restaurou em 07/2026) liga TSE↔id_deputado; CNPJ 14 dígitos liga CEAP/TSE/emendas↔RFB↔CEIS. Tabela `entity_link` guarda cada ligação com CF próprio (homonímia vira incerteza explícita).
- **Medallion simples**: `raw` (como veio) → `staging` (tipado) → `facts` (entidades resolvidas) → `findings` (inferências). Facilita debug e explicar no relatório.

### Caminho de escala (documentado, não implementado no MVP)
| Hoje (TCC) | Quando crescer |
|---|---|
| DuckDB arquivo único | PostgreSQL (+ Apache AGE ou Neo4j se o grafo pesar) — troca só em `repo/` |
| Cron/`make ingest` | Orquestrador (Prefect/Dagster) com um job por `source` |
| Motor roda em lote após ingestão | Fila de eventos: fato novo → reavalia só regras afetadas (índice regra↔tipo de fato) |
| Só deputados federais | Senado/estados = novos plugins em `sources/`, regras reaproveitadas |
| API read-only com cache | CDN/ISR na ficha (página muda 1×/dia) |

### Onboarding de quem entra no projeto
- `CONTRIBUTING.md` na raiz (e o mapa em `docs/mapa-do-repositorio.md`): mapa de pastas, regra de dependência, comandos (`make setup | ingest | infer | test | dev`), "como adicionar uma fonte" e "como adicionar uma regra" em passo a passo.
- `README.md` curto em **cada** pasta: responsabilidade, entradas, saídas, dono.
- `docs/adr/` (decisões), `docs/glossario.md` (CEAP, emenda Pix, CF…), `docs/arquitetura.md` com o diagrama acima.
- Monorepo: `pyproject.toml` (uv) para Python, `pnpm` para web, `Makefile` como interface única; CI (GitHub Actions) roda lint, testes e valida contratos e YAML de regras.
- Convenções: conventional commits, 1 PR por tarefa, branch `luis/*` e `pedro/*`, CODEOWNERS por pasta.

## Experiência do leitor leigo (web/)
1. **Busca** por nome/foto/UF → **Ficha do deputado** em linguagem simples: "Quem é", "Como vota" (governismo em barra), "Quanto gasta" (CEAP vs média), "Para onde mandou dinheiro" (mapa de emendas), "Quem financiou", "Alertas" (cartões com semáforo de certeza: Alta/Média/Indício).
2. Cada alerta tem botão **"Como sabemos disso?"** → trilha de explicação com links para o documento oficial.
3. **Grafo estilo Obsidian** (Cytoscape.js/Sigma): nós = deputado, partido, empresa, município, proposição; arestas = votou junto, doou, recebeu, sócio de. Clique em nó → painel lateral com "backlinks" (todas as menções). Filtro por tipo de relação e período.
4. **Comparar** dois deputados (afinidade de votos, fornecedores em comum).
5. Glossário embutido (tooltip em termos como CEAP, emenda Pix, votação nominal).

## Estrutura do repositório e divisão (Luis faz a 1ª metade, Pedro Rodrigues finaliza a 2ª)
```
raio-x-parlamentar/
  CONTRIBUTING.md  README.md  Makefile  CODEOWNERS  .github/workflows/
  contracts/     Fact, Entity, Finding, Explanation, GraphNode/Edge (Pydantic + JSON Schema)  [LUIS]
  sources/       base.py (interface) + camara/ ceap/ tse/ cgu/ rfb/ opensanctions/            [LUIS]
  ingest/        pipeline.py, resolve/ (CPF/CNPJ, homonímia → entity_link com CF)             [LUIS]
  repo/          acesso ao banco (DuckDB agora, Postgres depois), migrations/                 [LUIS]
  engine/        rule_loader, forward, backward, certainty (MYCIN), guardrails, explain       [LUIS núcleo]
  knowledge/rules/*.yaml   4 primeiras regras [LUIS] · 4 restantes [PEDRO]
  graph/         projeção de fatos/findings em nós e arestas                                  [PEDRO]
  api/           FastAPI: /deputados, /deputados/{id}, /grafo, /findings, /explicar           [PEDRO]
  web/           Next.js: busca, ficha, grafo, comparação, glossário (tipos gerados de contracts/) [PEDRO]
  tests/         unit/ (motor, regras) [LUIS] · e2e/ [PEDRO]
  docs/          adr/, arquitetura.md, glossario.md, HANDOFF.md, relatorio/                   [ambos; relatório PEDRO]
```
**Metade 1 — Luis (fundação + raciocínio)**
1. Scaffold repo, `docs/ADR-001` (decisões acima), CONTRIBUTING com contrato de interfaces.
2. Ingestão Câmara (deputados, votações nominais + orientação, proposições) e CEAP; TSE candidaturas/receitas 2022; emendas CGU; CEIS/CNEP; OpenSanctions PEP; QSA via BrasilAPI só para CNPJs que aparecem (evita os 17 GB).
3. Schema DuckDB + resolução de entidades.
4. Motor: loader YAML, forward chaining, CF MYCIN, trilha de explicação; 4 regras (Governismo, Votação Simbólica, Fornecedor Sancionado, Outlier CEAP) com testes.
5. **Entrega de handoff**: `docs/HANDOFF.md` + contrato JSON de `Finding` e `Explanation` + DB populado de amostra (ex.: 20 deputados).

**Metade 2 — Pedro (inteligência restante + produto)**
6. Regras restantes (Produção Ponderada, Circuito Doador‑Sócio, Concentração de Emendas, Lacuna/Presunção) e backward chaining para perguntas.
7. API FastAPI sobre o contrato.
8. Frontend: ficha leiga, grafo, explicação, comparação, glossário.
9. Validação: comparar achados com Basômetro/Radar do Voto/Serenata em casos conhecidos (precisão percebida), teste com usuários leigos.
10. Relatório acadêmico + apresentação.

Contrato de fronteira (definido por Luis na etapa 1, para Pedro não depender do código interno):
`Finding {id, deputado_id, regra, conclusao_texto_simples, cf, nivel, evidencias:[{tipo, id_oficial, url}], guardrails_aplicados}`.

## Verificação
- `pytest` no motor: cada regra com caso positivo, negativo e guardrail (ex.: votação simbólica nunca gera voto individual; CPF mascarado → CF ≤ 0,4).
- Rodar ingestão para amostra e conferir 3 achados manualmente contra o portal oficial.
- E2E (Playwright) da ficha e do botão "Como sabemos disso?".
- Teste de leitura com 3 pessoas leigas: conseguem explicar um alerta em 1 frase?

## Pendências
- Ementa oficial da Unimontes e última atividade do professor (usuário vai enviar) — ajustar a tabela de conceitos se exigirem ferramenta específica (CLIPS/Prolog/Experta).
