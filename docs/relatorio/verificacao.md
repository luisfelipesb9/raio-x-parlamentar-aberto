# Verificação dos dados contra o bruto

Gerado em 2026-11-26 por `python -m scripts.verifica` (`make verifica`). Banco: `raio_x_sample.duckdb` (20 deputados). Brutos: pasta `raw`.

**Resultado:** **APROVADO**: nenhuma divergência.

44 conferências: 44 ok, 0 com divergência, 0 não verificadas.

| verificação | ok | diverge | não verificado |
|---|---|---|---|
| Votações | 3 | 0 | 0 |
| Governismo (R01) | 20 | 0 | 0 |
| Despesas CEAP | 20 | 0 | 0 |
| Manifesto do bruto | 1 | 0 | 0 |

## Divergências

Nenhuma divergência.

## Não verificado

Nada ficou sem verificar nas conferências executadas.

## Todas as conferências

### Votações

| item | bruto (esperado) | banco/motor (obtido) | status |
|---|---|---|---|
| votações | 145 | 145 | ok |
| votações nominais | 24 | 24 | ok |
| votações com orientação Sim/Não | 22 | 22 | ok |

### Governismo (R01)

| item | bruto (esperado) | banco/motor (obtido) | status |
|---|---|---|---|
| 74156 Leonardo Monteiro | 18 votos, taxa 0.889, dispara | 18 votos, taxa 0.889, dispara | ok |
| 74158 Mário Heringer | 18 votos, taxa 1.0, dispara | 18 votos, taxa 1.0, dispara | ok |
| 74159 Odair Cunha | 14 votos, taxa 1.0, dispara | 14 votos, taxa 1.0, dispara | ok |
| 74160 Patrus Ananias | 20 votos, taxa 1.0, dispara | 20 votos, taxa 1.0, dispara | ok |
| 74161 Reginaldo Lopes | 12 votos, taxa 1.0, dispara | 12 votos, taxa 1.0, dispara | ok |
| 74581 Gilmar Machado | 0 votos, taxa —, não dispara | 0 votos, taxa —, não dispara | ok |
| 74585 Lincoln Portela | 17 votos, taxa 0.529, não dispara | 17 votos, taxa 0.529, não dispara | ok |
| 74646 Aécio Neves | 9 votos, taxa 1.0, não dispara | 9 votos, taxa 1.0, não dispara | ok |
| 77003 Sergio Santos Rodrigues | 0 votos, taxa —, não dispara | 0 votos, taxa —, não dispara | ok |
| 92776 Stefano Aguiar | 17 votos, taxa 0.882, dispara | 17 votos, taxa 0.882, dispara | ok |
| 98057 Lafayette de Andrada | 9 votos, taxa 0.889, não dispara | 9 votos, taxa 0.889, não dispara | ok |
| 107970 Ana Paula Leão | 13 votos, taxa 0.769, dispara | 13 votos, taxa 0.769, dispara | ok |
| 141487 Luiz Fernando Faria | 12 votos, taxa 0.917, dispara | 12 votos, taxa 0.917, dispara | ok |
| 141516 Paulo Abi-Ackel | 13 votos, taxa 1.0, dispara | 13 votos, taxa 1.0, dispara | ok |
| 141531 Rodrigo de Castro | 21 votos, taxa 1.0, dispara | 21 votos, taxa 1.0, dispara | ok |
| 160510 Luis Tibé | 6 votos, taxa 1.0, não dispara | 6 votos, taxa 1.0, não dispara | ok |
| 160518 Weliton Prado | 16 votos, taxa 0.875, dispara | 16 votos, taxa 0.875, dispara | ok |
| 160556 Padre João | 16 votos, taxa 1.0, dispara | 16 votos, taxa 1.0, dispara | ok |
| 160588 Diego Andrade | 16 votos, taxa 0.938, dispara | 16 votos, taxa 0.938, dispara | ok |
| 160599 Dimas Fabiano | 17 votos, taxa 1.0, dispara | 17 votos, taxa 1.0, dispara | ok |

