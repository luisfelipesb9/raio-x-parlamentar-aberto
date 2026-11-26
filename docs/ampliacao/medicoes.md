# Medições na amostra de 20 deputados (base para a Onda 4)

Data: **2026-11-26**. Máquina: macOS (Apple Silicon), Python via `uv`, DuckDB do `uv.lock`. Tudo aqui foi **medido**
nesta data, exceto as linhas marcadas como EXTRAPOLAÇÃO. Preenche as lacunas da seção 7 de
[`pesquisa.md`](pesquisa.md). Scripts de medição: leitura somente (`read_only=True`), em cópias temporárias.

Banco medido: `data/sample/raio_x_publico.duckdb` (pseudonimizado; 31.777 fatos, 40 findings, 5.543 `entity_link`).
Obs.: é o arquivo local de 22/11; a base no ar tem 38 achados. A ordem de grandeza não muda.

## 1. Tamanho dos arquivos

| Arquivo | Bytes | `PRAGMA database_size` |
|---|---|---|
| `data/sample/raio_x_publico.duckdb` | 7.614.464 (7,6 MB) | 7,2 MiB |
| `data/sample/raio_x_sample.duckdb` | 7.352.320 (7,4 MB) | — |
| `data/raio_x.duckdb` (banco antigo de trabalho) | 2.895.872 | — |

### O índice da chave primária ocupa metade do arquivo

Cópia só da tabela `fact` (31.777 linhas) em arquivo novo:

| Variante | Tamanho |
|---|---|
| como hoje (`PRIMARY KEY (tipo, chave)`) | **7,88 MB** |
| sem chave primária | **3,94 MB** |
| sem chave primária, `atributos` como `VARCHAR` em vez de `JSON` | 3,94 MB (sem ganho) |

Um banco **somente leitura** não precisa do índice: a unicidade já foi garantida no banco de trabalho.

## 2. O que domina, por tipo de fato

| Tipo | Fatos | JSON bruto | Em disco* | ≈ bytes por fato em disco |
|---|---|---|---|---|
| `votos_municipio` | 17.060 | 3,27 MB | 1,05 MB | 62 |
| `despesa_ceap` | 10.950 | 1,96 MB | 1,31 MB | 120 |
| `emenda` | 2.083 | 0,60 MB | 0,26 MB | 125 |
| `doacao` | 1.008 | 0,27 MB | 0,26 MB | (abaixo da resolução de bloco) |
| `votacao`, `voto`, `socio`, `pep`, `empresa`, `proposicao`, `candidatura`, `deputado`, `sancao`, `autoria` | 719 | 0,10 MB | < 0,26 MB cada | — |

\* Cada tipo gravado sozinho em arquivo novo, **sem** chave primária, descontando o piso de 0,54 MB do arquivo vazio.
Tipos pequenos ficam abaixo da resolução de bloco (0,26 MB) e não dá para separar.

Por **quantidade**, `votos_municipio` + `despesa_ceap` são 88% dos fatos. Por **tamanho em disco**, ~80% dos dados.

EXTRAPOLAÇÃO para 513 deputados (×25,65 só nesses dois tipos, sem chave primária): `despesa_ceap` ≈ 281 mil × 120 B ≈ 34 MB;
`votos_municipio` ≤ 437 mil × 62 B ≈ 27 MB (teto; MG tem muitos municípios). Soma com o resto: **de 70 a 90 MB**, perto do
limite de 100 MB de envio da CLI no Hobby, **sem margem** e antes de contar a chave primária (que dobraria: ~180 MB,
batendo com a extrapolação linear de ~185 MiB da pesquisa).

## 3. Custo do `Snapshot` da API (`AppState(...).snapshot()`)

Comando: `RAIO_X_DB=... RAIO_X_ID_SALT=teste /usr/bin/time -l uv run python ...`. Duas execuções.

| Medida | Valor |
|---|---|
| `import api.state` sozinho (RSS) | 72 MB |
| `snapshot()` (tempo) | 0,21 s e 0,68 s (a 1ª com disco frio) |
| Pico de memória (RSS) após `snapshot()` | **195–197 MB** (≈ +125 MB sobre o import) |
| Fatos / nós / arestas | 31.777 / 2.397 / 3.063 |

Por etapa (um processo, RSS medido entre etapas):

| Etapa | Tempo | Memória |
|---|---|---|
| `store.load_facts()` (objetos `Fact` com `dict`) | 0,13 s | **+131 MB** (≈ 4,1 KB por fato) |
| `project(facts, findings)` (grafo) | 0,08 s | +1 MB |
| `forward.run(...)` (usado só por `/perguntar`) | 0,05 s | +7 MB |

