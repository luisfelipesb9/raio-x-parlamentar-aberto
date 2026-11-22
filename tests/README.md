# tests/
unit/ (Luis): motor, regras R01–R09, resolução, API, grafo e fontes com fixtures (`make test`). e2e/ (Pedro): Playwright da web.

## Fixtures
O formato e os valores estruturais (ids, datas, valores, CNPJ de empresas) das fixtures em `unit/fixtures/` vêm dos arquivos oficiais; os **nomes de pessoas físicas, os CPFs mascarados e as datas de nascimento são fictícios** (e o OpenSanctions é 100% sintético: a licença dos dados reais, CC BY-NC, não permite redistribuição). `make checa-pii` reprova CPF íntegro e segredos nos arquivos versionados; um CPF sintético de teste só passa se estiver na allowlist comentada de `scripts/checa_pii.py`.
