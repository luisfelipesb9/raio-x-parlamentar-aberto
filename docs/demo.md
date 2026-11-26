# Demo offline (5 minutos)

Roda o sistema inteiro com um banco **100% fictício**: sem internet, sem coletar nada das fontes oficiais, sem CPF
de ninguém. Serve para conhecer o Raio-X Parlamentar, testar a interface e mostrar o projeto.

> **DADOS FICTÍCIOS PARA DEMONSTRAÇÃO.** Os seis deputados (Alice, Bruno, Carla, Davi, Elisa e Fábio, todos com
> "(demo)" no nome), os partidos FICT-A e FICT-B, as empresas, os doadores e os valores foram inventados. Nenhum
> alerta da demo diz algo sobre uma pessoa ou empresa real. Os ids de deputado (a partir de 9900001) e os CNPJ
> (raiz 99999) são de demonstração, sem relação com deputados ou empresas reais, e as URLs de "fonte" terminam em
> `.invalid`, que nunca abre.

## Pré-requisitos
- Python (3.11+ suportado, 3.12 recomendado) e [uv](https://docs.astral.sh/uv/) (`make setup` instala as dependências Python).
- Node 22 e pnpm (`pnpm --dir web install` instala o site).

## Comandos
```bash
make setup                                   # uma vez
make demo                                    # gera data/sample/raio_x_demo.duckdb e imprime os dois comandos abaixo
```
Em dois terminais, na raiz do repositório:
```bash
make dev-demo                                # API em http://localhost:8000 (se o banco não existir, avisa: rode make seed-demo)
pnpm --dir web install && pnpm --dir web dev # site em http://localhost:3000 (o install só na primeira vez)
```
`make dev-demo` equivale a subir a API com `RAIO_X_ID_SALT=sal-fixo-da-demonstracao` e
`RAIO_X_DB=data/sample/raio_x_demo.duckdb`. `RAIO_X_ID_SALT` é o sal dos ids de pessoa do grafo e é obrigatório
(a API não sobe sem ele); o valor da demo é público e só serve para dados fictícios, nunca o use numa base real.
Só `make seed-demo` gera o banco, sem imprimir as instruções. O banco é recriado do zero a cada execução.

## O que ver
| Onde | Deputado fictício | O que mostra |
|---|---|---|
| Ficha, "Como vota" | Alice, Bruno, Fábio | alertas de **governismo** (R01) acima do limiar de 70% |
| Ficha, "Como vota" / Perguntar `alinhado_governo` | Carla e Elisa | R01 **abaixo do limiar**: o sistema explica por que não concluiu |
| Ficha, "Como vota" / Perguntar `alinhado_governo` | Davi | R01 com **dados insuficientes** (só 6 votos válidos; mínimo 10) |
| Ficha, "Quanto gasta" | Carla | **gasto fora do padrão** (R04): combustível ~13x o dos colegas |
| Ficha, alertas de integridade | Bruno e Elisa | pagamento a **empresa sancionada** (R03); Alice pagou uma empresa com sanção já encerrada e não é alertada |
| Ficha, "Produção" | Alice, Bruno, Carla, Davi, Fábio | **produção legislativa** (R05); Elisa não tem autoria registrada (falta de dado, não zero) |
| Ficha, "Para onde mandou dinheiro" | Alice e Carla | **emendas concentradas** onde tiveram mais votos (R07; a de Carla tem ressalva de Emenda Pix); Bruno recebeu proporcional |
| Ficha, "Quem financiou" | Davi | doador com o **mesmo nome de um sócio** de empresa que ele pagou (R06b, só indício: o CPF do sócio é mascarado) |
| Mapa de relações | qualquer um | grafo com partido, votos parecidos, doações, pagamentos, emendas, sociedades e autorias |
| Comparar, Fontes e método | | comparação lado a lado e a cobertura da base (fonte única `demo_ficticio`) |

Os links "página oficial na Câmara" das fichas apontam para ids que não existem lá: é esperado na demo.

## Como o banco é feito
`scripts/seed_demo.py` monta os `Fact` à mão (contrato em `docs/fact_types.md`), troca o CPF das doações por HMAC como
na base pública (`--pseudonimizar`), grava pelo `Store` e roda o motor (`engine.run`), como o `make sample`. O teste
`tests/unit/test_seed_demo.py` confere contagens, regras disparadas e a varredura de CPF.
