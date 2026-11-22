.PHONY: setup ingest infer test dev lint
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
