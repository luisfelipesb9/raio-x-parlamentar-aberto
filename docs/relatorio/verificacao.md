# Verificação dos dados contra o bruto

Gerado em 2026-11-26 por `python -m scripts.verifica` (`make verifica`). Banco: `raio_x_publico.duckdb` (20 deputados). Brutos: pasta `data/raw`.

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
| 74156 Leonardo Monteiro | 243 despesas, R$ 406.695,79 | 243 despesas, R$ 406.695,79 | ok |
| 74158 Mário Heringer | 41 despesas, R$ 195.568,86 | 41 despesas, R$ 195.568,86 | ok |
| 74159 Odair Cunha | 803 despesas, R$ 454.247,12 | 803 despesas, R$ 454.247,12 | ok |
| 74160 Patrus Ananias | 1154 despesas, R$ 412.340,83 | 1154 despesas, R$ 412.340,83 | ok |
| 74161 Reginaldo Lopes | 229 despesas, R$ 159.003,83 | 229 despesas, R$ 159.003,83 | ok |
| 74581 Gilmar Machado | 0 despesas, R$ 0,00 | 0 despesas, R$ 0,00 | ok |
| 74585 Lincoln Portela | 456 despesas, R$ 446.690,27 | 456 despesas, R$ 446.690,27 | ok |
| 74646 Aécio Neves | 264 despesas, R$ 324.515,32 | 264 despesas, R$ 324.515,32 | ok |
| 77003 Sergio Santos Rodrigues | 0 despesas, R$ 0,00 | 0 despesas, R$ 0,00 | ok |
| 92776 Stefano Aguiar | 348 despesas, R$ 453.078,05 | 348 despesas, R$ 453.078,05 | ok |
| 98057 Lafayette de Andrada | 440 despesas, R$ 422.498,15 | 440 despesas, R$ 422.498,15 | ok |
| 107970 Ana Paula Leão | 536 despesas, R$ 461.940,01 | 536 despesas, R$ 461.940,01 | ok |
| 141487 Luiz Fernando Faria | 264 despesas, R$ 368.935,33 | 264 despesas, R$ 368.935,33 | ok |
| 141516 Paulo Abi-Ackel | 586 despesas, R$ 358.323,56 | 586 despesas, R$ 358.323,56 | ok |
| 141531 Rodrigo de Castro | 478 despesas, R$ 363.754,62 | 478 despesas, R$ 363.754,62 | ok |
| 160510 Luis Tibé | 273 despesas, R$ 266.178,16 | 273 despesas, R$ 266.178,16 | ok |
| 160518 Weliton Prado | 141 despesas, R$ 447.225,31 | 141 despesas, R$ 447.225,31 | ok |
| 160556 Padre João | 646 despesas, R$ 451.715,33 | 646 despesas, R$ 451.715,33 | ok |
| 160588 Diego Andrade | 366 despesas, R$ 361.386,09 | 366 despesas, R$ 361.386,09 | ok |
| 160599 Dimas Fabiano | 1430 despesas, R$ 387.364,50 | 1430 despesas, R$ 387.364,50 | ok |

### Manifesto do bruto

| item | bruto (esperado) | banco/motor (obtido) | status |
|---|---|---|---|
| manifest.json | 309 arquivos | 309 arquivos | ok |

## Como ler e limites

- Contagens: tolerância zero. Valores em reais: até 1 centavo (somados em centavos, sem float).
- "Bruto" é recalculado do JSON da Câmara e do zip da CEAP sem usar o motor; "banco" é a consulta SQL aos fatos; "motor" é o finding da R01 gravado por `make infer`.
- Governismo e CEAP conferem os deputados que estão no banco (a amostra), não os 513.
- Isto confere o caminho bruto → banco → motor. Não prova que o dado oficial está certo, só que o sistema o reproduz sem perder nem inventar nada.
- A conferência `--online` (contagem de votos direto na API da Câmara) não foi executada.
