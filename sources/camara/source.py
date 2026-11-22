"""Câmara dos Deputados — API v2 (dadosabertos.camara.leg.br/api/v2). Sem autenticação."""
from __future__ import annotations

import time
from typing import Any

import httpx

from contracts import Fact
from sources.base import Source

BASE = "https://dadosabertos.camara.leg.br/api/v2"
FONTE = "camara_api_v2"


class CamaraSource(Source):
    nome = "camara"

    def __init__(self, client: httpx.Client | None = None, pausa: float = 0.2):
        self.client = client or httpx.Client(timeout=30, headers={"Accept": "application/json"})
        self.pausa = pausa

    def _get_all(self, path: str, paginar: bool = True, **params: Any) -> list[dict]:
        if paginar:
            params = {"itens": 100, **params}
        out, url = [], f"{BASE}{path}"
        while url:
            r = self.client.get(url, params=params)
            r.raise_for_status()
            body = r.json()
            out += body.get("dados", [])
            url = next((link["href"] for link in body.get("links", [])
                        if link.get("rel") == "next"), None)
            params = None  # o link "next" já traz os parâmetros
            time.sleep(self.pausa)
        return out

    def fetch(self, legislatura: int = 57, data_inicio: str = "2025-01-01",
              data_fim: str = "2025-03-31", max_votacoes: int | None = None) -> dict:
        deputados = self._get_all("/deputados", idLegislatura=legislatura)
        votacoes = self._get_all("/votacoes", dataInicio=data_inicio, dataFim=data_fim,
                                 ordem="ASC", ordenarPor="dataHoraRegistro")
        votacoes = [v for v in votacoes if v.get("siglaOrgao") == "PLEN"][:max_votacoes]
        for v in votacoes:
            v["_votos"] = self._get_all(f"/votacoes/{v['id']}/votos", paginar=False)
            v["_orientacoes"] = self._get_all(f"/votacoes/{v['id']}/orientacoes",
                                             paginar=False)
        raw = {"deputados": deputados, "votacoes": votacoes}
        self.save_raw(f"camara_{data_inicio}_{data_fim}.json", raw)
        return raw

    def normalize(self, raw: dict) -> list[Fact]:
        facts: list[Fact] = []
        for d in raw.get("deputados", []):
            facts.append(Fact(tipo="deputado", chave=str(d["id"]), fonte=FONTE,
                              id_oficial=str(d["id"]), url=d.get("uri"),
                              atributos={"nome": d.get("nome"), "partido": d.get("siglaPartido"),
                                         "uf": d.get("siglaUf"), "foto": d.get("urlFoto")}))
        for v in raw.get("votacoes", []):
            votos = v.get("_votos", [])
            gov = next((o.get("orientacaoVoto") for o in v.get("_orientacoes", [])
                        if (o.get("siglaPartidoBloco") or "").lower() == "governo"), None)
            vid = str(v["id"])
            facts.append(Fact(tipo="votacao", chave=vid, fonte=FONTE, id_oficial=vid,
                              url=v.get("uri"),
                              atributos={"data": v.get("data"), "descricao": v.get("descricao"),
                                         "nominal": bool(votos), "orientacao_governo": gov}))
            for vt in votos:
                dep = vt.get("deputado_", {})
                facts.append(Fact(tipo="voto", chave=f"{vid}:{dep.get('id')}", fonte=FONTE,
                                  id_oficial=vid, url=v.get("uri"),
                                  atributos={"votacao_id": vid, "deputado_id": str(dep.get("id")),
                                             "voto": vt.get("tipoVoto")}))
        return facts
