"""R05 — Produção legislativa ponderada (Radar da República V2)."""
from __future__ import annotations

import math
from collections import defaultdict

from contracts import Evidence
from engine.factbase import FactBase
from engine.predicates.registry import Candidate, predicate


@predicate("producao_ponderada")
def producao_ponderada(fb: FactBase, params: dict) -> list[Candidate]:
    """Score 0–40: 32·(1−e^(−iniciativa/25)) + 8·(1−e^(−relatorias/10,57)).

    iniciativa = autorias + 0,25·coautorias. Só pontua quem TEM fatos `autoria`; deputado sem
    nenhum registro fica de fora (lacuna de dado ≠ produção zero).
    """
    peso_co = params.get("peso_coautor", 0.25)
    max_ini, esc_ini = params.get("max_iniciativa", 32), params.get("escala_iniciativa", 25)
    max_rel, esc_rel = params.get("max_relatoria", 8), params.get("escala_relatoria", 10.57)
    papeis: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    ev: dict[str, list[Evidence]] = defaultdict(list)
    for a in fb.of("autoria"):
        dep, papel = a.atributos["deputado_id"], a.atributos.get("papel")
        if papel not in ("autor", "coautor", "relator"):
            continue
        papeis[dep][papel].add(a.atributos["proposicao_id"])
        ev[dep].append(Evidence(tipo="autoria", id_oficial=a.id_oficial, url=a.url))
    out: dict[str, Candidate] = {}
    for dep, p in papeis.items():
        autor, relator = len(p["autor"]), len(p["relator"])
        coautor = len(p["coautor"] - p["autor"])  # autor prevalece sobre coautor
        ini = autor + peso_co * coautor
        pts = max_ini * (1 - math.exp(-ini / esc_ini)) + max_rel * (1 - math.exp(-relator / esc_rel))
        out[dep] = Candidate(dep, {
            "autorias": autor, "coautorias": coautor, "relatorias": relator,
            "iniciativa": round(ini, 2), "pontos": round(pts, 2), "pontos_max": max_ini + max_rel,
        }, ev[dep][:20])
    # contexto (nunca conclusão pessoal): média do partido, só com ≥ N colegas com dados
    partido = {d.chave: d.atributos.get("partido") for d in fb.of("deputado")}
    por_partido: dict[str, list[float]] = defaultdict(list)
    for dep, c in out.items():
        if partido.get(dep):
            por_partido[partido[dep]].append(c.valores["pontos"])
    minimo = params.get("minimo_colegas_partido", 3)
    for dep, c in out.items():
        vals = por_partido.get(partido.get(dep) or "", [])
        c.valores["contexto_media_partido"] = round(sum(vals) / len(vals), 2) \
            if len(vals) >= minimo else None
    return list(out.values())
