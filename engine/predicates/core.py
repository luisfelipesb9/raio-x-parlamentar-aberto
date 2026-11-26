"""Predicados R01–R04."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from datetime import date
from statistics import median
from typing import Any

from contracts import Evidence, Fact
from engine.diagnostico import Diagnostico
from engine.factbase import FactBase
from engine.predicates.registry import Candidate, diagnostico, guardrail, predicate


# ---------------------------------------------------------------- guardrails
@guardrail("somente_votacoes_nominais")
def somente_votacoes_nominais(fb: FactBase, params: dict) -> tuple[int, str]:
    simbolicas = {v.chave for v in fb.of("votacao") if not v.atributos.get("nominal", False)}
    n = fb.exclude("voto", lambda f: f.atributos["votacao_id"] in simbolicas,
                   motivo="R02_votacao_simbolica")
    fb.exclude("votacao", lambda f: f.chave in simbolicas, motivo="R02_votacao_simbolica")
    return n, f"{len(simbolicas)} votações simbólicas não usadas para atribuir voto individual"


# ---------------------------------------------------------------- inferência
def _votos_validos(fb: FactBase) -> Iterator[tuple[Fact, str, bool]]:
    """(voto, deputado_id, igual_ao_governo) dos votos que entram na taxa de governismo.

    Voto válido = Sim/Não numa votação em que o governo orientou Sim/Não (abstenção, obstrução e
    votação sem orientação ficam fora do denominador). Só vê o que sobrou do guardrail R02."""
    orient = {v.chave: v.atributos.get("orientacao_governo") for v in fb.of("votacao")}
    for voto in fb.of("voto"):
        o = orient.get(voto.atributos["votacao_id"])
        escolha = voto.atributos.get("voto")
        if o not in ("Sim", "Não") or escolha not in ("Sim", "Não"):
            continue
        yield voto, voto.atributos["deputado_id"], escolha == o


@predicate("taxa_governismo")
def taxa_governismo(fb: FactBase, params: dict) -> list[Candidate]:
    """Basômetro: % de votos nominais iguais à orientação do governo."""
    conv, total = defaultdict(int), defaultdict(int)
    ev: dict[str, list[Evidence]] = defaultdict(list)
    for voto, dep, igual in _votos_validos(fb):
        total[dep] += 1
        conv[dep] += int(igual)
        ev[dep].append(Evidence(tipo="votacao", id_oficial=voto.atributos["votacao_id"],
                                url=voto.url))
    minimo = params.get("minimo_votacoes", 10)
    out = []
    for dep, n in total.items():
        if n < minimo:
            continue
        out.append(Candidate(dep, {"taxa_governismo": round(conv[dep] / n, 3),
                                   "n_votacoes": n, "taxa_pct": round(100 * conv[dep] / n)},
                             ev[dep][:20]))
    return out


@diagnostico("taxa_governismo")
def diagnostico_governismo(fb: FactBase, params: dict, deputado_id: str) -> Diagnostico | None:
    """Por que a R01 não concluiu: votos válidos de menos ou taxa abaixo do limiar.

    Usa a mesma contagem do predicado (`_votos_validos`) e o mesmo `minimo_votacoes`. O limiar vem
    de `parametros.limiar` da regra (o mesmo número da condição `se`)."""
    minimo = params.get("minimo_votacoes", 10)
    n = conv = 0
    for _, dep, igual in _votos_validos(fb):
        if dep == deputado_id:
            n += 1
            conv += int(igual)
    detalhes: dict[str, float | int | str] = {"n_votos_validos": n, "minimo_votos": minimo}
    taxa = round(conv / n, 3) if n else None
    if taxa is not None:
        detalhes["taxa"] = taxa
    if n < minimo:
        return Diagnostico("dados_insuficientes", detalhes)
    limiar = params.get("limiar")
    if limiar is not None and taxa is not None and taxa < limiar:
        return Diagnostico("abaixo_do_limiar", {**detalhes, "limiar": limiar})
    return None


@predicate("fornecedor_sancionado")
def fornecedor_sancionado(fb: FactBase, params: dict) -> list[Candidate]:
    """CNPJ que recebeu CEAP enquanto tinha sanção vigente (CEIS/CNEP).

    Só casa por CNPJ preenchido (despesa/sanção de pessoa física não casa). Estornos (valor < 0)
    não contam como pagamento: só valores > 0 entram, e só se o líquido por CNPJ for > 0.
    """
    sancoes = defaultdict(list)
    for s in fb.of("sancao"):
        if s.atributos.get("cnpj"):
            sancoes[s.atributos["cnpj"]].append(s)
    pagos: dict[tuple[str, str], list[tuple[Any, Any]]] = defaultdict(list)  # (dep, cnpj)
    for d in fb.of("despesa_ceap"):
        cnpj = d.atributos.get("cnpj")
        data = _d(d.atributos.get("data"))
        if not cnpj:
            continue
        for s in sancoes.get(cnpj, []):
            ini, fim = _d(s.atributos.get("inicio")), _d(s.atributos.get("fim"))
            if data and ini and data >= ini and (fim is None or data <= fim):
                pagos[(d.atributos["deputado_id"], cnpj)].append((d, s))
                break  # uma despesa conta uma vez, mesmo com várias sanções vigentes
    hits: dict[str, Candidate] = {}
    for (dep, cnpj), pares in pagos.items():
        liquido = sum(float(d.atributos.get("valor", 0)) for d, _ in pares)
        if liquido <= 0:
            continue  # estorno anula o pagamento
        c = hits.setdefault(dep, Candidate(dep, {"n_despesas": 0, "valor_total": 0.0,
                                                 "cnpjs": []}))
        c.valores["valor_total"] = round(c.valores["valor_total"] + liquido, 2)  # líquido
        for d, s in pares:
            if float(d.atributos.get("valor", 0)) <= 0:
                continue
            c.valores["n_despesas"] += 1
            c.evidencias += [Evidence(tipo="despesa_ceap", id_oficial=d.id_oficial, url=d.url),
                             Evidence(tipo="sancao", id_oficial=s.id_oficial, url=s.url,
                                      descricao=s.atributos.get("cadastro"))]
        c.valores["cnpjs"].append(cnpj)
    return list(hits.values())


@predicate("outlier_ceap")
def outlier_ceap(fb: FactBase, params: dict) -> list[Candidate]:
    """Rosie/Serenata simplificado: z-score robusto (MAD) do gasto por categoria."""
    limiar = params.get("z_limiar", 3.5)
    tot: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    ev: dict[tuple[str, str], list[Evidence]] = defaultdict(list)
    for d in fb.of("despesa_ceap"):
        cat, dep = d.atributos.get("categoria", "outros"), d.atributos["deputado_id"]
        tot[cat][dep] += float(d.atributos.get("valor", 0))
        ev[(cat, dep)].append(Evidence(tipo="despesa_ceap", id_oficial=d.id_oficial, url=d.url))
    out: dict[str, Candidate] = {}
    for cat, por_dep in tot.items():
        vals = list(por_dep.values())
        if len(vals) < params.get("minimo_deputados", 5):
            continue
        med = median(vals)
        mad = median(abs(v - med) for v in vals) or 1e-9
        for dep, v in por_dep.items():
            z = 0.6745 * (v - med) / mad
            if z > limiar:
                c = out.setdefault(dep, Candidate(dep, {"categorias": [], "z_max": 0.0}))
                c.valores["categorias"].append(
                    {"categoria": cat, "valor": round(v, 2), "mediana": round(med, 2)})
                c.valores["z_max"] = round(max(c.valores["z_max"], z), 2)
                c.evidencias += ev[(cat, dep)][:10]
    for c in out.values():
        top = max(c.valores["categorias"], key=lambda x: x["valor"] / max(x["mediana"], 1))
        c.valores.update(categoria_top=top["categoria"], valor_top=top["valor"],
                         mediana_top=top["mediana"],
                         vezes_mediana=round(top["valor"] / max(top["mediana"], 1), 1))
    return list(out.values())


def _d(v: Any) -> date | None:
    if v is None or isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])
