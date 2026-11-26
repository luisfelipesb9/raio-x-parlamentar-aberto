# Como contribuir

Obrigado pelo interesse. Leia também o [Código de Conduta](CODE_OF_CONDUCT.md) e a
[política de uso e correção](docs/politica-de-uso-e-correcao.md). O mapa completo do repositório está
em [docs/mapa-do-repositorio.md](docs/mapa-do-repositorio.md).

## Regra de ouro: dependência em uma direção só
```
sources → ingest → repo(fatos) → engine → graph → api → web
                 ↑ contracts/ é usado por todos, não importa ninguém
```
- Uma camada **nunca** importa a camada à sua direita.
- Tudo que atravessa camadas é um tipo de `contracts/`.
- `api/` e `web/` só **leem** o banco e nunca chamam API externa. Exceção: a API pode ler
  `data/raw/manifest.json` ([ADR-009](docs/adr/ADR-009-api-le-manifesto-do-bruto.md)). Outras exceções: [ADR-005](docs/adr/ADR-005-excecao-direcao-dependencia.md).

## Comandos (interface única: Makefile)
```
make setup          # instala dependências Python (uv)
make ingest         # coleta fontes e grava em data/raw e no banco
make infer          # roda o motor e materializa findings
make sample         # amostra de 20 deputados de MG + motor
make sample-publico # amostra pseudonimizada (HMAC) + varredura de CPF
make seed-demo      # gera o banco fictício da demonstração (offline)
make demo           # seed-demo + instruções para subir API e site
make dev-demo       # API sobre o banco da demo (sal e banco já definidos)
make test           # pytest
make lint           # ruff
make verifica       # recalcula governismo e CEAP dos brutos e confronta com o banco
make deploy-check   # confere que só a base pública seria publicada
make checa-pii      # guarda de dados pessoais
make dev            # só a API (exige RAIO_X_ID_SALT e, para outro banco, RAIO_X_DB); o site roda à parte: `pnpm dev` em web/
```
Pare a API antes de `make ingest` ou `make infer` (lock de escrita do DuckDB).

## Como adicionar uma FONTE de dados
1. Crie `sources/<nome>/source.py` com uma classe que herda `sources.base.Source`.
2. Implemente `fetch()` (salva o bruto em `data/raw/<nome>/`) e `normalize(raw) -> list[Fact]`.
3. Todo `Fact` precisa de `fonte`, `id_oficial` e `url` (rastreabilidade obrigatória).
4. Registre em `sources/__init__.py::REGISTRY` e escreva teste com fixture JSON em `tests/unit/fixtures/`.

## Como adicionar uma REGRA
1. Crie `knowledge/rules/RNN_nome.yaml` seguindo [`_schema.md`](knowledge/rules/_schema.md).
2. Use predicados registrados no pacote `engine/predicates/`. Para um predicado novo, crie
   `engine/predicates/<regra>.py` com `@predicate("nome")` (ou `@guardrail`) e importe em `engine/predicates/__init__.py`.
   Regra composta não tem `predicado` e usa `requer: [objetivo]` (só roda no encadeamento regressivo).
3. Defina `cf` (0 a 1) e, se houver incerteza de dado, `penalidades`.
4. Teste em `tests/unit/test_rules.py` (ou `test_rules_r05_r08.py`): caso positivo, negativo e guardrail.

O motor não precisa mudar para uma regra nova.

## Como propor mudança de contrato
Mudou algo em `contracts/`? Escreva um ADR novo em `docs/adr/` (numeração sequencial, status
`Proposto`, e atualize o [índice](docs/adr/README.md)) e aumente `CONTRACT_VERSION` em
`contracts/models.py`. Exemplo: [ADR-007](docs/adr/ADR-007-contrato-v0-2-0.md).

## Convenções
- Python 3.11+ suportado, 3.12 recomendado, `ruff` e `pytest`. No site, em `web/`: `pnpm lint`, `pnpm test`, `pnpm build` e `pnpm e2e`.
- Commits no padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/), por exemplo `feat(engine): nova regra R10`.
- Branches com o prefixo do autor, por exemplo `nome/assunto`. Uma tarefa por pull request, com o checklist do modelo preenchido.

## Dados pessoais e guardrails (não negociáveis)
- **Nunca** versione dados reais com CPF. A pasta `data/` é ignorada pelo git; gere os bancos localmente.
- Para publicar uma base, use `make sample-publico` (CPF trocado por HMAC) e `make deploy-check`.
- Antes de abrir o PR, rode `make checa-pii`.
- Processo sem condenação definitiva não é culpa; votação simbólica não é voto individual; texto para o leitor em
  linguagem simples, sempre com nível de certeza e link para a fonte oficial.
