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
from ingest.pseudonimizar import CPF_EM_TEXTO, TOKEN_HASH, dv_ok

PERMITIDOS = {("deputado", "cpf"), ("candidatura", "cpf")}


class Achado(NamedTuple):
    tipo: str
    chave: str
    campo: str


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
            if (f.tipo, campo) in PERMITIDOS:
                continue
            if tem_cpf(texto):
                achados[(f.tipo, f.chave, campo)] = None
    return [Achado(*k) for k in achados]


def varrer_banco(store: Any) -> list[Achado]:
    """Fatos, findings/explicações (citam valores dos fatos), entity_link e entity_ambiguity."""
    achados = cpfs_integros(store.load_facts())
    for fid, payload, expl in store.con.execute(
            "SELECT id, payload::VARCHAR, explanation::VARCHAR FROM finding").fetchall():
        for campo, texto in (("payload", payload), ("explanation", expl)):
            if tem_cpf(texto or ""):
                achados.append(Achado("finding", fid, campo))
    for tabela, colunas in (("entity_link", ("origem", "destino", "metodo")),
                            ("entity_ambiguity", ("origem", "candidatos", "motivo"))):
        sel = ", ".join(f"{c}::VARCHAR" for c in colunas)
        for linha in store.con.execute(f"SELECT {sel} FROM {tabela}").fetchall():
            for campo, texto in zip(colunas, linha, strict=True):
                if tem_cpf(texto or ""):
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
