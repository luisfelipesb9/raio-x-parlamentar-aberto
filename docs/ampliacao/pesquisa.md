# Ampliação para 513 deputados: pesquisa de viabilidade

Data da pesquisa e do acesso a todas as URLs: **2026-11-26**. Escrito antes de qualquer código.
Convenções: **MEDIDO** = li no repositório ou consultei a fonte oficial nesta data; **EXTRAPOLAÇÃO** =
conta linear a partir de um número medido; **HIPÓTESE** = suposição que precisa de medição.
Nada aqui é parecer jurídico.

## 0. Veredito

| Pergunta | Resposta |
|---|---|
| O **ingest** nacional cabe de graça? | **Sim**, rodando local (ou em CI público) em etapas. Ordem de grandeza: de 1 a 3 horas de relógio, quase todo em esperas de rede (Câmara ~3,9 mil requisições; Receita opcional ~7 GB). Custo em dinheiro: zero. |
| O **banco publicado** cabe na Vercel Hobby como está hoje? | **Não como está.** O limite de pacote (500 MB Python) não é o problema. Os problemas são: (1) envio pela CLI limitado a **100 MB** no Hobby; (2) `api/state.py` carrega **todos** os fatos em objetos Python a cada partida a frio (memória máx. 2 GB e CPU ativa de 4 h/mês no Hobby); (3) a cláusula "uso pessoal ou não comercial". |
| Decisão | **Cabe com ajuste**: publicar um banco *enxuto* (agregados e findings, não as ~230 mil despesas cruas) e trocar o `Snapshot` global por leitura sob demanda. Se a medição (seção 7) mostrar banco público > ~80 MB ou pico de memória do snapshot > ~1 GB, vai para o **plano B** (arquivo no Cloudflare R2 + API em Fly.io por ~US$ 4–7/mês, ou Vercel Pro por US$ 20/mês). |

**3 maiores riscos:** (1) o `Snapshot` em memória (partida a frio e RAM); (2) CPF de terceiros em escala (base de trabalho com CPF íntegro e banco público maior); (3) a API da Câmara sem limite documentado e o `CamaraSource` sem nova tentativa em 429, gravando o bruto só no fim.

**1ª coisa a medir:** na amostra atual, tempo de `Snapshot` (build) e pico de memória, mais o tamanho dos dois `.duckdb`. Comando na seção 7.

---

## 1. O que o código faz hoje (lido no repositório)

| Etapa | Como coleta | Cresce com o nº de deputados? |
|---|---|---|
| Câmara (`sources/camara/source.py`) | API v2, `itens=100`, pausa 0,2 s entre chamadas, **sem nova tentativa** (`raise_for_status`); grava `data/raw/camara/*.json` **só no final** do `fetch`. Votos e orientações: 2 chamadas por votação PLEN (uma resposta traz os votos de **todos** os deputados). | Votações: **não**. `--detalhar-deputados`: 1 chamada por deputado. Proposições: 1+ chamada por autor e 2 por proposição. |
| CEAP (`sources/ceap`) | 1 zip por ano; lê o JSON em streaming e **processa o ano inteiro** mesmo na amostra (o filtro por deputado vem depois). | **Não** na leitura; sim no que é gravado. |
| TSE (`sources/tse`) | HTTP Range nos zips (só o membro da UF). Com escopo `None`, o pipeline chama `fetch(uf=None)`, que percorre as 27 UFs e **devolve tudo em memória**; existe `fetch_por_uf` (uma UF por vez), mas o pipeline ainda não o usa nesse caso. | Sim (uma UF por vez hoje; 27 no nacional). |
| CGU (`sources/cgu`) | 3 downloads (CEIS, CNEP, emendas) lidos inteiros em memória. | **Não** (constante). |
| OpenSanctions PEP | 1 arquivo JSON Lines, constante. | **Não**. |
| RFB (`sources/rfb`) | BrasilAPI, 1 chamada por CNPJ, pausa 0,5 s, 5 tentativas com espera; `--limite-rfb 50` pega os de maior valor. | Sim, **linear no nº de CNPJs** (inviável em massa; seção 4). |
| API (`api/state.py`) | `Snapshot` = `store.load_facts()` (todos os fatos viram objetos pydantic) + projeção do grafo inteiro + `forward.run`, uma vez por processo. Quase todo endpoint chama `state.snapshot()`. | **Sim, linear nos fatos.** É o gargalo. |
| Deploy (`vercel.json`, `.vercelignore`, `ingest/deploy_check.py`) | `maxDuration: 30`; só `data/sample/raio_x_publico.duckdb` sobe; `deploy-check` reprova qualquer outro `.duckdb`. | Tamanho do arquivo público. |

