# Ingest nacional: TSE por UF e CEAP de vários anos

Parte da Onda 4 (513 deputados). Contexto e números de volume em [pesquisa.md](pesquisa.md).

## Modo nacional (`--nacional`, `make ingest-nacional`)

`python -m ingest.pipeline --nacional ...` junta o que a Onda 4 precisa: todos os deputados em exercício (sem `--uf`/`--amostra`;
combinar é erro), sem teto de votações nem de proposições (`--max-votacoes`/`--max-proposicoes` só valem se dados; os tetos de 30 e
300 continuam sendo o padrão do modo amostra), TSE por UF e CEAP de vários anos (`--anos-ceap`). O Makefile acrescenta o resto
(`make ingest-nacional`: dump anual de votos, detalhe dos deputados, proposições, pseudonimização, saída em `$(ORIGEM_NACIONAL)`); `make
publicar-nacional` roda o motor, a varredura de CPF e o `publicar` depois, com origem e destino próprios
(`ORIGEM_NACIONAL`, padrão `$TMPDIR/raio_x_nacional_origem.duckdb`; `DESTINO_NACIONAL`, padrão `data/nacional/raio_x_publico.duckdb`),
sem tocar na origem nem no arquivo público da amostra. `data/nacional/` é ignorado pelo git (`data/*`, `*.duckdb`) e **não** vai no deploy
da Vercel (o `.vercelignore` só reabre `data/sample/raio_x_publico.duckdb`): para subir a base nacional, MOVA-a (não copie: o `deploy-check` reprova um segundo `.duckdb` na árvore) para esse caminho depois de
tirar a da amostra do lugar. `make deploy-check-nacional` confere o destino nacional (e reprova se houver outro `.duckdb` na árvore). `make sample` e `make sample-publico` não mudam
(20 deputados de MG, teto de 145 votações e de 300 proposições).

Flags da Câmara repassadas ao `CamaraSource.fetch`: `--legislatura-completa` (878 da legislatura em vez dos 513 em exercício),
`--fonte-votos {api,dump}`, `--reusar-dumps` e `--retomar`/`--sem-retomar` (padrão: retomar o checkpoint; vale também para as
proposições). No modo nacional as proposições são pedidas pela janela inteira, sem filtrar por autor (o `fetch_proposicoes` sem
`deputado_ids`); só ficam proposição e autoria de deputado conhecido.

### Quem entra: a lista de deputados conhecidos

Sem escopo (`--nacional` ou uma rodada sem `--uf`/`--amostra`), o pipeline só grava voto, autoria e despesa de quem está entre os deputados
conhecidos. Antes, voto de quem não está na lista (ex-deputado, suplente que já saiu; o dump de votos traz todo mundo que votou na janela)
virava fato órfão e podia gerar achado sobre quem não tem ficha. O filtro vale para voto, autoria, despesa CEAP, candidatura (`_restringir`), emenda (só fica a que liga a deputado),
links de PEP, o ranking de CNPJs da Receita (`--limite-rfb`) e `_ligar_cnpj`: todos passam por `_no_escopo`. Se o banco ainda não tem
deputados (rodada só de CEAP, TSE, CGU ou OpenSanctions, sem a Câmara antes), nada é filtrado e o pipeline avisa no log
(`ATENÇÃO: sem deputados no banco, nada filtrado`). Efeito: candidato que nunca foi deputado deixa de ser gravado (e, como o
`publicar` copia a candidatura inteira da origem, de ser publicado), o que vale para a origem gerada por esta versão; uma origem
antiga continua com o que já tinha. Com escopo (`--uf`, `--amostra`) vale o recorte de sempre. Os deletes pré-gravação do modo sem escopo não filtram por
deputado, então rodar de novo remove o voto órfão deixado por uma rodada antiga.

### `--reusar-raw` e o escopo gravado no bruto da Câmara

O `fetch` grava `_escopo` no `camara_<início>_<fim>.json`: `legislatura`, `legislatura_completa`, `janela`, `fonte_votos` e `max_votacoes`
(`None` = sem teto). Com `--reusar-raw` (ou `--detalhar-deputados`, que lê a lista de deputados do bruto), o pipeline só reaproveita o
arquivo se ele serve ao pedido: mesma legislatura completa ou não, mesma janela, mesma fonte de votos e teto igual ou menor que o gravado
(bruto sem teto serve a qualquer pedido; bruto de 145 votações não serve a um pedido sem teto). Se não serve, o pipeline avisa
(`ATENÇÃO: ... não reaproveitado: <motivo>; coletando de novo`) e coleta de novo, sobrescrevendo o arquivo. Bruto de antes do registro
(sem `_escopo`, possivelmente com a legislatura inteira) só serve à rodada de amostra, com aviso; numa rodada nacional é recusado. O
formato do bruto ganhou só esta chave (`normalize` a ignora). Os brutos do TSE já eram por UF e conferidos por ano e UF.

