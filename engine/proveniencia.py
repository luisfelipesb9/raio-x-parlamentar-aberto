"""Proveniência das evidências: de quando é o dado e de qual arquivo bruto ele veio (ADR-007).

Função pura: recebe os fatos e, opcionalmente, o hash do bruto por fonte; não lê disco nem rede.
`Evidence.coletado_em` vem do fato de origem. `Evidence.sha256_bruto` só vem quando quem chama
sabe que a fonte do fato tem UM arquivo bruto (ver `sources.manifest.sha_por_fonte_fato`).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC

from contracts import Evidence, Fact

Indice = dict[tuple[str, str], Fact]


def indexar(fatos: Iterable[Fact]) -> Indice:
    """(tipo, id_oficial) -> fato. Se vários fatos repetem o `id_oficial` (a CEAP repete
    `idDocumento` em créditos e ajustes), vale o de `coletado_em` mais antigo, para o resultado
    não depender da ordem em que os fatos chegam."""
    indice: Indice = {}
    for f in fatos:
        atual = indice.get((f.tipo, f.id_oficial))
        if atual is None or f.coletado_em < atual.coletado_em:
            indice[(f.tipo, f.id_oficial)] = f
    return indice


def enriquecer(evidencias: Iterable[Evidence], indice: Indice,
               sha_por_fonte: Mapping[str, str] | None = None) -> list[Evidence]:
    """Cópia das evidências com `coletado_em` e `sha256_bruto` preenchidos quando faltam.
    Valor já preenchido nunca é trocado; evidência sem fato correspondente fica como veio."""
    sha_por_fonte = sha_por_fonte or {}
    saida = []
    for e in evidencias:
        fato = indice.get((e.tipo, e.id_oficial))
        if fato is None:
            saida.append(e)
            continue
        saida.append(e.model_copy(update={
            "coletado_em": e.coletado_em or fato.coletado_em.astimezone(UTC),
            "sha256_bruto": e.sha256_bruto or sha_por_fonte.get(fato.fonte)}))
    return saida
