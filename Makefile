.PHONY: setup ingest infer test dev lint sample sample-publico deploy-check
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
# Antes de publicar: só a base pública, sem CPF íntegro de terceiros, e nenhum outro .duckdb na árvore.
deploy-check:
	uv run python -m ingest.deploy_check --raiz . --publico data/sample/raio_x_publico.duckdb
