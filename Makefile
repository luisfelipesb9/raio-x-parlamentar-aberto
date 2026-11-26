.PHONY: setup ingest infer test dev lint sample sample-publico deploy-check verifica checa-pii seed-demo demo
setup:
	uv sync
ingest:
	uv run python -m ingest.pipeline
infer:
	uv run python -m engine.run
test:
	uv run pytest -q
lint:
	uv run ruff check .
dev:
	uv run uvicorn api.main:app --reload
sample:
	uv run python -m ingest.pipeline --fontes camara,ceap,cgu,tse,opensanctions,rfb --uf MG --ano 2024 --amostra 20 --max-votacoes 145 --reusar-raw --limite-rfb 50 --detalhar-deputados --incluir-proposicoes --max-proposicoes 300 --db data/sample/raio_x_sample.duckdb
	RAIO_X_DB=data/sample/raio_x_sample.duckdb uv run python -m engine.run
# Base pública: CPF de terceiros pseudonimizado (HMAC). Exige RAIO_X_ID_SALT no ambiente (nunca no repo).
sample-publico:
	uv run python -m ingest.pipeline --fontes camara,ceap,cgu,tse,opensanctions,rfb --uf MG --ano 2024 --amostra 20 --max-votacoes 145 --reusar-raw --limite-rfb 50 --detalhar-deputados --incluir-proposicoes --max-proposicoes 300 --pseudonimizar --db data/sample/raio_x_publico.duckdb
	RAIO_X_DB=data/sample/raio_x_publico.duckdb uv run python -m engine.run
	uv run python -m ingest.varredura --db data/sample/raio_x_publico.duckdb
# Recalcula governismo e CEAP direto dos brutos e confronta com banco/motor; grava docs/relatorio/verificacao.md.
# Banco: $RAIO_X_DB (padrão: a amostra). Opções: `make verifica ARGS="--gerar-manifesto --online"`.
verifica:
	RAIO_X_DB=$${RAIO_X_DB:-data/sample/raio_x_sample.duckdb} uv run python -m scripts.verifica $(ARGS)
# Antes de publicar: só a base pública, sem CPF íntegro de terceiros, e nenhum outro .duckdb na árvore.
deploy-check:
	uv run python -m ingest.deploy_check --raiz . --publico data/sample/raio_x_publico.duckdb
# Reprova CPF íntegro (fora da allowlist de scripts/checa_pii.py) e segredos óbvios nos arquivos versionados.
checa-pii:
	uv run python -m scripts.checa_pii
# Demo OFFLINE: banco 100% fictício (6 deputados inventados), sem rede e sem dados reais.
seed-demo:
	uv run python -m scripts.seed_demo
demo: seed-demo
	@echo ""
	@echo "Demo pronta em data/sample/raio_x_demo.duckdb (DADOS FICTÍCIOS PARA DEMONSTRAÇÃO). Agora, em dois terminais:"
	@echo ""
	@echo "  1) API (na raiz do repositório):"
	@echo "     RAIO_X_ID_SALT=demo-ficticio RAIO_X_DB=data/sample/raio_x_demo.duckdb uv run uvicorn api.main:app --port 8000"
	@echo "  2) Site (instale uma vez com: pnpm --dir web install):"
	@echo "     pnpm --dir web dev     # abra http://localhost:3000 (a API padrão é http://localhost:8000)"
	@echo ""
	@echo "Passo a passo e o que ver: docs/demo.md"