## TSE, uma UF por vez

Sem `--uf` nem `--amostra`, `_passo_tse` usa `TseSource.fetch_por_uf` em vez de `fetch(uf=None)`
(que percorre as 27 UFs e as devolve juntas em memória). Para cada UF: lê o membro da UF dos zips
(HTTP Range), grava `data/raw/tse/tse_{ano}_{UF}.json`, normaliza, resolve candidaturas, grava no
banco e **solta** a UF antes de ler a próxima. Com escopo (`--uf MG`, `--amostra N`) continua
`fetch(uf=...)`, uma chamada por UF do escopo.

- A regravação é por UF: `candidatura` é apagada só da UF em processamento (`ano` + `uf`), então
  refazer uma UF não apaga as outras.
- **`--reusar-raw` vale também com escopo** (é o que `make sample` passa): a UF com bruto completo
  em `data/raw/tse/` é lida do disco em vez de baixada de novo. É equivalente ao que o `fetch`
  gravou (o bruto só é aceito se for do mesmo ano e UF e tiver todos os conjuntos e os
  municípios do IBGE); a diferença é a mesma de sempre do flag: não vê atualização do TSE. Sem
  `--reusar-raw` baixa de novo.
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

- O `delete_facts(ano_data=ano)` apaga pela **data da nota**, e o zip de um ano traz notas de
  outro (dez/2023 dentro do zip de 2024). Deletar ano a ano apagaria nota que o zip anterior
  acabou de gravar; por isso, numa rodada com vários anos, os deletes de todos os anos acontecem
  juntos, antes de qualquer gravação (testes nas duas ordens, `tests/unit/test_ceap_anos.py`).
  Eles esperam o primeiro ano baixado e lido com despesas, então uma falha logo no início não apaga
  nada. Se um ano posterior falhar, os anos ainda não recarregados ficam sem despesas até repetir a
  rodada (idempotente). Os sem data também são apagados no delete (não dá para saber de que carga
  são) e regravados pelos zips da mesma rodada; rodar `--ano 2024` sozinho depois de `--ano 2023`
  ainda apaga os sem data de 2023 (limitação antiga).
- Memória de um ano nacional (medida com 40 mil linhas sintéticas e extrapolada): ~1,7 KB por
  linha só do bruto e ~3,4 KB até o fim do `normalize`, ou seja **~0,8 a 1,0 GB de pico** para
  230 a 281 mil linhas. Cabe numa máquina comum e no runner do GitHub (16 GB); se for um limite,
  o próximo passo é normalizar e gravar por lote de deputados (linhas idênticas ficam juntas
  porque têm o mesmo `idDeputado`, então o sufixo `-2`, `-3` da chave continua correto).
- `scripts/verifica.py` soma, por deputado, os zips `data/raw/ceap/Ano-*.json.zip` antes de conferir o total com o banco (cada
  zip é uma partição das despesas). O padrão são os zips **efetivamente ingeridos**: o banco não guarda de que zip veio cada
  despesa (e uma nota de dez/2023 vem no zip de 2024), então o `verifica` procura o maior conjunto de zips cuja soma fecha
  com o banco. Dois casos que a busca não distingue sozinha: (1) um zip **sobrando** em disco (nunca ingerido) e (2) um **ano que
  deveria ter entrado e não entrou** no banco. Nos dois o zip fica de fora da soma e vira uma linha "não verificado" ("não fecha com o
  banco; confirme com --anos-ceap"): não reprova, mas o relatório deixa de dizer que tudo foi conferido. Quem sabe quais anos ingeriu
  resolve com `--anos-ceap`, que fixa os anos (sem busca): com um ano que falta no banco, ele DIVERGE. Se nenhum conjunto fecha, soma
  todos e a divergência aparece. Zip ilegível ou de ano pedido e ausente é "não verificado", nunca "ok". A busca testa todos os
  subconjuntos, por isso só roda até 10 zips em disco (acima disso soma todos).
  Base nacional: `make verifica-nacional` (equivale a `RAIO_X_DB=$ORIGEM_NACIONAL python -m scripts.verifica --anos-ceap $(ANOS_CEAP)`,
  relatório em `data/nacional/verificacao.md`, sem tocar no `docs/relatorio/verificacao.md` da amostra). Na mão, `make verifica` precisa de
  `RAIO_X_DB=$ORIGEM_NACIONAL`, senão confere a amostra.