**Conclusão medida:** o gargalo é transformar as linhas em objetos Python (`load_facts`); o grafo e a inferência são baratos.

EXTRAPOLAÇÃO (linear em fatos): 0,5 M de fatos ≈ 2,0 GB; 0,9 M ≈ 3,7 GB. O teto da função no Hobby é 2 GB, então o snapshot
global **deixa de caber acima de ~0,45 M de fatos** (a estimativa nacional com CEAP cru é 0,5–0,9 M). Tempo: ~3,5 s só
para carregar os fatos, linear (não medi a inferência em escala).

## 4. O que NÃO foi medido (e como medir)

- Quantas votações nominais de Plenário existem por ano (define os fatos `voto`): contar `distinct idVotacao` no
  dump `votacoesVotos-{ano}.csv` (tarefa do agente da Câmara).
- Latência da Câmara e tamanho dos dumps (idem).
- Tempo da inferência (`make infer`) em escala nacional: só depois do ingest nacional.
- Tamanho real do banco enxuto da [ADR-011](../adr/ADR-011-publicacao-enxuta-e-leitura-sob-demanda.md): medir no teste
  sintético de escala e depois com dados nacionais reais.

## 5. Teste sintético de escala (SINTÉTICO: não são dados reais)

Data: **2026-11-26**, mesma máquina das seções anteriores (macOS, Apple Silicon, 10 núcleos, 16 GB; DuckDB 2.0.1).
Script: `scripts/escala_sintetica.py` (`RAIO_X_ID_SALT=teste uv run python -m scripts.escala_sintetica --base <cópia da base pública> --saida <dir>`).
Método: a amostra real de 20 deputados é **replicada 25,65 vezes** com chaves e ids distintos (513 deputados exatos; a última réplica é
parcial). Votações, proposições, empresas, sanções, sócios e PEP **não** se repetem (os 513 votam nas mesmas votações e pagam as mesmas
empresas). Roda o motor sobre o resultado, depois `python -m publicar`, e mede a API em processos novos (3 rodadas; vale a mediana do tempo
e o maior pico de memória, via `/usr/bin/time -l`). Caminho antigo = a API sobre o banco completo sintético; novo = sobre o arquivo de `publicar`.

| Medida (SINTÉTICO, 513 deputados) | Caminho antigo (banco completo) | Caminho novo (banco enxuto) | Gatilho do plano B |
|---|---|---|---|
| Fatos no arquivo | 808.800 | 13.772 | |
| Tamanho do arquivo | 164,9 MB | **8,9 MB** | > 80 MB |
| Pico de memória da API | 2.585 MB | **324 MB** | > 1 GB |
| Partida a frio (1ª `/deputados` + 1ª `/grafo`) | 7,87 s (7,82 a 7,95) | **0,37 s** (0,36 a 0,37) | > 10 s |
| 1ª `/perguntar` | 4,63 s | 0,01 s | |
| 1ª `/comparar` | 0,19 s | 0,02 s | |
| `python -m publicar` (roda local) | | 12,0 s, pico de 2.144 MB | |

Nenhum gatilho do plano B foi acionado. O caminho antigo passa de 2 GB (teto da função no Hobby) já com ~0,8 M de fatos, como a
extrapolação da seção 3 previa; o novo fica em 324 MB. Grafo materializado: 2.890 nós e 77.294 arestas; 1.056 findings.

**Sensibilidade a votos (também sintética).** Somando 200 votações nominais novas × 513 deputados (102.800 votos, ~10× a densidade de votos
da amostra): arquivo de **11,8 MB** (≈ 28 bytes por voto), pico da API 324 MB, partida 0,34 s.

**Limites desta medição (leia antes de citar os números):**
- É replicação da amostra de MG (CEAP de 2024, um trimestre de votos), não o dado nacional. A distribuição real (fornecedores, emendas, votos)
  será diferente; repetir com dados reais é o critério de aceite final da ADR-011.
- As réplicas **compartilham empresas**, então o grafo sintético tem poucos nós (2.890). No dado real cada deputado tem fornecedores próprios,
  e os nós podem ir à casa de dezenas de milhares (estimativa da ADR: 60 a 80 mil nós e arestas). Como a memória do grafo é por objeto,
  espere o pico da API acima de 324 MB, ainda longe do gatilho de 1 GB (não medido).
- A partida foi medida em processo local (cliente de teste, sem rede nem partida de função serverless da Vercel).
