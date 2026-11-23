"""Exporta o JSON Schema dos contratos e das respostas da API para o web gerar tipos TS.

Uso: uv run python -m scripts.export_schemas [--out web/src/types/schemas]
Gera um <Nome>.json por modelo (self-contained, com $defs) + index.json (versão do contrato).
Modo "serialização" e todos os campos obrigatórios — é exatamente o que a API devolve.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

import api.schemas as api_schemas
import contracts
from contracts import CONTRACT_VERSION
from graph import Afinidade, Backlink

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_PADRAO = RAIZ / "web" / "src" / "types" / "schemas"


def _modelos() -> dict[str, type]:
    """Contratos + modelos de resposta da API (os que a API de fato devolve)."""
    out: dict[str, type] = {n: getattr(contracts, n) for n in contracts.__all__
                            if n != "CONTRACT_VERSION"}
    out.update({"Afinidade": Afinidade, "Backlink": Backlink})
    for nome, obj in vars(api_schemas).items():
        if (isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel
                and obj.__module__ == api_schemas.__name__):
            out[nome] = obj
    return dict(sorted(out.items()))


def _tudo_obrigatorio(schema: dict) -> dict:
    """A API serializa todos os campos (defaults inclusos): o TS não deve gerar `campo?`."""
    for obj in [schema, *schema.get("$defs", {}).values()]:
        if obj.get("type") == "object" and "properties" in obj:
            obj["required"] = list(obj["properties"])
    return schema


def export(destino: Path = SAIDA_PADRAO) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    escritos: list[Path] = []
    nomes: list[str] = []
    for nome, modelo in _modelos().items():
        schema = _tudo_obrigatorio(TypeAdapter(modelo).json_schema(mode="serialization"))
        schema.setdefault("title", nome)
        arq = destino / f"{nome}.json"
        arq.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        escritos.append(arq)
        nomes.append(nome)
    manifesto = destino / "index.json"
    manifesto.write_text(json.dumps({"contract_version": CONTRACT_VERSION, "schemas": nomes},
                                    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    escritos.append(manifesto)
    return escritos


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=SAIDA_PADRAO)
    args = ap.parse_args()
    arquivos = export(args.out)
    print(f"{len(arquivos) - 1} schemas (contrato {CONTRACT_VERSION}) em {args.out}")


if __name__ == "__main__":
    main()
