# engine/
Motor de inferência do Sistema Especialista.
- `certainty.py`: fatores de certeza (MYCIN).
- `rules.py`: carrega regras YAML de knowledge/rules.
- `predicates.py`: funções-condição usadas pelas regras.
- `forward.py`: encadeamento progressivo (gera findings).
- `backward.py`: encadeamento regressivo (prova um objetivo). Esqueleto pronto; Pedro completa.
- `explain.py`: trilha "como" e "por quê".
Entrada: `FactBase`. Saída: list[Finding]. Dono: Luis (núcleo), Pedro (backward).
