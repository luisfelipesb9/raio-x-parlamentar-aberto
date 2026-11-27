"""Varredura de CPF íntegro de terceiros no banco (confirma que a pseudonimização valeu).

Só considera CPF com dígitos verificadores válidos (número qualquer de 11 dígitos, como um id,
não conta). Permitido: `cpf` de deputado e candidato (dado cadastral público, ADR-002).
NUNCA devolve nem imprime o valor encontrado, só onde está.

Uso: python -m ingest.varredura --db data/sample/raio_x_publico.duckdb   (sai com 1 se achar)
"""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Iterator
from typing import Any, NamedTuple

from contracts import Fact
from ingest.pseudonimizar import ATRIBUTOS_ID_PUBLICO, CPF_EM_TEXTO, TOKEN_HASH, dv_ok

PERMITIDOS = {("deputado", "cpf"), ("candidatura", "cpf"),
              # a chave da candidatura é o SQ_CANDIDATO (id público do TSE, 11 dígitos), e a de
              # `votos_municipio` o embute: coincidem com DV de CPF em ~1% dos casos e não são CPF
              ("candidatura", "chave"), ("candidatura", "id_oficial"),
              ("votos_municipio", "chave"), ("votos_municipio", "id_oficial")}
# tabelas materializadas por `publicar/` (ADR-011): (tabela, colunas de texto; a 1ª identifica a linha)
TABELAS_MATERIALIZADAS = (("graph_node", ("id", "payload")),
                          ("graph_edge", ("origem", "destino", "rel", "payload")),
                          ("inferencia", ("deputado_id", "regra", "payload")),
                          ("publicacao_meta", ("chave", "valor")))


class Achado(NamedTuple):
    tipo: str
    chave: str
    campo: str


# Derivados (findings, links, grafo) repetem ids públicos e números dos fatos. Duas formas que podem
# fechar como CPF por coincidência (~1%) e não são CPF: o SQ_CANDIDATO (em `candidatura:<SQ>` e no
# `id_oficial` `<SQ>:<município>` de `votos_municipio`), só quando o SQ é de uma `candidatura` que está
# no banco, e o valor em reais cru, com 9 dígitos, ponto e 2 casas (`123456789.12`; CPF com ponto
# traz o ponto entre os grupos de 3).
_REF_SQ = re.compile(r'(candidatura:|"tipo":\s*"votos_municipio",\s*"id_oficial":\s*")(\d{11})(?!\d)')
_VALOR_CRU = re.compile(r"(?<![\d.])\d{9}\.\d{2}(?![\d.])")


def _sem_ids_publicos(texto: str, sqs: frozenset[str] | set[str]) -> str:
    texto = _REF_SQ.sub(lambda m: m.group(1) + ("#" if m.group(2) in sqs else m.group(2)), texto)
    return _VALOR_CRU.sub("#", texto)


def tem_cpf_derivado(texto: str, sqs: frozenset[str] | set[str] = frozenset()) -> bool:
    """`tem_cpf` para findings, links e grafo: ignora SQ de candidatura conhecido e valor cru."""
    return tem_cpf(_sem_ids_publicos(texto, sqs))


def tem_cpf(texto: str) -> bool:
    texto = TOKEN_HASH.sub(" ", texto)  # o hash não é CPF, mesmo que tenha 11 dígitos seguidos
    return any(dv_ok(re.sub(r"\D", "", m.group())) for m in CPF_EM_TEXTO.finditer(texto))


def _textos(valor: Any, caminho: str) -> Iterator[tuple[str, str]]:
    if isinstance(valor, dict):
        for k, v in valor.items():
            yield from _textos(v, f"{caminho}.{k}" if caminho else str(k))
    elif isinstance(valor, list):
        for v in valor:
            yield from _textos(v, caminho)
    elif valor is not None:
        yield caminho, str(valor)


def cpfs_integros(fatos: Iterable[Fact]) -> list[Achado]:
    achados: dict[tuple[str, str, str], None] = {}
    for f in fatos:
        campos = [("chave", f.chave), ("id_oficial", f.id_oficial), ("url", f.url or "")]
        campos += list(_textos(f.atributos, ""))
        for campo, texto in campos:
            if (f.tipo, campo) in PERMITIDOS or campo.rsplit(".", 1)[-1] in ATRIBUTOS_ID_PUBLICO:
                continue
            if tem_cpf(texto):
                achados[(f.tipo, f.chave, campo)] = None
    return [Achado(*k) for k in achados]


def varrer_banco(store: Any) -> list[Achado]:
    """Fatos, findings/explicações (citam valores dos fatos), entity_link, entity_ambiguity e as
    tabelas materializadas da publicação (as que existirem)."""
    fatos = store.load_facts()
    achados = cpfs_integros(fatos)
    sqs = {f.chave for f in fatos if f.tipo == "candidatura"}
    for fid, payload, expl in store.con.execute(
            "SELECT id, payload::VARCHAR, explanation::VARCHAR FROM finding").fetchall():
        for campo, texto in (("payload", payload), ("explanation", expl)):
            if tem_cpf_derivado(texto or "", sqs):
                achados.append(Achado("finding", fid, campo))
    ausentes = set(store.tabelas_publicacao_faltando())
    for tabela, colunas in (("entity_link", ("origem", "destino", "metodo")),
                            ("entity_ambiguity", ("origem", "candidatos", "motivo")),
                            *(t for t in TABELAS_MATERIALIZADAS if t[0] not in ausentes)):
        sel = ", ".join(f"{c}::VARCHAR" for c in colunas)
        for linha in store.con.execute(f"SELECT {sel} FROM {tabela}").fetchall():
            for campo, texto in zip(colunas, linha, strict=True):
                if tem_cpf_derivado(texto or "", sqs):
                    achados.append(Achado(tabela, linha[0], campo))
    return achados


def main(argv: list[str] | None = None) -> None:
    from repo.store import Store
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True)
    a = ap.parse_args(argv)
    achados = varrer_banco(Store(a.db, read_only=True))
    for x in achados[:50]:
        print(f"CPF íntegro em {x.tipo}:{x.chave} campo {x.campo}")
    print(f"{len(achados)} ocorrência(s) de CPF íntegro de terceiro")
    sys.exit(1 if achados else 0)


if __name__ == "__main__":
    main()
