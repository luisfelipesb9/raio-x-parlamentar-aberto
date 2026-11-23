"""R07 — Concentração eleitoral de emendas (Radar do Voto).

Compara a fatia de votos do deputado (votos / votos válidos) nos municípios que receberam
emendas dele com a fatia nos demais municípios da UF em que ele teve votação registrada.
Municípios sem linha em `votos_municipio` ficam fora das duas médias (não se inventa voto zero).
"""
from __future__ import annotations

from collections import defaultdict

from contracts import Evidence
from engine.factbase import FactBase
from engine.predicates.registry import Candidate, predicate


@predicate("concentracao_emendas")
def concentracao_emendas(fb: FactBase, params: dict) -> list[Candidate]:
    ano_pix = params.get("ano_pix_rastreavel", 2027)
    sq_dep = {c.chave: c.atributos["deputado_id"] for c in fb.of("candidatura")
              if c.atributos.get("deputado_id")}
    sq_cf = {c.chave: float(c.atributos.get("deputado_cf", 1.0)) for c in fb.of("candidatura")}
    emendas: dict[str, list] = defaultdict(list)
    for e in fb.of("emenda"):
        if e.atributos.get("deputado_id") and float(e.atributos.get("valor_empenhado") or 0) > 0:
            emendas[e.atributos["deputado_id"]].append(e)
    votos: dict[str, list] = defaultdict(list)
    for v in fb.of("votos_municipio"):
        dep = sq_dep.get(v.atributos.get("sq_candidato"))
        if dep:
            votos[dep].append(v)
    out = []
    for dep, linhas in emendas.items():
        ems = list({e.chave: e for e in linhas}.values())  # uma emenda = uma chave
        rows = votos.get(dep)
        if not rows:
            continue
        ultimo = max(int(v.atributos.get("ano", 0)) for v in rows)  # só a eleição mais recente
        rows = [v for v in rows if int(v.atributos.get("ano", 0)) == ultimo]
        destino_ibge = {str(e.atributos["municipio_ibge"]) for e in linhas
                        if e.atributos.get("municipio_ibge")}
        dest = [v for v in rows if str(v.atributos["municipio_ibge"]) in destino_ibge]
        resto = [v for v in rows if str(v.atributos["municipio_ibge"]) not in destino_ibge]
        pct_dest, pct_resto = _fatia(dest), _fatia(resto)
        if not dest or not resto or pct_dest is None or not pct_resto:
            continue  # sem comparação possível (ou 0% no resto: não dividimos por zero)
        pix = [e for e in ems if e.atributos.get("tipo") == "pix"
               and int(e.atributos.get("ano") or 0) < ano_pix]
        premissas = [float(e.atributos.get("deputado_cf", 1.0)) for e in linhas]
        premissas += [sq_cf.get(v.atributos.get("sq_candidato"), 1.0) for v in rows]
        out.append(Candidate(dep, {
            "pct_destino": round(pct_dest, 2), "pct_resto": round(pct_resto, 2),
            "razao": round(pct_dest / pct_resto, 3), "n_municipios_destino": len(dest),
            "n_municipios_resto": len(resto), "n_emendas": len(ems),
            "valor_emendas": round(sum(float(e.atributos["valor_empenhado"]) for e in ems), 2),
            "n_emendas_pix_pre_2027": len(pix), "ano_eleicao": ultimo,
        }, [Evidence(tipo="emenda", id_oficial=e.id_oficial, url=e.url) for e in ems[:10]]
            + [Evidence(tipo="votos_municipio", id_oficial=v.id_oficial, url=v.url)
               for v in dest[:5]], premissas_cf=[min(premissas)]))
    return out


def _fatia(rows: list) -> float | None:
    validos = sum(float(v.atributos.get("votos_validos_municipio") or 0) for v in rows)
    if validos <= 0:
        return None
    return 100 * sum(float(v.atributos.get("votos") or 0) for v in rows) / validos
