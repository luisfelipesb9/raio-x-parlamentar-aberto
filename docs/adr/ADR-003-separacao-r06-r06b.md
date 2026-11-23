# ADR-003 — Separação R06/R06b e teto de CF para identidade não confirmada
Status: Proposto · 2026-11-22

## Contexto
O circuito doador-sócio-fornecedor casa o sócio de uma empresa paga com a CEAP e um doador pessoa física da
campanha do mesmo deputado **pelo nome normalizado**. O CPF do sócio na Receita vem mascarado (`***123456**`),
então o nome sozinho pode ser homonímia. Com uma só regra, o motor combinaria (MYCIN) um caso confirmado com
vários casos não confirmados e um deles "emprestaria" CF alto aos outros; e o nome de um inocente poderia
aparecer na conclusão.

## Decisão
Duas regras, ambas sobre o predicado `circuito_doador_socio`, distinguidas por `parametros.modo`:
- **R06 (modo `confirmado`)**: CPF íntegro igual nos dois lados. cf 0,85.
- **R06b (modo `indicio`)**: CPF mascarado ou ausente, dígitos visíveis compatíveis. cf 0,85 com penalidade
  `n_confirmados == 0` ×0,4, ou seja CF final 0,34 (nível **indício**, ≤ 0,4 por construção). Dígitos visíveis incompatíveis
  ou CPF íntegro diferente descartam o par.
- Cada par vai para exatamente uma regra; um confirmado nunca eleva um não confirmado.
- Na R06b o nome do sócio **não** é exposto na conclusão nem nos `valores` (LGPD); só R06 inclui `socios`.
- Texto da conclusão traz a `ressalva` ("identidade confirmada pelo CPF" / "indício sujeito a confirmação").

## Consequências
Comportamento verificado por teste (CPF mascarado → CF ≤ 0,4, como previsto no plano). Um mesmo deputado pode ter
findings `R06:ID` e `R06b:ID`. Ambas concluem `risco_integridade` e, no regressivo, são combinadas por MYCIN.
O teto de 0,4 vale **por finding** (R06b isolada). No regressivo os sinais se combinam por MYCIN: R06b (0,34) ⊕ R04 (0,4) = 0,34 + 0,4·0,66 = 0,604, e R09 = 0,8 × 0,604 ≈ 0,48. Isso é intencional: duas evidências independentes fortalecem a conclusão `risco_integridade`, mas nenhuma delas isolada passa de indício.
Qualquer mudança do teto 0,4 exige revisão deste ADR.
