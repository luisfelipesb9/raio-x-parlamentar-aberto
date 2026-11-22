# Formato de uma regra (YAML)

```yaml
id: R01                      # único, prefixo R + número
nome: Taxa de governismo
tipo: inferencia             # inferencia | guardrail
categoria: votacao           # votacao | gastos | integridade | producao | emendas
conclui: alinhado_governo    # objetivo para o encadeamento regressivo (opcional)
predicado: taxa_governismo   # função em engine/predicates.py
parametros: {minimo_votacoes: 10}
se: "taxa_governismo >= 0"   # condição sobre valores do predicado (expressão segura)
entao: "Votou com o governo em {taxa_pct}% ..."   # texto leigo; usa {variáveis}
cf: 0.95                     # confiança do especialista na regra (0–1)
penalidades:                 # reduzem o CF quando o dado é incerto
  - {se: "n_votacoes < 30", fator: 0.7, motivo: "Poucas votações"}
por_que: "Por que isso importa para o cidadão"
limitacoes: ["O que a regra NÃO consegue afirmar"]
fonte_metodologica: "Basômetro (Estadão)"
prioridade: 100              # guardrails < 10 rodam antes
```
Arquivos começando com `_` ou `TODO_` são ignorados pelo carregador (só `R*.yaml`).