Tamanhos de referência da amostra (20 deputados de MG):

- `raio_x_sample.duckdb` e `raio_x_publico.duckdb`: **FALTA MEDIR.** Não consegui o tamanho em bytes com as ferramentas desta tarefa (só leitura de arquivos). Como medir está na seção 7. Só sei que o arquivo público é DuckDB v2.0.1 (cabeçalho) e que o README da API fala em "bundle < 500 MB (DuckDB ~40 MB + banco)" (`api/README.md`, linha 89), sem dar o tamanho do banco.
- Contagens medidas pelo dono (`docs/HANDOFF.md`, `docs/relatorio/verificacao.md`): 10.950 despesas CEAP (soma das 20 linhas da verificação), 17.060 `votos_municipio`, 1.008 doações, 2.083 emendas ligadas (de 37.297 ligadas e 77.113 no total global da CGU), 1.598 empresas, ~713 sócios, 40 findings.

---

## 2. Vercel Hobby em 2026

| Item | Limite no Hobby | Fonte |
|---|---|---|
| Pacote da função, **Python** (descompactado) | **500 MB** (250 MB nas outras linguagens). "Large functions" (beta): até 5 GB, projetos novos já elegíveis | https://vercel.com/docs/functions/limitations e https://vercel.com/docs/functions/runtimes/python |
| Memória da função | **2 GB / 1 vCPU** (máx. no Hobby; Pro 4 GB) | https://vercel.com/docs/functions/limitations |
| Duração máxima | **300 s** (nosso `vercel.json` usa 30 s: dá para subir sem custo) | idem |
| Envio **pela CLI** (arquivos-fonte) | **100 MB** no Hobby (1 GB no Pro); falha se passar. Máx. 15.000 arquivos | https://vercel.com/docs/limits |
| Build | 45 min por deploy; 2 vCPU, 8 GB; 100 deploys/dia | https://vercel.com/docs/limits e https://vercel.com/docs/plans/hobby |
| Uso mensal incluído | 100 GB de transferência rápida, 1 M de invocações, **4 h de CPU ativa**, 360 GB-h de memória. Estourar = esperar 30 dias | https://vercel.com/docs/plans/hobby |
| `/tmp` gravável | até **500 MB** por instância, some quando a instância para (resumo de busca no domínio vercel.com; reconferir em https://vercel.com/docs/functions/runtimes) | https://vercel.com/docs/functions/runtimes |
| Vercel Blob (Hobby) | 1 GB de armazenamento, 10 GB de transferência/mês, blob de até 512 MB em cache; passou do limite, bloqueia por 30 dias | https://vercel.com/docs/vercel-blob/usage-and-pricing |
| Git | Hobby **não** conecta a repositório de **organização** do GitHub | https://vercel.com/docs/limits |
| Páginas/ISR | **Não relevante hoje**: `grep` em `web/src` não achou `generateStaticParams` nem `revalidate`; o web busca a API em tempo de execução (`web/src/lib/api.ts`). 513 deputados não criam 513 páginas estáticas. | repositório |

**Cláusula de uso não comercial.** O texto dos Termos diz: "You shall only use the Services under a Hobby plan for your personal or non-commercial use" (https://vercel.com/legal/terms, seção 4). A página dos Termos **não define** "comercial" e a página de uso justo (https://vercel.com/docs/limits/fair-use-guidelines) veio sem os blocos "Examples of fair use / Never fair use" na minha leitura. Um fio da comunidade cita doações e anúncios como exemplos comerciais, mas é resumo de usuário, **não** texto oficial. **Leitura prudente (HIPÓTESE):** projeto acadêmico, MIT, sem receita, sem anúncio, sem botão de doação nem patrocínio, se enquadra. Se alguma dessas coisas aparecer, ou o projeto virar de organização, migrar para Pro. Peça confirmação por escrito ao suporte antes da ampliação.

**Dá para hospedar um `.duckdb` de dezenas a centenas de MB lido pela função?**

| Tamanho do banco público | Cabe? |
|---|---|
| até ~100 MB (**MEDIDO**: limite de envio) | Sim, pelo caminho atual (`vercel deploy` da pasta). Confirmar com `vercel deploy --dry --json` e um deploy de preview se a regra dos 100 MB conta bytes brutos ou compactados (a doc não diz: HIPÓTESE de bytes brutos). |
| 100–500 MB | O pacote aguenta (500 MB), mas a **CLI recusa** o envio no Hobby. Saídas: guardar o arquivo no Blob/R2 e baixar em `/tmp` na partida (500 MB, por instância), ou testar `vercel build` + `vercel deploy --prebuilt` (HIPÓTESE: o limite de 100 MB seria dos arquivos-fonte, não da saída de build; a doc não esclarece). |
| acima de ~500 MB | Fora do Hobby. Plano B. |

O DuckDB também sabe ler um `.duckdb` remoto, somente leitura, por HTTPS com requisições de faixa (`ATTACH 'https://…' (READ_ONLY)`; "uses HTTP range requests to fetch only the blocks required by a query", https://duckdb.org/docs/2.0/core_extensions/httpfs/https.html). Isso permite o arquivo ficar no R2 (egresso grátis) em vez de dentro do pacote. HIPÓTESE a testar: carregar a extensão `httpfs` dentro da função da Vercel (a extensão precisaria vir empacotada).

**O problema real não é o arquivo, é o `Snapshot`.** Abrir o `.duckdb` é rápido; o custo está em transformar milhões de linhas em objetos Python a cada processo novo.

- **Memória (HIPÓTESE):** se cada `Fact` ocupar 1–2 KB em RAM, 0,6 M de fatos já são 0,6–1,2 GB, antes do grafo (uma aresta por despesa em `graph/build.py`) e do DuckDB. O teto é 2 GB.
- **CPU ativa (conta):** 4 CPU-h = 14.400 s por mês. Se uma partida a frio custar, por exemplo, 30 s de CPU (HIPÓTESE), são só ~480 partidas por mês antes de o plano pausar.
- **Tempo:** a duração configurada é 30 s; o teto do Hobby é 300 s.

### Alternativas gratuitas (limites e custo)

| Opção | Limite relevante | Serve? | Fonte |
|---|---|---|---|
| **Cloudflare R2** (só arquivo) | 10 GB/mês de armazenamento, 1 M de operações classe A, 10 M classe B, **egresso grátis** | Sim, como depósito do `.duckdb` (não executa Python) | https://developers.cloudflare.com/r2/pricing/ |
| Cloudflare Workers Free | 128 MB de memória, pacote de 64 MiB, 10 ms de CPU por requisição | **Não** para a API | https://developers.cloudflare.com/workers/platform/limits/ |
| **Render** (web service grátis) | 512 MB de RAM e 0,1 CPU; hiberna após 15 min; ~1 min para voltar; sem disco persistente; 750 h/mês | **Não** com o `Snapshot` atual (RAM); aceitável só com leitura sob demanda | https://render.com/docs/free |
| **Hugging Face Spaces** | CPU Basic (2 vCPU, 16 GB) sem custo por hora, mas **Docker/Gradio exigem plano pago para criar**; só Space estático é grátis para todos | **Não** é mais grátis para API FastAPI | https://huggingface.co/docs/hub/spaces-overview |
| **Fly.io** | Não achei plano grátis permanente: conta nova começa com US$ 1 de crédito, e US$ 5/mês de uso incluído depois de cadastrar cartão; `shared-cpu-1x` 512 MB ≈ US$ 3,69/mês, 1 GB ≈ US$ 6,70/mês; volume US$ 0,15/GB/mês | Plano B barato, com RAM suficiente para o snapshot atual | https://docs.fly.io/about/pricing |
| **Vercel Pro** | US$ 20 por usuário-desenvolvedor por mês; 1 GB de envio pela CLI, 4 GB de memória | Plano B simples (mesmo fluxo) | https://vercel.com/docs/plans/hobby |
| GitHub Pages / Vercel estático | Só arquivos estáticos | Serve para JSONs pré-gerados por deputado (ver seção 6, opção "estático") | (conhecimento geral, sem URL verificada) |

---

## 3. Câmara dos Deputados: volume nacional

| Fato | Valor | Como obtive | Status |
|---|---|---|---|
| Deputados **em exercício** | **513** | `GET /api/v2/deputados?itens=1`: último `pagina=513`; e `itens=100&pagina=6` devolveu 13 itens | MEDIDO (API, 2026-11-26) |
| Pessoas na legislatura 57 (`idLegislatura=57`, o que o `fetch` baixa hoje) | **878** | `GET /api/v2/deputados?idLegislatura=57&itens=1`: último `pagina=878` | MEDIDO |
| Votações no período Jan–Mar/2025 (todos os órgãos) | 459 | `votacoes?dataInicio=2025-01-01&dataFim=2025-03-31&itens=1`: última página 459 | MEDIDO |
| Votações Jan–Mar/2026 (todos os órgãos) | 2.060 | idem | MEDIDO (só PLEN e nominais importam; quantos são: **medir**) |
| Janela de datas da API de votações | Janela de 3 meses funcionou; janelas de 6 e de 12 meses deram **HTTP 400** (corpo da resposta não visível na minha ferramenta) | 3 chamadas de teste | HIPÓTESE: teto perto de 3 meses. Para um ano pela API, fatiar em trimestres |
| PL/PEC/PLP apresentados em Jan–Mar/2025 | 1.268 | `proposicoes?...siglaTipo=PL&siglaTipo=PEC&siglaTipo=PLP&itens=1`: última página 1268 (leitura da ferramenta) | MEDIDO |
| Limite de requisições da API | **Não documentado**: a página oficial do Swagger não cita limite nem termos | https://dadosabertos.camara.leg.br/swagger/api.html | MEDIDO (ausência). O repo já viu HTTP 429 (`DATA_LICENSES.md`). |
| Arquivos em lote | Existem, atualizados diariamente | https://dadosabertos.camara.leg.br/swagger/api.html | MEDIDO |

**Dumps oficiais** (padrões de URL da página do Swagger):

| Conjunto | URL | Recorte |
|---|---|---|
| Votações | `https://dadosabertos.camara.leg.br/arquivos/votacoes/csv/votacoes-{ano}.csv` | por ano |
| Votos por parlamentar | `https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/votacoesVotos-{ano}.csv` | por ano (o de 2025 passa de 10 MiB: mediu "maxContentLength 10485760 exceeded", só um piso; tamanho real **falta medir**) |
| Orientações de bancada | `.../arquivos/votacoesOrientacoes/csv/votacoesOrientacoes-{ano}.csv` | por ano, só Plenário |
| Deputados | `.../arquivos/deputados/csv/deputados.csv` | arquivo único |
| Proposições | `.../arquivos/proposicoes/csv/proposicoes-{ano}.csv` | pelo ano de apresentação |
| CEAP | `https://www.camara.leg.br/cotas/Ano-{ano}.{formato}[.zip]` | por ano de ocorrência; xml, json e csv podem vir em `.zip` |

Tamanho do CEAP: o docstring de `sources/ceap/source.py` diz "~9 MB zip / ~250 MB JSON por ano; ~230 mil linhas" (ano 2024). É **declaração do código, não reverificada por mim**. Cruzamento: 10.950 despesas dos 20 deputados de MG × 25,65 = ~281 mil (EXTRAPOLAÇÃO), mesma ordem de grandeza. Como confirmar: `curl -sI https://www.camara.leg.br/cotas/Ano-2025.json.zip | grep -i content-length`.

**Efeito prático dos dumps:** para votos, o custo da API **não** depende do nº de deputados (cada resposta traz os 513 votos), então para a janela atual (um trimestre) a API serve. Para janela longa (ano ou legislatura), o dump `votacoesVotos-{ano}` troca centenas ou milhares de chamadas por 3 downloads por ano, e contorna o teto de janela.

Duas armadilhas do `CamaraSource` ao escalar (lidas no código):

1. Sem nova tentativa em 429/5xx (só RFB tem): uma falha no meio perde tudo, porque `save_raw` só roda no fim de `fetch`.
2. Proposições: `_coletar_proposicoes` **para** quando acha `max_proposicoes` (padrão 300) e consulta autor por autor em ordem de id; com 513 autores, 300 proposições viram uma amostra enviesada pelos primeiros autores. No nacional, usar `--max-proposicoes` sem teto (ou desligar).

Ainda por confirmar: se `/votacoes/{id}/votos` devolve os 513 votos em uma resposta só (o código usa `paginar=False`, mas `_get_all` segue links `next`). Testei uma votação simbólica (0 votos, sem `next`) e não bastou. Uma chamada a uma votação nominal resolve.

---

## 4. TSE, CGU, PEP e Receita (CNPJ)

| Fonte | O que é | Tamanho | Formato | Licença | Escala com deputados? |
|---|---|---|---|---|---|
| **TSE 2022** (candidatos, receitas, votação por zona) | zips em `cdn.tse.jus.br`, 1 CSV por UF, lidos por HTTP Range | candidatos ~5 MB; prestação de contas ~500 MB; votação ~590 MB (MG sozinho ≈ 1 GB de CSV, ~70 MB compactados). **Declaração do docstring de `sources/tse/source.py`, não reverificada por mim**; o portal não lista tamanhos | CSV latin-1, `;` | **CC BY** ("Creative Commons Attribution"), https://dadosabertos.tse.jus.br/dataset/candidatos-2022 (versão da licença não declarada) | Por UF: 27 UFs em vez de 1 |
| **CGU** CEIS, CNEP, emendas | downloads do Portal da Transparência | CEIS ~3 MB, CNEP ~0,2 MB, emendas ~47 MB (docstring de `sources/cgu/source.py`, não reverificado) | zip com CSV, latin-1 | **A confirmar**: a página de download não traz licença (https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares) | Não |
| **OpenSanctions `br_pep`** | `targets.nested.json` | **146,21 MB** (MEDIDO, 106.405 pessoas), atualizado diariamente | JSON Lines | **CC BY-NC 4.0**: empresas precisam de licença de dados (https://www.opensanctions.org/datasets/br_pep/) | Não |
| **Receita, CNPJ aberto mensal** | cadastro completo em zips | ~**7,1 a 7,6 GB compactados**, 36–37 zips para a competência 2026-07 (10 Empresas, 10 Estabelecimentos, 10 Sócios, 1 Simples, 6 tabelas de apoio). **Fonte secundária** (artigos de terceiros: https://ecobigdata.com.br/blog/dados-abertos-cnpj-receita-federal e https://toexceed.com.br/blog/2026/09/27/dados-abertos-cnpj-receita-federal-o-guia-completo-para-acessar-e-utilizar/); descompactado: **não confirmado** (HIPÓTESE: dezenas de GB; `docs/` do repo fala em ~17 GB) | CSV `;` **sem cabeçalho**, em geral latin-1 (não declarado no layout) | Sem licença nomeada ("dado aberto"); ver pendência em `DATA_LICENSES.md` | Só pelo nº de CNPJs |

Receita, o que **confirmei** em fonte oficial:

- Layout (documento oficial `https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf`, "Novo Layout para os DADOS ABERTOS do CNPJ"): **Empresas**, **Estabelecimentos** e **Sócios** têm o campo "CNPJ BÁSICO" (os 8 primeiros dígitos); Estabelecimentos acrescenta ordem (4) e DV (2). Sócios traz identificador (PJ/PF/estrangeiro), nome, CPF/CNPJ do sócio, qualificação e data de entrada.
- **Filtro viável:** montar o conjunto de CNPJ básicos que aparecem em `despesa_ceap` e `doacao` (fornecedores e doadores PJ) e varrer os 30 zips (Empresas, Estabelecimentos, Sócios) em streaming, guardando só as linhas que casam. Não precisa guardar a base inteira nem descompactar para disco.
- **Onde baixar:** a página oficial (`gov.br/receitafederal/.../dados-publicos-cnpj`) exigiu login na minha leitura, e o host antigo `dadosabertos.rfb.gov.br` recusou a conexão. Fontes de terceiros dizem que o caminho mudou no fim de janeiro de 2026 e apontam `arquivos.receitafederal.gov.br`, mas o diretório que tentei deu 404. **Falta confirmar a URL vigente** pelo portal https://dados.gov.br (conjunto "Cadastro Nacional da Pessoa Jurídica - CNPJ") ou pela página da Receita antes de escrever o conector. A lista de arquivos e o diretório mudam ("Diretórios e nomes podem mudar", segundo a fonte secundária): deixar a URL base configurável e validar a lista esperada.
- **CPF dos sócios no arquivo aberto:** HIPÓTESE de que venha mascarado como na BrasilAPI (o layout oficial não diz). Conferir numa fatia.

**Alerta novo: CNPJ alfanumérico.** A Receita informa que os primeiros CNPJs alfanuméricos entram em produção "a partir de Julho de 2026", com 14 posições (A–Z e 0–9, DV por módulo 11 sobre o código ASCII) e que os formatos numérico e alfanumérico coexistem (https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf, PDF oficial de 14 páginas). No repositório, `ingest/resolve/comum.py::cnpj_valido` exige `isdigit()` e `sources/ceap/source.py::_documento_fornecedor` e `sources/rfb` removem tudo que não é dígito. HIPÓTESE: fornecedor com CNPJ alfanumérico em CEAP de 2026 ficaria sem documento (ou, no pior caso, viraria 11 dígitos e seria lido como CPF). Não afeta dados de 2024–2025. Testar com o arquivo CEAP de 2026 antes de incluí-lo.

**BrasilAPI NÃO serve para ingestão em massa. Confirmado em fonte oficial.** O README oficial (https://raw.githubusercontent.com/BrasilAPI/BrasilAPI/main/README.md) e o site (https://brasilapi.com.br/) dizem, na seção de termos: "Estamos em beta e ainda elaborando os Termos de Uso"; "por favor, não abuse deste serviço"; "por enquanto por favor não utilize formas automatizadas para fazer 'crawling' dos dados da API"; "O volume de consultas deve ter a natureza de uma pessoa real requisitando um determinado dado"; para alto volume "forneceremos posteriormente alguma solução". Não há limite numérico. Conta: 30.000 CNPJs (suposição de ordem de grandeza) × 0,5 s de pausa = 4,2 h, ignorando 429; além de contrariar o pedido deles. Manter `--limite-rfb` pequeno para a demonstração; cobertura nacional vem do arquivo mensal.

---

## 5. Estimativa para 513 deputados

Base de comparação: 20 deputados de MG; fator 513/20 = **25,65**.

### 5.1 Quantidade de fatos

| Tipo | Amostra (MEDIDO) | Nacional | Status |
|---|---|---|---|
| `despesa_ceap` (1 ano) | 10.950 | 230 mil (docstring) a 281 mil (×25,65) | declaração do código / EXTRAPOLAÇÃO |
| `votos_municipio` (TSE 2022) | 17.060 | ≤ 437 mil (×25,65); **provavelmente menos**, porque MG tem muitos municípios | EXTRAPOLAÇÃO (teto) |
| `doacao` | 1.008 | ~26 mil | EXTRAPOLAÇÃO |
| `emenda` ligada | 2.083 | até 37.297 (total global ligado, medido pelo dono) | MEDIDO (teto) |
| `empresa` + `socio` (RFB) | 1.598 + ~713 (com `--limite-rfb 50`, só 36 empresas com cadastro) | HIPÓTESE: dezenas de milhares com o arquivo mensal filtrado | HIPÓTESE |
| `voto` | só votações **nominais** do período da amostra | nº de votações nominais × ~513 (**medir** o nº nominal; a amostra de 145 votações PLEN teve 121 simbólicas removidas pela R02) | HIPÓTESE |
| Total, 1 ano de CEAP + 1 trimestre de votos | ~34 mil (soma dos acima, sem votos) | **~0,5 a 0,9 milhão** | EXTRAPOLAÇÃO |

Cada ano extra de CEAP soma ~230–280 mil fatos. Janela de votos de um ano soma votações nominais × 513.

### 5.2 Tamanho do banco

- Não consigo dar o tamanho da amostra (FALTA MEDIR). Fórmula para extrapolar depois de medir: `tamanho_nacional ≈ tamanho_amostra × (fatos_nacional / fatos_amostra)`, com a observação de que a tabela `fact` tem coluna JSON e `url` por linha.
- Só aritmética (sem tamanho real por fato): a cada **100 bytes por fato**, 0,6 milhão de fatos ocupa **60 MB**. Ou seja, é fácil passar dos 100 MB do envio pela CLI se todo o CEAP cru for publicado.

### 5.3 Requisições e tempo do ingest

| Etapa | Requisições | Tempo | Status |
|---|---|---|---|
| Câmara: lista de deputados (878 linhas, 9 páginas) | 9 | segundos | MEDIDO (contagem) |
| `--detalhar-deputados` (CPF, nome civil) | 513 (878 se for a legislatura toda) | 513 × (0,2 s + latência) | contagem MEDIDA |
| Votações do trimestre: listagem + 2 por votação PLEN (limite atual 145) | ~5 + ~290 | idem | contagem do código |
| Proposições, 1 autor por vez + 2 por proposição (até 1.268 no trimestre) | 513 + ≤ 2.536 | idem | contagem do código; teto de 1.268 MEDIDO |
| **Total Câmara** | **~3,9 mil** (com `max_proposicoes=300`, como hoje: ~1,9 mil, mas enviesado) | **~30–65 min** se a latência média for 0,3–0,8 s | latência é HIPÓTESE (**medir**) |
| CEAP | 1 download (~9 MB) por ano + leitura de ~250 MB em streaming | a amostra já lê o ano inteiro; **cronometrar** | HIPÓTESE |
| TSE, 27 UFs por Range | ~3 zips × 27 membros; transferência de até ~1,1 GB e leitura de vários GB de CSV em Python | HIPÓTESE: de 10 a 40 min; **cronometrar uma UF e multiplicar** | HIPÓTESE |
| CGU + PEP | 4 downloads (~200 MB no total) | minutos | declaração do código + PEP medido |
| Receita (arquivo mensal filtrado) | 30 zips, ~7 GB | download: 7,5 GB a 50 Mbps ≈ 20 min; a 10 Mbps ≈ 1,7 h (aritmética); o servidor é descrito por terceiros como lento ou instável | HIPÓTESE |
| `make infer` | — | **medir** (não sei se a complexidade é linear) | HIPÓTESE |

Resumo: **de 1 a 3 horas de relógio**, dominadas por espera de rede, com a Receita como parcela opcional e a mais longa. Execução única; depois só atualizações.

---

## 6. Desenho mais barato

1. **Ingest local em etapas, com cache em `data/raw/`** (já existe `--reusar-raw` na Câmara; o TSE já grava um bruto por UF). Ordem: deputados + CPF → CEAP → TSE por UF → CGU/PEP → Receita filtrada → `make infer`. Cada etapa é idempotente (o pipeline apaga o que vai reafirmar).
2. **CI agendado só para o que é público e barato** (`schedule` mínimo de 5 min; em repositório público o agendamento é **desativado após 60 dias sem atividade**, https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows). Runners padrão em repositório público: 4 vCPU, 16 GB, **14 GB de SSD**, uso "free and unlimited" (https://docs.github.com/en/actions/reference/runners/github-hosted-runners), job de no máx. **6 h** (https://docs.github.com/en/actions/reference/limits). O cadastro da Receita (~7 GB) cabe só em streaming, um zip por vez. **Não** subir o banco de trabalho (tem CPF íntegro) como artefato: HIPÓTESE de que artefatos e logs de repositório público sejam legíveis por qualquer pessoa; confirmar antes. Recomendação: ingest com CPF **sempre local**; CI só para testes e para a varredura do banco público.
3. **Três mudanças de dados antes de ampliar** (cada uma pede ADR, porque mexe em `repo/` e na API):
   - gerar na publicação **tabelas agregadas** (por deputado × fornecedor, por deputado × categoria, votos por município agregados) e deixar as despesas cruas fora do banco público, ou em um segundo arquivo consultado só por id quando alguém abre a evidência;
   - trocar o `Snapshot` global por **consultas sob demanda** (subgrafo do deputado vem do SQL), mantendo a regra "api só lê";
   - **escopo explícito**: 513 em exercício (padrão) × 878 da legislatura (inclui suplentes que passaram). O custo por deputado sobe ~71% com os 878.
4. **Opção estática** (HIPÓTESE, só se o banco público ficar grande demais): pré-gerar um JSON por deputado (ficha, findings, subgrafo) no momento de publicar e servir como arquivo estático; a API fica só com `/perguntar` e `/comparar`. Sai do problema de partida a frio e dos 100 MB, ao custo de reescrever a camada de leitura.
5. **Votos por dump anual** quando a janela passar de um trimestre.

**Como validar (`make verifica`).** Hoje ele recalcula, a partir dos brutos, o governismo e o total CEAP de **cada deputado do banco** e confronta com banco e motor (44 conferências na amostra, 0 divergências). No nacional: rodar com `RAIO_X_DB` apontando para o banco nacional (ele já itera por deputado); trocar a amostra online de votos (`--online`) por ~30 deputados sorteados; acrescentar conferência por fonte (contagem do bruto × contagem em `fact`); e `make deploy-check` + `ingest.varredura` no banco público. Critério de aceite sugerido: 0 divergências, 0 CPF íntegro, `GET /cobertura` com `n_deputados = 513`.

---

## 7. Recomendação, riscos e o que medir primeiro

**Decisão:** ampliar para 513 **cabe com ajuste**. O ingest cabe de graça. A publicação na Vercel Hobby só cabe se o banco público for **enxuto** e a API **não** carregar tudo na partida. Sem esses dois ajustes, o plano B é Fly.io (~US$ 4–7/mês) com o arquivo em R2, ou Vercel Pro (US$ 20/mês).

### Riscos

| Risco | Por quê | Mitigação |
|---|---|---|
| `Snapshot` em memória / partida a frio | Linear nos fatos; teto de 2 GB e 4 CPU-h/mês no Hobby | Agregar na publicação; leitura sob demanda; ou plano B |
| **LGPD de CPF em escala** | A amostra tem 752 CPFs íntegros de terceiros (controle positivo da varredura); em escala, ×25 só como teto de ordem de grandeza (~19 mil, EXTRAPOLAÇÃO). Nomes continuam na base pública (ADR-006). Ser público não dispensa finalidade e minimização (LGPD art. 7º §3º, citado em `DATA_LICENSES.md`) | Base de trabalho só local; só o banco pseudonimizado sai; `deploy-check` e `varredura` em todo release; mesmo sal sempre; publicar só o necessário (agregados); manter canal de correção (`docs/politica-de-uso-e-correcao.md`) |
| **Tamanho do banco público** | 100 MB de envio no Hobby; ~60 MB para cada 0,6 M de fatos a 100 B/fato | Agregados; segundo arquivo de evidências em R2 |
| API da Câmara | Sem limite documentado, 429 já visto, sem retry, bruto só no fim | Retry com espera (como na RFB), checkpoint por votação, dump anual para votos, `pausa` ≥ 0,2 s |
| Janela de datas da API de votações | 400 acima de ~3 meses (HIPÓTESE) | Fatiar em trimestres ou dump |
| CNPJ alfanumérico | Entra a partir de julho/2026 (oficial); código só aceita dígitos | Testar com CEAP 2026; atualizar normalização e DV |
| Licenças | Câmara, CGU e Receita sem licença nomeada (pendências em `DATA_LICENSES.md`); OpenSanctions é **CC BY-NC**: comercial exige desligar | Manter atribuição; não monetizar; migrar PEP para a CGU quando houver licença |
| Termos da Vercel Hobby | "Uso pessoal ou não comercial" sem definição de "comercial" | Sem receita; pedir confirmação por escrito; Pro se mudar |
| Receita | URL vigente não confirmada; site lento; layout/diretório mudam | URL configurável; validar lista de arquivos; download com retomada |

### O que medir primeiro (nesta ordem, uns 30 min no total)

1. **Tamanhos** (na máquina do dono):
   `ls -l data/sample/*.duckdb`
   `duckdb -readonly data/sample/raio_x_publico.duckdb "PRAGMA database_size; SELECT tipo, count(*) n, sum(length(atributos)) bytes_json FROM fact GROUP BY 1 ORDER BY 3 DESC;"`
2. **Custo do `Snapshot`** na amostra (tempo e pico de memória), para extrapolar por nº de fatos:
   `RAIO_X_DB=data/sample/raio_x_publico.duckdb RAIO_X_ID_SALT=teste /usr/bin/time -l uv run python -c "import time; from api.state import AppState; t=time.time(); AppState(None, None).snapshot(); print('snapshot s =', round(time.time()-t, 2))"`
   Ler "maximum resident set size" no fim (no macOS; em Linux use `/usr/bin/time -v`).
3. **Latência da Câmara:** `curl -s -o /dev/null -w '%{time_total}\n'` em 20 URLs de `/deputados/{id}`; e uma chamada a `/votacoes/{id}/votos` de votação **nominal** (conferir se vem inteira).
4. **Tamanhos dos dumps:** `curl -sI` em `Ano-2025.json.zip`, `votacoesVotos-2025.csv` e nas três partes do TSE; contar votações nominais PLEN do período (`distinct idVotacao` do dump de votos).
5. **Uma UF do TSE** (por exemplo `--uf SP --fontes tse`) cronometrada, para multiplicar por 27.
6. **Receita:** confirmar a URL vigente e a lista de arquivos na página oficial; baixar **um** zip de Sócios e conferir o mascaramento do CPF e a codificação.

---

## 8. Fontes e lacunas

Todas acessadas em 2026-11-26.

Vercel: https://vercel.com/docs/functions/limitations · https://vercel.com/docs/functions/runtimes/python · https://vercel.com/docs/limits · https://vercel.com/docs/plans/hobby · https://vercel.com/legal/terms · https://vercel.com/docs/limits/fair-use-guidelines · https://vercel.com/docs/vercel-blob/usage-and-pricing · https://vercel.com/docs/functions/runtimes (só o resumo de busca sobre `/tmp`)
Câmara: https://dadosabertos.camara.leg.br/swagger/api.html · chamadas de teste a `https://dadosabertos.camara.leg.br/api/v2/{deputados,votacoes,proposicoes}`
Receita: https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf · https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf · (secundárias) https://ecobigdata.com.br/blog/dados-abertos-cnpj-receita-federal · https://toexceed.com.br/blog/2026/09/27/dados-abertos-cnpj-receita-federal-o-guia-completo-para-acessar-e-utilizar/
BrasilAPI: https://raw.githubusercontent.com/BrasilAPI/BrasilAPI/main/README.md · https://brasilapi.com.br/
TSE: https://dadosabertos.tse.jus.br/dataset/candidatos-2022 · CGU: https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares · OpenSanctions: https://www.opensanctions.org/datasets/br_pep/
Alternativas: https://developers.cloudflare.com/r2/pricing/ · https://developers.cloudflare.com/workers/platform/limits/ · https://render.com/docs/free · https://huggingface.co/docs/hub/spaces-overview · https://docs.fly.io/about/pricing · https://duckdb.org/docs/2.0/core_extensions/httpfs/https.html
GitHub Actions: https://docs.github.com/en/actions/reference/runners/github-hosted-runners · https://docs.github.com/en/actions/reference/limits · https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows

**Lacunas assumidas (não afirmei):** tamanho real em bytes dos dois `.duckdb`; tamanho real dos dumps da Câmara, do TSE e da CGU (usei o que está nos docstrings, marcado); URL vigente e tamanho descompactado do CNPJ aberto; definição oficial de "comercial" da Vercel; se o limite de 100 MB da CLI conta bytes brutos ou compactados e se vale para `--prebuilt`; se `/votos` pagina; limite de requisições da Câmara; licença formal de Câmara, CGU e Receita (já é pendência em `DATA_LICENSES.md`).