### Despesas CEAP

| item | bruto (esperado) | banco/motor (obtido) | status |
|---|---|---|---|
| 74156 Leonardo Monteiro | 373 despesas, R$ 511.827,49 | 373 despesas, R$ 511.827,49 | ok |
| 74158 Mário Heringer | 125 despesas, R$ 323.076,87 | 125 despesas, R$ 323.076,87 | ok |
| 74159 Odair Cunha | 880 despesas, R$ 524.034,98 | 880 despesas, R$ 524.034,98 | ok |
| 74160 Patrus Ananias | 1260 despesas, R$ 452.144,87 | 1260 despesas, R$ 452.144,87 | ok |
| 74161 Reginaldo Lopes | 519 despesas, R$ 494.417,40 | 519 despesas, R$ 494.417,40 | ok |
| 74581 Gilmar Machado | 0 despesas, R$ 0,00 | 0 despesas, R$ 0,00 | ok |
| 74585 Lincoln Portela | 537 despesas, R$ 503.732,34 | 537 despesas, R$ 503.732,34 | ok |
| 74646 Aécio Neves | 413 despesas, R$ 479.997,65 | 413 despesas, R$ 479.997,65 | ok |
| 77003 Sergio Santos Rodrigues | 0 despesas, R$ 0,00 | 0 despesas, R$ 0,00 | ok |
| 92776 Stefano Aguiar | 414 despesas, R$ 511.491,85 | 414 despesas, R$ 511.491,85 | ok |
| 98057 Lafayette de Andrada | 534 despesas, R$ 423.227,47 | 534 despesas, R$ 423.227,47 | ok |
| 107970 Ana Paula Leão | 575 despesas, R$ 457.596,92 | 575 despesas, R$ 457.596,92 | ok |
| 141487 Luiz Fernando Faria | 420 despesas, R$ 466.780,52 | 420 despesas, R$ 466.780,52 | ok |
| 141516 Paulo Abi-Ackel | 821 despesas, R$ 501.103,25 | 821 despesas, R$ 501.103,25 | ok |
| 141531 Rodrigo de Castro | 639 despesas, R$ 484.881,34 | 639 despesas, R$ 484.881,34 | ok |
| 160510 Luis Tibé | 487 despesas, R$ 429.681,42 | 487 despesas, R$ 429.681,42 | ok |
| 160518 Weliton Prado | 184 despesas, R$ 498.000,74 | 184 despesas, R$ 498.000,74 | ok |
| 160556 Padre João | 732 despesas, R$ 487.026,70 | 732 despesas, R$ 487.026,70 | ok |
| 160588 Diego Andrade | 544 despesas, R$ 501.048,82 | 544 despesas, R$ 501.048,82 | ok |
| 160599 Dimas Fabiano | 1493 despesas, R$ 439.428,73 | 1493 despesas, R$ 439.428,73 | ok |

### Manifesto do bruto

| item | bruto (esperado) | banco/motor (obtido) | status |
|---|---|---|---|
| manifest.json | 309 arquivos | 309 arquivos | ok |

## Como ler e limites

- Contagens: tolerância zero. Valores em reais: até 1 centavo (somados em centavos, sem float).
- "Bruto" é recalculado do JSON da Câmara e do zip da CEAP sem usar o motor; "banco" é a consulta SQL aos fatos; "motor" é o finding da R01 gravado por `make infer`.
- Governismo e CEAP conferem os deputados que estão no banco (a amostra), não os 513.
- Isto confere o caminho bruto → banco → motor. Não prova que o dado oficial está certo, só que o sistema o reproduz sem perder nem inventar nada.
- O manifesto foi gerado agora para 309 arquivo(s) que já existiam (origem `retroativo`): o hash prova que o arquivo não mudou daqui em diante, não que é idêntico ao que foi baixado na época.
- A conferência `--online` (contagem de votos direto na API da Câmara) não foi executada.
