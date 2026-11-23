# ADR-004 — Encadeamento regressivo com `requer` e detecção de ciclo
Status: Proposto · 2026-11-22

## Contexto
O plano pede encadeamento **regressivo** para responder perguntas ("o deputado X merece atenção da fiscalização?").
O primeiro `backward.py` só tratava objetivo único. Queríamos sub-objetivos sem tocar o motor ao criar regras.

## Decisão
- Uma regra pode ser **composta**: sem `predicado`, com `requer: [objetivo, ...]` e `conclui`. O carregador
  (`engine/rules.py`) exige exatamente um entre `predicado` e `requer`, e proíbe `se`/`penalidades`/guardrail na composta.
- `backward.prove(goal, deputado_id, fb, rules)`:
  1. Calcula as regras alcançáveis do objetivo (BFS por `requer`) e roda `forward.run` só nelas + guardrails.
  2. `resolve(obj, pilha)` recursivo: regra de folha usa o CF do finding; regra composta usa
     `cf_regra × min(CF dos sub-objetivos)` e só dispara se **todos** forem > 0.
  3. Várias regras para o mesmo objetivo: `certainty.combine_all` (MYCIN).
  4. **Ciclo**: se o objetivo já está na pilha, o ramo vale CF 0 e registra "ciclo detectado: a -> b -> a" na trilha, sem travar.
- O `forward.run` ignora regras compostas: `make infer` não gera finding para R09. A API `/perguntar` devolve CF + trilha (`PassoProva`).

## Consequências
Regras novas encadeiam por dado (YAML) sem alterar código. A trilha mostra profundidade, regra, CF e nota. Fora de escopo:
perguntar ao usuário por fatos faltantes (backward interativo).
