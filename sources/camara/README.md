# sources/camara

Conector da Câmara dos Deputados (API v2 e dumps anuais oficiais). Medições de 2026-11-26.

## Escopo dos deputados
- **Padrão: deputados em exercício** (513): `GET /deputados` sem `idLegislatura`.
- **Legislatura inteira** (878 na 57ª, com suplentes que já passaram): só por opção explícita,
  `CamaraSource.fetch(legislatura_completa=True)` (e `legislatura=<n>` para outra legislatura).
  Passar `legislatura=57` sozinho **não** amplia o escopo.

## Robustez
- Nova tentativa em **429, 5xx e erro de rede/timeout**: até 5 tentativas, espera `2 s × 2^(n-1)` (teto de
  60 s) ou o `Retry-After` do servidor. Outro 4xx sobe na hora. Mesmo padrão da RFB.
- **Pausa entre chamadas**: 0,2 s por padrão (`CamaraSource(pausa=...)`). A API não documenta limite.
- **Checkpoint por etapa** em `data/raw/camara/parcial/*.json.part` (o manifesto ignora `.part`): lista de
  deputados, detalhe dos deputados (a cada 25), cada trimestre de votações (listagem + votos, a cada 25) e as
  proposições (a cada 25). O `fetch` só apaga o que ele mesmo guardou (o parcial de `fetch_proposicoes`, que o
  pipeline roda depois, sobrevive). Se a coleta cair, a chamada seguinte **retoma dali** (`retomar=False` refaz tudo).
  Coleta concluída apaga o parcial. O bruto final `camara_<início>_<fim>.json` **não mudou de formato**.
- Erro HTTP numa proposição ou num detalhe de deputado continua registrado em `*_erros` e é tentado de novo na
  coleta seguinte (não vira dado guardado).

## Votos em janela longa
- A API recusa mais de 3 meses (HTTP 400: "A diferença entre as datas não pode ser maior que 3 meses"):
  `fetch` **fatia** a janela em trimestres (`janelas.fatiar_janela`); `max_votacoes` vale para a janela toda.
- Alternativa: `fetch(fonte_votos="dump")` lê os CSV anuais oficiais
  `https://dadosabertos.camara.leg.br/arquivos/{votacoes,votacoesVotos,votacoesOrientacoes}/csv/<conjunto>-<ano>.csv`
  (UTF-8 com BOM, `;`), em streaming, para `data/raw/camara/dumps/`. Ano de 2025: votacoes 8,4 MiB,
  votacoesVotos 55,5 MiB, votacoesOrientacoes 1,0 MiB. O dump muda todo dia: só é reaproveitado do disco com
  `reusar_dumps=True`.
- **Só votação nominal de Plenário** vira voto individual. Votação simbólica não tem linha no arquivo de votos
  (`_votos == []`, `nominal=False`); voto de comissão é descartado. Mesmos `Fact` (`votacao`, `voto`).
- O leitor confere o cabeçalho e cada linha: coluna ausente, arquivo vazio ou linha curta (download truncado)
  viram erro claro com o nome do arquivo. O cliente HTTP manda `Accept: application/json` e o servidor dos dumps
  responde o CSV normalmente (conferido com `curl -r 0-2000` em 2026-11-26).
- Recomendado para mais de um trimestre.

## Proposições
- **Sem teto por padrão** (`max_proposicoes=None`): é o modo para os 513. O teto existe só para demonstração
  e avisa no log quando corta de fato: fica com as de menor id da janela (as mais antigas), uma amostra enviesada.
- Custo: 1+ chamada por autor + 2 por proposição (autores e tramitações, de onde vem a relatoria). O dump
  `proposicoes-<ano>.csv` (~90 MB em 2025) + `proposicoesAutores-<ano>.csv` (~39 MB) não foi implementado:
  ele não traz a relatoria.

## Detalhe dos deputados
`detalhar_deputados=True` (ou lista de ids): 1 chamada por deputado a `/deputados/{id}`. Guarda **só** o CPF e o
nome civil que a API pública devolve; nada de terceiros.

## Migração
O formato de `data/raw/camara/` não mudou; acrescentam-se as subpastas `parcial/` (transitória) e `dumps/`.
Um `camara_<início>_<fim>.json` antigo foi baixado com a legislatura inteira (878); com `--reusar-raw` o
pipeline o reaproveita como está. Apague-o para refazer com os 513.
