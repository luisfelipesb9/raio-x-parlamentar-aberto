# ingest/
Orquestra fetch → normalize → resolve → upsert. Dono: Luis.

```
uv run python -m ingest.pipeline --fontes camara,ceap,cgu,tse,opensanctions,rfb \
    --uf MG --ano 2024 --amostra 20 --limite-rfb 50 --reusar-raw --max-votacoes 145 \
    --db data/sample/raio_x_sample.duckdb
```
- `--uf` / `--amostra N`: escopo = os N primeiros deputados (por id) da UF. Só entra o que é atribuível a eles.
- Cada fonte recebe só os argumentos que o seu `fetch` aceita (`montar_kwargs` lê a assinatura).
- Banco: `--db` > `$RAIO_X_DB` > `data/raio_x.duckdb`.
- Cada passo apaga o que vai reafirmar antes de regravar (re-executar não deixa chave velha nem duplica).
- Rode tudo na MESMA execução quando possível: a resolução enxerga os 600+ deputados (homônimos fora do escopo) só quando `camara` está na execução; sozinhas, as demais fontes resolvem contra o que já está no banco.

## resolve/
Funções puras (fatos entram; fatos enriquecidos + `EntityLink` + `Ambiguidade` saem):

| função | liga | método / cf |
|---|---|---|
| `resolver_candidaturas` | candidatura → deputado (`deputado_id`) | cpf 1.0; nome+UF único 0.8; desempate por partido 0.7; ambíguo não liga |
| `resolver_emendas` | emenda → deputado (`deputado_id`) | nome do autor único 0.8 |
| `resolver_peps` | pep → deputado (só link) | nome + CPF mascarado 0.95; nome civil 0.7; nome parlamentar 0.5 |
| `resolver_cnpj` | despesa_ceap → empresa / sancao | cnpj 1.0 |

`deputado_id` só é gravado no fato quando cf ≥ 0.7. CPF íntegro diferente descarta o par (homonímia). Ambiguidades vão para a tabela `entity_ambiguity`.

## Flags da Onda 4
- `--incluir-proposicoes [--max-proposicoes 300]`: `proposicao` + `autoria` (PL, PEC, PLP da janela) só dos deputados do escopo; alimenta a R05.
- `--detalhar-deputados`: `cpf` e `nome_civil` via `/deputados/{id}` (só o escopo); candidatura passa a ligar por CPF (cf 1.0).
- `--pseudonimizar` (exige `RAIO_X_ID_SALT` no ambiente, nunca no repositório): CPF íntegro de terceiros vira `hmac:<32 hex>` (HMAC-SHA256). Vale para `doacao.doador_cpf_cnpj`, `socio.cpf_cnpj`, `despesa_ceap.cpf`, `sancao.cpf`, `pep.cpf/cpfs` e CPF solto em texto livre (ex.: `despesa_ceap.fornecedor`). No doador grava também `doador_cpf_visivel` (6 dígitos, posições 4–9) para a R06b seguir descartando homônimos. CPF de deputado/candidato (ADR-002), CPF já mascarado e CNPJ ficam como estão. Mesmo CPF + mesmo sal = mesmo hash; trocar o sal muda todos os hashes (guarde o sal fora do repo).
- `python -m ingest.varredura --db X.duckdb`: varre fatos e findings atrás de CPF íntegro (dígito verificador válido) fora de deputado/candidato; sai com 1 se achar. Nunca imprime o valor.

### Cuidados com a base pública
- A pseudonimização acontece em `Pipeline._gravar` (ponto único): nada é gravado sem passar por ela. Sócio com CPF íntegro ganha `cpf_visivel` (6 dígitos, posições 4–9), como o doador ganha `doador_cpf_visivel`.
- `--pseudonimizar` sobre um banco JÁ existente e não pseudonimizado **deixa resíduo** (fatos de passos/chaves que esta execução não regrava continuam com CPF íntegro). Gere a base pública sempre em arquivo novo (`make sample-publico` já parte de um arquivo novo; apague o antigo antes).
- `make deploy-check` reprova se houver CPF íntegro de terceiro na base pública (fatos, findings, `entity_link`, `entity_ambiguity`) ou qualquer outro `.duckdb`/`.wal` na árvore. Não olha `data/raw` (JSON bruto das fontes, que pode ter CPF): não envie essa pasta.
