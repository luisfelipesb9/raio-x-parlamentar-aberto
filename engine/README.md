# engine/
Motor de inferência do Sistema Especialista.
- `certainty.py`: fatores de certeza (MYCIN).
- `rules.py`: carrega regras YAML de knowledge/rules.
- `predicates/`: funções-condição usadas pelas regras (core R01–R04, producao R05, circuito R06, emendas R07, presuncao R08).
- `forward.py`: encadeamento progressivo (gera findings).
- `backward.py`: encadeamento regressivo com sub-objetivos (`requer`), ciclo detectado, trilha de prova.
- `explain.py`: trilha "como" e "por quê".
Entrada: `FactBase`. Saída: list[Finding]. Dono: Luis (núcleo), Pedro (backward).
