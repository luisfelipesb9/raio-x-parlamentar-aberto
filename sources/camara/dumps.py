"""Dump anual oficial da Câmara: votações, votos por parlamentar e orientações de bancada.

`https://dadosabertos.camara.leg.br/arquivos/<conjunto>/csv/<conjunto>-<ano>.csv`, atualizado
diariamente (medido em 2026-11-26, ano 2025: votacoes 8,4 MiB, votacoesVotos 55,5 MiB,
votacoesOrientacoes 1,0 MiB). Troca centenas de chamadas por votação por 3 downloads por ano e
contorna o teto de 3 meses da janela da API. CSV UTF-8 com BOM, separador `;`, tudo entre aspas.

O resultado tem o mesmo formato do bruto da API (`_votos`, `_orientacoes`), então o `normalize`
da fonte gera os mesmos `Fact` (`votacao`, `voto`), sem mudar o contrato.

Princípio ético: voto individual só vem de votação NOMINAL de PLENÁRIO. Votação simbólica não
tem linha no arquivo de votos e fica com `_votos == []` (o `normalize` a marca `nominal=False`);
voto de comissão é descartado.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable, Iterator
from datetime import date
from pathlib import Path

BASE_DUMPS = "https://dadosabertos.camara.leg.br/arquivos"
CONJUNTOS = ("votacoes", "votacoesVotos", "votacoesOrientacoes")
ORGAO_PLENARIO = "PLEN"


def url_dump(conjunto: str, ano: int) -> str:
    return f"{BASE_DUMPS}/{conjunto}/csv/{conjunto}-{ano}.csv"


def ler_csv(caminho: Path | str) -> Iterator[dict[str, str]]:
    """Linhas do CSV, uma a uma (o arquivo de votos de um ano passa de 50 MiB: nada de ler tudo)."""
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f, delimiter=";")


def _id_deputado(texto: str) -> int | str:
    return int(texto) if texto.isdigit() else texto


def votacoes_do_dump(arq_votacoes: Iterable[Path | str], arq_votos: Iterable[Path | str],
                     arq_orientacoes: Iterable[Path | str], inicio: str, fim: str,
                     max_votacoes: int | None = None) -> list[dict]:
    """Votações de Plenário em [`inicio`, `fim`] (ISO, inclusivo), em ordem de registro, no
    formato do bruto da API, com `_votos` e `_orientacoes`. `max_votacoes` corta depois de
    ordenar (como o caminho da API) e antes de ler os votos."""
    ini, ate = date.fromisoformat(inicio), date.fromisoformat(fim)
    if ini > ate:
        raise ValueError(f"início ({inicio}) depois do fim ({fim})")

    candidatas: list[dict] = []
    for caminho in arq_votacoes:
        for r in ler_csv(caminho):
            if r["siglaOrgao"] != ORGAO_PLENARIO:
                continue
            try:
                data = date.fromisoformat(r["data"][:10])
            except ValueError:
                continue
            if ini <= data <= ate:
                candidatas.append({"id": r["id"], "uri": r["uri"], "data": r["data"],
                                   "dataHoraRegistro": r["dataHoraRegistro"],
                                   "siglaOrgao": r["siglaOrgao"], "descricao": r["descricao"],
                                   "aprovacao": r["aprovacao"]})
    candidatas.sort(key=lambda v: (v["dataHoraRegistro"], v["id"]))
    votacoes = candidatas[:max_votacoes]
    por_id = {v["id"]: v for v in votacoes}

    votos: dict[str, list[dict]] = defaultdict(list)
    for caminho in arq_votos:
        for r in ler_csv(caminho):
            if r["idVotacao"] in por_id and r["voto"]:
                votos[r["idVotacao"]].append(
                    {"tipoVoto": r["voto"], "deputado_": {"id": _id_deputado(r["deputado_id"])}})
    orientacoes: dict[str, list[dict]] = defaultdict(list)
    for caminho in arq_orientacoes:
        for r in ler_csv(caminho):
            if r["idVotacao"] in por_id:
                orientacoes[r["idVotacao"]].append(
                    {"siglaPartidoBloco": r["siglaBancada"], "orientacaoVoto": r["orientacao"]})
    for v in votacoes:
        v["_votos"] = votos.get(v["id"], [])
        v["_orientacoes"] = orientacoes.get(v["id"], [])
    return votacoes
