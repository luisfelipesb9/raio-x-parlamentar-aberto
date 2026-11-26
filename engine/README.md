# engine/
Motor de inferência do Sistema Especialista.
- `certainty.py`: fatores de certeza (MYCIN).
- `rules.py`: carrega regras YAML de knowledge/rules.
- `predicates/`: funções-condição usadas pelas regras (core R01–R04, producao R05, circuito R06, emendas R07, presuncao R08).
- `forward.py`: encadeamento progressivo (gera findings).
- `backward.py`: encadeamento regressivo com sub-objetivos (`requer`), ciclo detectado, trilha de prova.
- `explain.py`: trilha "como" e "por quê".
- `diagnostico.py` + `@diagnostico` (em `predicates/registry.py`): por que um passo da prova ficou sem conclusão
  (`dados_insuficientes`, `abaixo_do_limiar`, `sem_regra_aplicavel`). Só a R01 tem diagnosticador; regra nova cai em
  `sem_regra_aplicavel` até registrar o seu. Nunca muda CF nem decisão.
- `proveniencia.py`: preenche `Evidence.coletado_em` (do fato de origem) e `sha256_bruto` (só se a fonte tem um único arquivo bruto no manifesto).
Entrada: `FactBase`. Saída: list[Finding]. Dono: Luis (núcleo), Pedro (backward).
