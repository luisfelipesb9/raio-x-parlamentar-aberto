.PHONY: setup ingest infer test dev lint sample sample-publico publicar ingest-nacional publicar-nacional deploy-check deploy-check-nacional verifica checa-pii seed-demo demo dev-demo
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
# A origem pseudonimizada (com todos os fatos) fica em ORIGEM, FORA da árvore (padrão: $TMPDIR ou /tmp), para o
# `make deploy-check` não reprová-la; o arquivo enxuto que sobe para a Vercel fica em DESTINO.
ORIGEM ?= $(or $(TMPDIR),/tmp)/raio_x_publico_origem.duckdb
DESTINO ?= data/sample/raio_x_publico.duckdb
sample-publico:
	uv run python -m ingest.pipeline --fontes camara,ceap,cgu,tse,opensanctions,rfb --uf MG --ano 2024 --amostra 20 --max-votacoes 145 --reusar-raw --limite-rfb 50 --detalhar-deputados --incluir-proposicoes --max-proposicoes 300 --pseudonimizar --db $(ORIGEM)
	RAIO_X_DB=$(ORIGEM) uv run python -m engine.run
	uv run python -m ingest.varredura --db $(ORIGEM)
	$(MAKE) publicar
# Banco enxuto para a API pública (ADR-011): grafo, inferência e contagens materializados, só os fatos que a API
# ainda lê, sem chave primária; reprova se sobrar CPF íntegro de terceiro. Refaz o DESTINO a cada rodada.
# Exige o mesmo RAIO_X_ID_SALT da pseudonimização.
publicar:
	mkdir -p $(dir $(DESTINO))
	rm -f $(DESTINO) $(DESTINO).wal
	uv run python -m publicar --origem $(ORIGEM) --destino $(DESTINO)
# Onda 4: os deputados em exercício (sem --uf/--amostra e sem teto de votações nem de proposições), na origem
# pseudonimizada do nacional (ORIGEM_NACIONAL, fora da árvore e separada da ORIGEM da amostra; exige RAIO_X_ID_SALT). TSE uma UF por vez, CEAP de vários anos, votos pelo dump
# anual. É uma coleta longa e pesada em rede: rode com calma (nada é medido nem prometido aqui). Retoma de onde caiu
# (checkpoint em data/raw/camara/parcial/); ajuste por variável (`make ingest-nacional ANOS_CEAP=2024`) ou por ARGS
# (`ARGS="--reusar-raw --reusar-dumps"`: o bruto só é reaproveitado se o escopo gravado nele servir).
ORIGEM_NACIONAL ?= $(or $(TMPDIR),/tmp)/raio_x_nacional_origem.duckdb
DESTINO_NACIONAL ?= data/nacional/raio_x_publico.duckdb
ANOS_CEAP ?= 2023,2024
JANELA_INICIO ?= 2025-01-01
JANELA_FIM ?= 2025-12-31
FONTE_VOTOS ?= dump
LIMITE_RFB ?= 50
ingest-nacional:
	uv run python -m ingest.pipeline --nacional --fontes camara,ceap,cgu,tse,opensanctions,rfb --anos-ceap $(ANOS_CEAP) --janela-inicio $(JANELA_INICIO) --janela-fim $(JANELA_FIM) --fonte-votos $(FONTE_VOTOS) --limite-rfb $(LIMITE_RFB) --detalhar-deputados --incluir-proposicoes --pseudonimizar --db $(ORIGEM_NACIONAL) $(ARGS)
# Depois do `ingest-nacional`: motor, varredura de CPF e o arquivo enxuto em DESTINO_NACIONAL (data/nacional/, ignorado
# pelo git; não sobrescreve o artefato da amostra). Para subir à Vercel, o arquivo tem de estar em data/sample/raio_x_publico.duckdb
# (único caminho que o .vercelignore reabre): copie-o para lá, tirando a amostra do lugar antes (o deploy-check reprova outro .duckdb).
publicar-nacional:
	RAIO_X_DB=$(ORIGEM_NACIONAL) uv run python -m engine.run
	uv run python -m ingest.varredura --db $(ORIGEM_NACIONAL)
	$(MAKE) publicar ORIGEM=$(ORIGEM_NACIONAL) DESTINO=$(DESTINO_NACIONAL)
# Como `deploy-check`, mas sobre a base nacional; reprova se a base da amostra (ou qualquer outro .duckdb) estiver na árvore.
deploy-check-nacional:
	uv run python -m ingest.deploy_check --raiz . --publico $(DESTINO_NACIONAL)
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
	@echo "  1) API (na raiz do repositório):   make dev-demo"
	@echo "  2) Site (instale uma vez com: pnpm --dir web install):"
	@echo "     pnpm --dir web dev     # abra http://localhost:3000 (a API padrão é http://localhost:8000)"
	@echo ""
	@echo "Passo a passo e o que ver: docs/demo.md"
# Sobe a API sobre o banco da demo (sal fixo e público, só da demonstração fictícia: o mesmo de scripts/seed_demo.py).
dev-demo:
	@test -f data/sample/raio_x_demo.duckdb || { echo "Banco da demo não encontrado em data/sample/raio_x_demo.duckdb: rode 'make seed-demo' (ou 'make demo') primeiro."; exit 1; }
	RAIO_X_ID_SALT=sal-fixo-da-demonstracao RAIO_X_DB=data/sample/raio_x_demo.duckdb uv run python -m uvicorn api.main:app --reload
