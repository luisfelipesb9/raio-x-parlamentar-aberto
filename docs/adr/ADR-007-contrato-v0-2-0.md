# ADR-007 — Contrato v0.2.0: transparência do corte, diagnóstico, proveniência e cobertura
Status: Proposto · 2026-11-26

## Contexto
Quatro lacunas do contrato 0.1.0 aparecem para quem lê a ficha, o grafo e o `/perguntar`:
1. **Corte do grafo.** `GrafoResposta` só diz `truncado: true`. Não diz quanto havia no total nem o que ficou de fora, então o leitor
   não sabe se o limite de nós escondeu algo importante.
2. **Resultado "Inconclusivo".** O passo da trilha do `/perguntar` traz só uma nota em texto. Não dá para distinguir, por máquina,
   "poucos votos para concluir" de "olhei e não passou do limiar" de "nenhuma regra se aplica".
3. **Proveniência.** `Fact` guarda `coletado_em`, mas `Evidence` (o que o leitor vê) não: a ficha não mostra de quando é o dado nem
   qual arquivo bruto o originou.
4. **Cobertura.** Não existe um lugar para dizer o que a base tem de cada fonte, de que período são as votações e quantas têm voto
   nominal ou orientação de bancada. Sem isso, a ausência de achado pode ser lida como ausência de problema.

## Decisão
Subir `CONTRACT_VERSION` de `0.1.0` para `0.2.0`, só com campos e modelos **novos e opcionais**:
- **Grafo** (`api/schemas.py`): `GrafoResposta` ganha `total_nos: int | None`, `total_arestas: int | None` e
  `ocultos: list[OcultoResumo]` (padrão `[]`). `OcultoResumo{tipo, relacao, quantidade}` resume o que o limite de nós cortou, por tipo
  de nó e relação. O comentário de `contracts/graph.py` passa a listar o tipo de nó `pessoa` e as relações `enviou_emenda` e `relator_de`.
- **Diagnóstico**: `PassoProva` ganha `diagnostico: Diagnostico | None`. `Diagnostico{motivo, detalhes}`, com `motivo` fechado em
  `dados_insuficientes | abaixo_do_limiar | sem_regra_aplicavel` e `detalhes: dict[str, float | int | str]`. Convenção para a R01:
  `n_votos_validos`, `minimo_votos`, `taxa`, `limiar`.
- **Proveniência**: `Evidence` ganha `coletado_em: datetime | None` e `sha256_bruto: str | None`. `Fact.coletado_em` não muda.
- **Cobertura e métricas** (`api/schemas.py`, **ainda sem endpoint**): `JanelaVotos`, `FonteCobertura`, `CoberturaResposta`, `MetricaRegra` e
  `MetricasDeputadoResposta`. Os modelos entram agora para o contrato e os tipos do web ficarem estáveis antes da implementação.
- Os JSON Schemas (`scripts/export_schemas.py`) e os tipos TypeScript (`pnpm gen:types`) são regenerados na mesma mudança.

Esta decisão cobre **só o contrato**. A lógica que preenche os campos novos (contagem do que o limite cortou, diagnóstico na R01,
preenchimento da proveniência, endpoints de cobertura e métricas) fica para mudanças seguintes, cada uma com seus testes.

## Compatibilidade
- Todo campo novo tem padrão (`None` ou lista vazia). Um `GrafoResposta`, `PassoProva` ou `Evidence` antigo continua válido na API
  Python; clientes que ignoram campos desconhecidos não quebram.
- No web, os tipos TS gerados tornam todo campo obrigatório (a API serializa os padrões). Quem monta esses objetos à mão (testes,
  dados de exemplo) precisa incluir os campos novos com `null` ou `[]`.
- Nenhum campo foi removido, renomeado ou teve o tipo mudado; por isso o salto é de versão menor.

## Consequências
- Enquanto a lógica não vier, a API devolve `total_nos`, `total_arestas` e `diagnostico` como `null` e `ocultos` como `[]`.
  O web não deve tratar `null` como "zero" nem como "sem corte".
- `Evidence.sha256_bruto` e `coletado_em` só terão valor depois que o ingest guardar o hash do bruto; até lá, `null`.
- Os modelos de cobertura e métricas ficam sem consumidor até os endpoints existirem; se o formato mudar antes disso, o custo é baixo
  (nenhum cliente depende deles).
- Cada novo campo preenchido por lógica deve citar este ADR no teste que o cobre.
