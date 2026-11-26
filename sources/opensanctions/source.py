"""OpenSanctions — dataset `br_pep` (Brazil Politically Exposed Persons, divulgado pela CGU).

LICENÇA: CC BY-NC 4.0 (OpenSanctions) — uso NÃO comercial, com atribuição. Este projeto é
acadêmico; não use estes dados em produto comercial sem licença.

Usamos `targets.nested.json` (JSON Lines, ~150 MB, uma pessoa por linha com as ocupações
aninhadas) e não `targets.simple.csv`: o CSV só tem nome e CPF mascarado; cargo, órgão e datas
(exigidos por docs/fact_types.md) só existem no nested.

ATENÇÃO à qualidade: os cargos (`Position`) são normalizados por IA (`origin: openai:...`) e vêm em
inglês ("Mayor, Guaraciaba-SC"); não são o texto oficial. O CPF vem mascarado (***.976.399-**) e
pessoas homônimas podem ter sido fundidas numa entidade (mais de um CPF).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from contracts import Fact
from sources.base import Source

URL = "https://data.opensanctions.org/datasets/latest/br_pep/targets.nested.json"
URL_ENTIDADE = "https://www.opensanctions.org/entities/{id}/"
FONTE = "opensanctions_br_pep"


def _primeiro(valores: Any) -> Any:
    return valores[0] if isinstance(valores, list) and valores else None


def _data(valores: Any) -> str | None:
    try:
        return date.fromisoformat(str(_primeiro(valores) or "")).isoformat()
    except ValueError:
        return None


def _cpf_mascarado(texto: Any) -> str | None:
    """'***.976.399-**' → '***976399**' (11 caracteres, só dígitos e '*')."""
    s = str(texto or "").replace(".", "").replace("-", "").strip()
    return s if len(s) == 11 and set(s) <= set("*0123456789") and s.strip("*") else None


def _ocupacao(o: dict) -> dict:
    p = o.get("properties", {})
    posicao = next((x.get("caption") for x in p.get("post", []) if x.get("caption")), None)
    cargo, _, orgao = (posicao or "").partition(", ")
    return {"cargo": cargo or None, "orgao": orgao or None, "posicao": posicao,
            "inicio": _data(p.get("startDate")), "fim": _data(p.get("endDate")),
            "status": _primeiro(p.get("status"))}


def _compactar(e: dict) -> dict:
    """Mantém só o que `normalize` lê, no mesmo formato do arquivo original."""
    p = e.get("properties", {})
    return {
        "id": e.get("id"), "caption": e.get("caption"), "schema": e.get("schema"),
        "properties": {
            "name": p.get("name"), "taxNumber": p.get("taxNumber"),
            "positionOccupancies": [
                {"properties": {k: o.get("properties", {}).get(k)
                                for k in ("startDate", "endDate", "status")}
                 | {"post": [{"caption": x.get("caption")}
                             for x in o.get("properties", {}).get("post", [])]}}
                for o in p.get("positionOccupancies", [])
            ],
        },
    }


class OpenSanctionsSource(Source):
    nome = "opensanctions"
    fontes_fato = (FONTE,)

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=300, follow_redirects=True)

    # ---------- fetch ----------

    def _baixar(self, destino: Path) -> None:
        parcial = destino.with_name(destino.name + ".part")
        try:
            with self.client.stream("GET", URL, follow_redirects=True) as r:
                r.raise_for_status()
                with parcial.open("wb") as f:
                    for pedaco in r.iter_bytes():
                        f.write(pedaco)
            parcial.replace(destino)
        finally:
            parcial.unlink(missing_ok=True)

    def fetch(self, max_entidades: int | None = None) -> dict:
        """Baixa o JSON Lines (guardado intacto em data/raw/opensanctions/) e devolve
        {"entities": [...]} só com Pessoas, já compactadas. `max_entidades` gera amostra."""
        destino = self.raw_path("br_pep.targets.nested.json")
        self._baixar(destino)
        self.registrar_raw(destino.name)
        entidades: list[dict] = []
        with destino.open(encoding="utf-8") as f:
            for n, linha in enumerate(f, start=1):
                if not linha.strip():
                    continue
                try:
                    e = json.loads(linha)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{destino.name}: JSON inválido na linha {n}") from exc
                if e.get("schema") == "Person":
                    entidades.append(_compactar(e))
                if max_entidades is not None and len(entidades) >= max_entidades:
                    break
        return {"entities": entidades}

    # ---------- normalize ----------

    def normalize(self, raw: dict) -> list[Fact]:
        """Um `pep` por pessoa. Cargo/órgão/datas vêm da ocupação em exercício (`current`) ou,
        se não houver, da de início mais recente; todas ficam em `ocupacoes`."""
        facts = []
        for e in raw.get("entities", []):
            if not e.get("id") or e.get("schema", "Person") != "Person":
                continue
            p = e.get("properties", {})
            cpfs = [c for t in p.get("taxNumber") or [] if (c := _cpf_mascarado(t))]
            ocupacoes = [_ocupacao(o) for o in p.get("positionOccupancies", [])]
            principal = max(
                ocupacoes, default={},
                key=lambda o: (o["status"] == "current", o["inicio"] or "", o["fim"] or ""))
            facts.append(Fact(
                tipo="pep", chave=e["id"], fonte=FONTE, id_oficial=e["id"],
                url=URL_ENTIDADE.format(id=e["id"]),
                atributos={
                    "nome": e.get("caption") or _primeiro(p.get("name")),
                    "cpf": cpfs[0] if len(cpfs) == 1 else None,
                    "cpfs": cpfs,
                    "cargo": principal.get("cargo"), "orgao": principal.get("orgao"),
                    "inicio": principal.get("inicio"), "fim": principal.get("fim"),
                    "status": principal.get("status"), "ocupacoes": ocupacoes,
                }))
        return facts
