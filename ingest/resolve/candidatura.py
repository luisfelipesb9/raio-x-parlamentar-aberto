"""candidatura (TSE) → deputado (Câmara)."""
from __future__ import annotations

from collections import defaultdict

from contracts import Fact
from ingest.resolve.comum import (
    CF_MIN_ENRIQUECER,
    Resolucao,
    confronto_cpf,
    cpf_pleno,
    deputados_unicos,
    nomes_do_deputado,
    normaliza_nome,
)
from repo.links import Ambiguidade, EntityLink

CF_CPF, CF_NOME, CF_NOME_PARTIDO = 1.0, 0.8, 0.7


def _nomes_da_candidatura(c: Fact) -> set[str]:
    a = c.atributos
    return {n for n in (normaliza_nome(a.get("nome_urna")), normaliza_nome(a.get("nome"))) if n}


def resolver_candidaturas(candidaturas: list[Fact], deputados: list[Fact]) -> Resolucao:
    """Liga cada candidatura a um deputado e preenche `deputado_id` + `deputado_cf` (cf ≥ 0,7).

    1. CPF íntegro igual (deputado com `cpf`): cf 1,0.
    2. Nome de urna/civil normalizado + UF, único nos dois sentidos (por eleição): cf 0,8.
    3. Ambíguo: o partido pode desempatar (cf 0,7); sem desempate não liga e registra.
    CPF íntegro diferente nos dois lados descarta o par (homonímia).
    """
    deps = deputados_unicos(deputados)
    por_cpf: dict[str, list[str]] = defaultdict(list)
    por_nome: dict[tuple[str, str], set[str]] = defaultdict(set)
    for k, d in deps.items():
        if cpf := cpf_pleno(d.atributos.get("cpf")):
            por_cpf[cpf].append(k)
        for n in nomes_do_deputado(d):
            por_nome[(d.atributos.get("uf") or "", n)].add(k)

    res = Resolucao()
    ligacao: dict[str, tuple[str, str, float]] = {}  # chave candidatura → (dep, metodo, cf)
    pendentes: dict[str, set[str]] = {}  # chave → deputados que casam por nome
    por_chave = {c.chave: c for c in candidaturas}
    for k, c in por_chave.items():
        if c.atributos.get("deputado_id"):
            res.ja_resolvidos += 1
            continue
        cpf = cpf_pleno(c.atributos.get("cpf"))
        if cpf and len(por_cpf.get(cpf, [])) == 1:
            ligacao[k] = (por_cpf[cpf][0], "cpf", CF_CPF)
            continue
        uf = c.atributos.get("uf") or ""
        achados = {d for n in _nomes_da_candidatura(c) for d in por_nome.get((uf, n), ())
                   if confronto_cpf(c.atributos.get("cpf"), deps[d].atributos.get("cpf"))
                   != "diferente"}
        if achados:
            pendentes[k] = achados
        else:
            res.sem_match.append(f"candidatura:{k}")

    # reverso: por (eleição, deputado), quais candidaturas casaram por nome
    reverso: dict[tuple, set[str]] = defaultdict(set)
    for k, achados in pendentes.items():
        for d in achados:
            reverso[(por_chave[k].atributos.get("ano"), d)].add(k)

    def partido(x: Fact) -> str:
        return normaliza_nome(x.atributos.get("partido"))

    for k, achados in pendentes.items():
        c, ano = por_chave[k], por_chave[k].atributos.get("ano")
        if len(achados) == 1:
            (d,) = achados
            if reverso[(ano, d)] == {k}:
                ligacao[k] = (d, "nome_norm", CF_NOME)
                continue
        # desempate por partido, dos dois lados
        mesmos = [d for d in achados if partido(deps[d]) and partido(deps[d]) == partido(c)]
        if len(mesmos) == 1:
            d = mesmos[0]
            rivais = [o for o in reverso[(ano, d)]
                      if partido(por_chave[o]) and partido(por_chave[o]) == partido(deps[d])]
            if rivais == [k]:
                ligacao[k] = (d, "nome_norm", CF_NOME_PARTIDO)
                continue
        rivais_todos = {o for d in achados for o in reverso[(ano, d)]}
        motivo = ("mais de um deputado com o mesmo nome e UF" if len(achados) > 1
                  else f"mais de uma candidatura ({len(rivais_todos)}) com o mesmo nome e UF")
        res.ambiguos.append(Ambiguidade(f"candidatura:{k}",
                                        tuple(sorted(f"deputado:{d}" for d in achados)), motivo))

    for k, (d, metodo, cf) in ligacao.items():
        res.links.append(EntityLink(f"candidatura:{k}", f"deputado:{d}", metodo, cf))
    for k, c in por_chave.items():
        if k in ligacao and ligacao[k][2] >= CF_MIN_ENRIQUECER and not c.atributos.get(
                "deputado_id"):
            c = c.model_copy(update={"atributos": {
                **c.atributos, "deputado_id": ligacao[k][0], "deputado_cf": ligacao[k][2]}})
        res.fatos.append(c)
    return res
