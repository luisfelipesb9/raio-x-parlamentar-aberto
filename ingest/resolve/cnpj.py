"""despesa_ceap.cnpj ↔ empresa / sancao, por CNPJ exato (cf 1,0)."""
from __future__ import annotations

from collections import defaultdict

from contracts import Fact
from ingest.resolve.comum import Resolucao
from repo.links import EntityLink


def resolver_cnpj(despesas: list[Fact], empresas: list[Fact], sancoes: list[Fact]) -> Resolucao:
    """Um link por (despesa, empresa) e por (despesa, sanção) com o mesmo CNPJ. Despesa sem
    CNPJ (CPF, telefonia) ou sem empresa/sanção conhecida não gera nada. Não altera fatos."""
    empresa = {e.chave for e in empresas}
    sancoes_do: dict[str, list[Fact]] = defaultdict(list)
    for s in sancoes:
        if cnpj := s.atributos.get("cnpj"):
            sancoes_do[cnpj].append(s)
    res = Resolucao(fatos=list(despesas))
    for d in despesas:
        cnpj = d.atributos.get("cnpj")
        if not cnpj:
            continue
        origem = f"despesa_ceap:{d.chave}"
        if cnpj in empresa:
            res.links.append(EntityLink(origem, f"empresa:{cnpj}", "cnpj", 1.0))
        res.links += [EntityLink(origem, f"sancao:{s.chave}", "cnpj", 1.0)
                      for s in sancoes_do.get(cnpj, [])]
    return res
