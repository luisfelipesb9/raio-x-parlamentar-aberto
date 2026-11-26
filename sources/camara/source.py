"""Câmara dos Deputados — API v2 (dadosabertos.camara.leg.br/api/v2). Sem autenticação."""
from __future__ import annotations

import re
import time
from collections.abc import Iterable
from datetime import date
from typing import Any

import httpx

from contracts import Fact
from sources.base import Source

BASE = "https://dadosabertos.camara.leg.br/api/v2"
FONTE = "camara_api_v2"

_RE_DEPUTADO_URI = re.compile(r"/deputados/(\d+)$")


def _deputado_id(uri: Any) -> str | None:
    """Id do deputado a partir de uma URI da API (`.../deputados/{id}`); None se for outra coisa."""
    m = _RE_DEPUTADO_URI.search(str(uri or ""))
    return m.group(1) if m else None


def _data_iso(texto: Any) -> str | None:
    try:
        return date.fromisoformat(str(texto or "")[:10]).isoformat()
    except ValueError:
        return None


class CamaraSource(Source):
    nome = "camara"
    fontes_fato = (FONTE,)

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
              data_fim: str = "2025-03-31", max_votacoes: int | None = None,
              incluir_proposicoes: bool = False, siglas_tipo: Iterable[str] | None = None,
              max_proposicoes: int | None = None,
              detalhar_deputados: bool | Iterable[str | int] = False) -> dict:
        """`detalhar_deputados`: True = GET /deputados/{id} de todos os deputados baixados;
        uma lista de ids = só os que estiverem nela e no escopo. Acrescenta `cpf` e `nome_civil`
        ao fato `deputado` (1 chamada por deputado, com `pausa`). Opt-in."""
        deputados = self._get_all("/deputados", idLegislatura=legislatura)
        erros_det = self._detalhar_deputados(deputados, detalhar_deputados)
        votacoes = self._get_all("/votacoes", dataInicio=data_inicio, dataFim=data_fim,
                                 ordem="ASC", ordenarPor="dataHoraRegistro")
        votacoes = [v for v in votacoes if v.get("siglaOrgao") == "PLEN"][:max_votacoes]
        for v in votacoes:
            v["_votos"] = self._get_all(f"/votacoes/{v['id']}/votos", paginar=False)
            v["_orientacoes"] = self._get_all(f"/votacoes/{v['id']}/orientacoes",
                                             paginar=False)
        raw = {"deputados": deputados, "votacoes": votacoes}
        if erros_det:
            raw["deputados_erros"] = erros_det
        if incluir_proposicoes:  # opt-in: 2 chamadas por proposição + listagem
            prop = self._coletar_proposicoes(data_inicio, data_fim,
                                             [str(d["id"]) for d in deputados],
                                             siglas_tipo, max_proposicoes)
            raw["proposicoes"] = prop["proposicoes"]
            if prop["erros"]:
                raw["proposicoes_erros"] = prop["erros"]
        self.save_raw(f"camara_{data_inicio}_{data_fim}.json", raw)
        return raw

    def _detalhar_deputados(self, deputados: list[dict],
                            quais: bool | Iterable[str | int]) -> list[dict]:
        """Anexa `_detalhe` {cpf, nomeCivil} a cada deputado pedido. Devolve os erros HTTP."""
        if quais is False:
            return []
        ids = None if quais is True else {str(i) for i in quais}
        erros: list[dict] = []
        vistos: dict[Any, dict] = {}  # a listagem repete deputados: 1 chamada por id
        for d in deputados:
            if ids is not None and str(d["id"]) not in ids:
                continue
            if d["id"] not in vistos:
                try:
                    r = self.client.get(f"{BASE}/deputados/{d['id']}")
                    r.raise_for_status()
                    dados = r.json().get("dados", {})
                except httpx.HTTPError as e:  # sem detalhe: segue sem cpf/nome_civil
                    erros.append({"id": d["id"], "erro": str(e)})
                    vistos[d["id"]] = {}
                else:
                    vistos[d["id"]] = {"cpf": dados.get("cpf"),
                                       "nomeCivil": dados.get("nomeCivil")}
                time.sleep(self.pausa)
            if vistos[d["id"]]:
                d["_detalhe"] = vistos[d["id"]]
        return erros

    # ---------- proposições (proposicao + autoria) ----------

    def fetch_proposicoes(self, data_inicio: str, data_fim: str,
                          deputado_ids: Iterable[str | int] | None = None,
                          siglas_tipo: Iterable[str] | None = None,
                          max_proposicoes: int | None = None) -> dict:
        """Proposições apresentadas em [data_inicio, data_fim] + autores + relatores.

        Com `deputado_ids`: só proposições em que algum deles consta como autor
        (`idDeputadoAutor`) — logo a relatoria só aparece em proposição de autoria de um dos
        ids. Sem `deputado_ids`: toda a janela (cobre relatoria de proposição alheia, mas só
        das apresentadas na janela). Custo: 2 chamadas por proposição (autores, tramitações).
        Devolve {"proposicoes": [...], "erros": [...]} e grava o bruto em data/raw/camara/.
        """
        out = self._coletar_proposicoes(data_inicio, data_fim, deputado_ids, siglas_tipo,
                                        max_proposicoes)
        self.save_raw(f"camara_proposicoes_{data_inicio}_{data_fim}.json", out)
        return out

    def _coletar_proposicoes(self, data_inicio: str, data_fim: str,
                             deputado_ids: Iterable[str | int] | None,
                             siglas_tipo: Iterable[str] | None,
                             max_proposicoes: int | None) -> dict:
        params: dict[str, Any] = {"dataApresentacaoInicio": data_inicio,
                                  "dataApresentacaoFim": data_fim,
                                  "ordem": "ASC", "ordenarPor": "id"}
        if siglas_tipo:
            params["siglaTipo"] = list(siglas_tipo)
        consultas = ([{}] if deputado_ids is None
                     else [{"idDeputadoAutor": str(i)} for i in deputado_ids])
        achadas: dict[int, dict] = {}
        for extra in consultas:
            for p in self._get_all("/proposicoes", **params, **extra):
                achadas.setdefault(p["id"], p)
            if max_proposicoes is not None and len(achadas) >= max_proposicoes:
                break
        lista = [achadas[i] for i in sorted(achadas)][:max_proposicoes]

        proposicoes: list[dict] = []
        erros: list[dict] = []
        for p in lista:
            try:
                autores = self._get_all(f"/proposicoes/{p['id']}/autores", paginar=False)
                tramitacoes = self._get_all(f"/proposicoes/{p['id']}/tramitacoes", paginar=False)
            except httpx.HTTPError as e:  # proposição com dado parcial não entra: vai p/ erros
                erros.append({"id": p["id"], "erro": str(e)})
                continue
            relatores = [{"sequencia": t.get("sequencia"), "siglaOrgao": t.get("siglaOrgao"),
                          "uriUltimoRelator": t["uriUltimoRelator"]}
                         for t in tramitacoes if t.get("uriUltimoRelator")]
            proposicoes.append({**p, "_autores": autores, "_relatores": relatores})
        return {"proposicoes": proposicoes, "erros": erros}

    def _normalize_proposicao(self, p: dict) -> list[Fact]:
        pid, url = str(p["id"]), p.get("uri")

        def fato(tipo: str, chave: str, **atributos: Any) -> Fact:
            return Fact(tipo=tipo, chave=chave, fonte=FONTE, id_oficial=pid, url=url,
                        atributos=atributos)

        facts = [fato("proposicao", pid, sigla_tipo=p.get("siglaTipo"), numero=p.get("numero"),
                      ano=p.get("ano"), ementa=p.get("ementa"),
                      data=_data_iso(p.get("dataApresentacao")))]
        autorias: dict[str, Fact] = {}

        def autoria(dep: str, papel: str, **extra: Any) -> None:
            chave = f"{pid}:{dep}:{papel}"
            autorias.setdefault(chave, fato("autoria", chave, proposicao_id=pid,
                                            deputado_id=dep, papel=papel, **extra))

        # proponente=1 são os autores de fato; proponente=0 são apoiadores de assinatura
        # (ex.: 167 de 171 signatários de uma PEC) e não contam como coautoria.
        for a in p.get("_autores", []):
            dep = _deputado_id(a.get("uri"))
            if dep and a.get("proponente") == 1:
                autoria(dep, "autor" if a.get("ordemAssinatura") == 1 else "coautor")
        # `uriUltimoRelator` persiste nas tramitações seguintes; o órgão certo é o da 1ª aparição
        for t in sorted(p.get("_relatores", []), key=lambda t: t.get("sequencia") or 0):
            dep = _deputado_id(t.get("uriUltimoRelator"))
            if dep:
                autoria(dep, "relator", orgao=t.get("siglaOrgao"))
        return facts + list(autorias.values())

    def normalize(self, raw: dict) -> list[Fact]:
        facts: list[Fact] = []
        for d in raw.get("deputados", []):
            atributos = {"nome": d.get("nome"), "partido": d.get("siglaPartido"),
                         "uf": d.get("siglaUf"), "foto": d.get("urlFoto")}
            det = d.get("_detalhe") or {}
            cpf = re.sub(r"\D", "", str(det.get("cpf") or ""))
            if len(cpf) == 11:
                atributos["cpf"] = cpf
            if (nome_civil := str(det.get("nomeCivil") or "").strip()):
                atributos["nome_civil"] = nome_civil
            facts.append(Fact(tipo="deputado", chave=str(d["id"]), fonte=FONTE,
                              id_oficial=str(d["id"]), url=d.get("uri"), atributos=atributos))
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
        for p in raw.get("proposicoes", []):
            facts += self._normalize_proposicao(p)
        return facts
