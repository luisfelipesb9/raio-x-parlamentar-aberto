"""pep (OpenSanctions) → deputado (Câmara). Só links; o fato `pep` não muda."""
from __future__ import annotations

from collections import defaultdict

from contracts import Fact
from ingest.resolve.comum import (
    Resolucao,
    confronto_cpf,
    cpf_pleno,
    deputados_unicos,
    normaliza_nome,
)
from repo.links import Ambiguidade, EntityLink

CF_CPF_NOME, CF_NOME_CIVIL, CF_NOME_PARLAMENTAR = 0.95, 0.7, 0.5
CF_LINK_FORTE = 0.8  # só candidatura ligada com ao menos isto empresta nome civil/CPF ao deputado


class _Perfil:
    def __init__(self) -> None:
        self.civis: set[str] = set()
        self.parlamentares: set[str] = set()
        self.cpfs: set[str] = set()


def _perfis(deputados: list[Fact], candidaturas: list[Fact],
            links_candidatura: list) -> dict[str, _Perfil]:
    perfis: dict[str, _Perfil] = defaultdict(_Perfil)
    for k, d in deputados_unicos(deputados).items():
        p = perfis[k]
        if n := normaliza_nome(d.atributos.get("nome")):
            p.parlamentares.add(n)
        if n := normaliza_nome(d.atributos.get("nome_civil")):
            p.civis.add(n)
        if cpf := cpf_pleno(d.atributos.get("cpf")):
            p.cpfs.add(cpf)
    por_chave = {c.chave: c for c in candidaturas}
    for lk in links_candidatura:
        if lk.cf < CF_LINK_FORTE or not lk.destino.startswith("deputado:"):
            continue
        c = por_chave.get(lk.origem.removeprefix("candidatura:"))
        d = lk.destino.removeprefix("deputado:")
        if c is None or d not in perfis:
            continue
        p = perfis[d]
        if n := normaliza_nome(c.atributos.get("nome")):
            p.civis.add(n)
        if n := normaliza_nome(c.atributos.get("nome_urna")):
            p.parlamentares.add(n)
        if cpf := cpf_pleno(c.atributos.get("cpf")):
            p.cpfs.add(cpf)
    return perfis


def resolver_peps(peps: list[Fact], deputados: list[Fact], candidaturas: list[Fact] = (),
                  links_candidatura: list = ()) -> Resolucao:
    """Níveis (vale o melhor, que precisa ser único): nome + CPF mascarado compatível 0,95;
    nome civil 0,7; nome parlamentar 0,5. CPF mascarado incompatível descarta o par — com 6
    dígitos visíveis o CPF sozinho NÃO basta (colidiria entre centenas de milhares de PEPs)."""
    perfis = _perfis(list(deputados), list(candidaturas), list(links_candidatura))
    idx_civil: dict[str, set[str]] = defaultdict(set)
    idx_parl: dict[str, set[str]] = defaultdict(set)
    for k, p in perfis.items():
        for n in p.civis:
            idx_civil[n].add(k)
        for n in p.parlamentares:
            idx_parl[n].add(k)

    res = Resolucao(fatos=list(peps))
    for pe in peps:
        origem, nome = f"pep:{pe.chave}", normaliza_nome(pe.atributos.get("nome"))
        cpfs_pep = [c for c in (pe.atributos.get("cpfs") or [pe.atributos.get("cpf")]) if c]

        def cpf_ok(d: str, pe_cpfs=cpfs_pep) -> str:
            sts = {confronto_cpf(c, x) for c in pe_cpfs for x in perfis[d].cpfs}
            return ("compativel" if sts & {"compativel", "igual"}
                    else "diferente" if "diferente" in sts else "desconhecido")

        niveis = [(CF_NOME_CIVIL, idx_civil.get(nome, set())),
                  (CF_NOME_PARLAMENTAR, idx_parl.get(nome, set()))]
        melhor: tuple[float, set[str], str] | None = None
        for cf, deps in niveis:
            deps = {d for d in deps if cpf_ok(d) != "diferente"}
            if not deps:
                continue
            confirmados = {d for d in deps if cpf_ok(d) == "compativel"}
            cand = (CF_CPF_NOME, confirmados, "cpf") if confirmados else (cf, deps, "nome_norm")
            if melhor is None or cand[0] > melhor[0]:
                melhor = cand
        if melhor is None:
            res.sem_match.append(origem)
        elif len(melhor[1]) == 1:
            (d,) = melhor[1]
            res.links.append(EntityLink(origem, f"deputado:{d}", melhor[2], melhor[0]))
        else:
            res.ambiguos.append(Ambiguidade(origem, tuple(sorted(f"deputado:{d}" for d in melhor[1])),
                                            "nome casa com mais de um deputado"))
    return res
