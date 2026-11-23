"""emenda (CGU) → deputado (Câmara), pelo nome do autor."""
from __future__ import annotations

from collections import defaultdict

from contracts import Fact
from ingest.resolve.comum import (
    CF_MIN_ENRIQUECER,
    Resolucao,
    deputados_unicos,
    nomes_do_deputado,
    normaliza_nome,
)
from repo.links import Ambiguidade, EntityLink

CF_NOME = 0.8


def resolver_emendas(emendas: list[Fact], deputados: list[Fact]) -> Resolucao:
    """Casa `autor_nome` normalizado com o nome (parlamentar/civil) do deputado.

    A emenda não traz a UF do autor (o município é o destino, não a origem), então a unicidade é
    só por nome: nome de dois deputados → ambíguo, não liga. Nome sem par (bancada, comissão,
    senador, ex-parlamentar) → sem match. Resolve o nome uma vez e vale para todas as emendas dele.
    """
    por_nome: dict[str, set[str]] = defaultdict(set)
    for k, d in deputados_unicos(deputados).items():
        for n in nomes_do_deputado(d):
            por_nome[n].add(k)

    res = Resolucao()
    for e in emendas:
        if e.atributos.get("deputado_id"):
            res.ja_resolvidos += 1
            res.fatos.append(e)
            continue
        achados = por_nome.get(normaliza_nome(e.atributos.get("autor_nome")), set())
        origem = f"emenda:{e.chave}"
        if len(achados) == 1:
            (d,) = achados
            res.links.append(EntityLink(origem, f"deputado:{d}", "nome_norm", CF_NOME))
            if CF_NOME >= CF_MIN_ENRIQUECER:
                e = e.model_copy(update={"atributos": {
                    **e.atributos, "deputado_id": d, "deputado_cf": CF_NOME}})
        elif achados:
            res.ambiguos.append(Ambiguidade(origem, tuple(sorted(f"deputado:{d}" for d in achados)),
                                            "nome do autor casa com mais de um deputado"))
        else:
            res.sem_match.append(origem)
        res.fatos.append(e)
    return res
