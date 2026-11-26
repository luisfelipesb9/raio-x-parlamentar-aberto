# Ingest nacional: TSE por UF e CEAP de vários anos

Parte da Onda 4 (513 deputados). Contexto e números de volume em [pesquisa.md](pesquisa.md).

## TSE, uma UF por vez

Sem `--uf` nem `--amostra`, `_passo_tse` usa `TseSource.fetch_por_uf` em vez de `fetch(uf=None)`
(que percorre as 27 UFs e as devolve juntas em memória). Para cada UF: lê o membro da UF dos zips
(HTTP Range), grava `data/raw/tse/tse_{ano}_{UF}.json`, normaliza, resolve candidaturas, grava no
banco e **solta** a UF antes de ler a próxima. Com escopo (`--uf MG`, `--amostra N`) nada muda:
continua `fetch(uf=...)`.

- A regravação é por UF: `candidatura` é apagada só da UF em processamento (`ano` + `uf`), então
  refazer uma UF não apaga as outras.
- **Retomada.** `--reusar-raw` lê de `data/raw/tse/` a UF cujo bruto já está completo (mesmo ano e
  UF, todos os conjuntos, lista de municípios do IBGE), sem ler o membro do zip nem consultar o
  IBGE; bruto ausente, corrompido ou incompleto é baixado de novo. A UF reaproveitada é
  normalizada e regravada de novo (barato e idempotente; cobre o caso de a rodada ter caído entre
  baixar e gravar). Sem UF explícita ainda se abre o diretório dos zips (alguns KB por Range) para
  saber quais UFs existem.

### Memória (tracemalloc, fixture sintética)

`tests/unit/test_tse_memoria.py` (`pytest -s` mostra os números): 8 UFs fictícias de 4.800 linhas
de votação agregadas cada, zips falsos.

| modo | pico |
|---|---|
| `fetch()` acumulado (8 UFs juntas) | 35.516 KiB |
| pipeline por UF, 4 UFs | 10.270 KiB |
| pipeline por UF, 8 UFs | 10.269 KiB |

O pico do modo por UF **não cresce com o número de UFs**. Sem os `del` que soltam a UF anterior
(no pipeline e no gerador) o pico sobe para 13,8 MiB, porque a UF anterior fica viva enquanto a
próxima é lida. Isto é medida de fixture: o pico de uma UF grande (SP, ~270 mil linhas de votação
agregadas, HIPÓTESE) não foi medido; extrapole pelos ~950 B por linha agregada (inclui
candidatos e receitas da UF) do modo acumulado, ou seja ~250 MB só do bruto de SP, mais o
buffer fixo de leitura (~6 MiB).

## CEAP

O pipeline baixa e lê **cada ano uma vez**, para qualquer número de deputados: o filtro por
escopo é um conjunto em memória aplicado depois da leitura (`tests/unit/test_ceap_anos.py`
confirma 1 download e 1 leitura com 513 deputados).

`--anos-ceap 2023,2024` processa vários anos em sequência (um zip por ano, um ano em memória por
vez) e vale no lugar de `--ano`. `relatorio["ceap"]["por_ano"]` traz a contagem por ano.

- O `delete_facts(ano_data=ano)` apaga também os fatos **sem data** (não sabe de que carga são).
  Numa rodada com vários anos, os sem data dos anos anteriores são regravados depois do delete do
  ano seguinte; rodar `--ano 2024` sozinho depois de `--ano 2023` ainda apaga os sem data de 2023
  (limitação antiga, só vista aqui).
- Memória de um ano nacional (medida com 40 mil linhas sintéticas e extrapolada): ~1,7 KB por
  linha só do bruto e ~3,4 KB até o fim do `normalize`, ou seja **~0,8 a 1,0 GB de pico** para
  230 a 281 mil linhas. Cabe numa máquina comum e no runner do GitHub (16 GB); se for um limite,
  o próximo passo é normalizar e gravar por lote de deputados (linhas idênticas ficam juntas
  porque têm o mesmo `idDeputado`, então o sufixo `-2`, `-3` da chave continua correto).
- `scripts/verifica.py` compara com **um** zip (`Ano-*.json.zip`); com vários anos no banco ele
  precisa somar os anos antes de conferir o total por deputado (fora desta mudança).
