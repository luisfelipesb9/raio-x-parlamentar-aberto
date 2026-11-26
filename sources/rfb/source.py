"""RFB — cadastro de CNPJ e quadro societário (QSA) via BrasilAPI. Sem autenticação.

GET https://brasilapi.com.br/api/cnpj/v1/{cnpj}: uma consulta por CNPJ, SOMENTE para a lista
recebida em `fetch(cnpjs=...)`. A base completa da Receita (~17 GB) não é baixada. A BrasilAPI é um
serviço público de terceiros que repassa dados da Receita: respeite o limite de requisições
(`pausa` entre consultas; 429 e erros 5xx são retentados com espera).

LGPD: o CPF dos sócios já vem mascarado pela Receita ("***550179**": só os 6 dígitos do meio) e é
preservado assim; sócio PJ traz o CNPJ inteiro.
"""
from __future__ import annotations

import logging
import re
import time
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Any

import httpx

from contracts import Fact
from sources.base import Source

BASE = "https://brasilapi.com.br/api/cnpj/v1"
FONTE = "brasilapi_cnpj"
_TIPO_SOCIO = {1: "PJ", 2: "PF", 3: "estrangeiro"}  # identificador_de_socio
_ESPERA_MAX = 60.0
_log = logging.getLogger(__name__)


def _digitos(texto: Any) -> str:
    return re.sub(r"\D", "", str(texto or ""))


def _cnpj_valido(cnpj: str) -> bool:
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False
    for n in (12, 13):
        pesos = [*range(n - 7, 1, -1), *range(9, 1, -1)][:n]
        resto = sum(int(d) * p for d, p in zip(cnpj[:n], pesos, strict=True)) % 11
        if int(cnpj[n]) != (0 if resto < 2 else 11 - resto):
            return False
    return True


def _nome_norm(nome: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", nome) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().upper()


def _documento_socio(texto: Any) -> str | None:
    """CPF mascarado ('***550179**') ou CNPJ de 14 dígitos; qualquer outra coisa vira None."""
    s = re.sub(r"[.\-/\s]", "", str(texto or ""))
    if re.fullmatch(r"[\d*]{11}", s) and s.strip("*"):
        return s
    return s if re.fullmatch(r"\d{14}", s) else None


class RfbSource(Source):
    nome = "rfb"
    fontes_fato = (FONTE,)

    def __init__(self, client: httpx.Client | None = None, pausa: float = 0.5,
                 max_tentativas: int = 5, espera_base: float = 2.0,
                 dormir: Callable[[float], None] = time.sleep,
                 max_indisponiveis_seguidos: int = 3):
        self.client = client or httpx.Client(timeout=30, headers={"Accept": "application/json"})
        self.pausa, self.max_tentativas, self.espera_base = pausa, max_tentativas, espera_base
        self._dormir = dormir
        self.max_indisponiveis_seguidos = max_indisponiveis_seguidos

    # ---------- fetch ----------

    def _espera(self, r: httpx.Response | None, tentativa: int) -> float:
        retry_after = r.headers.get("retry-after", "") if r is not None else ""
        if re.fullmatch(r"\d+(\.\d+)?", retry_after.strip()):
            return min(float(retry_after), _ESPERA_MAX)
        return min(self.espera_base * 2 ** (tentativa - 1), _ESPERA_MAX)

    def _consultar(self, cnpj: str) -> dict | None:
        """Dados do CNPJ, ou None se a Receita não o conhece (404). 429/5xx/timeout: retenta."""
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                r = self.client.get(f"{BASE}/{cnpj}", follow_redirects=True)
            except httpx.TransportError:
                if tentativa == self.max_tentativas:
                    raise
                self._dormir(self._espera(None, tentativa))
                continue
            if r.status_code == 404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                if tentativa == self.max_tentativas:
                    r.raise_for_status()
                self._dormir(self._espera(r, tentativa))
                continue
            r.raise_for_status()
            return r.json()
        raise AssertionError("inalcançável")  # pragma: no cover

    def fetch(self, cnpjs: Iterable[str]) -> dict:
        """Consulta cada CNPJ (14 dígitos, com ou sem máscara) uma vez; guarda cada resposta em
        data/raw/rfb/<cnpj>.json. Devolve {"cnpjs": [respostas], "nao_encontrados": [cnpj], "invalidos": [texto recebido],
        "indisponiveis": [cnpj]}. CNPJ inválido é só registrado em "invalidos" e o resto do lote segue.
        CNPJ que continua com erro 5xx/timeout depois de todas as tentativas vai para "indisponiveis"
        (a empresa fica sem dados da Receita; nada é inventado) e o lote segue. Com
        `max_indisponiveis_seguidos` falhas seguidas, levanta RuntimeError: é queda do serviço ou da
        rede, e terminar "com sucesso" geraria uma base sem empresas. 429 persistente e erros 4xx
        continuam abortando: indicam limite de uso ou requisição errada, não falha pontual."""
        lista: dict[str, None] = {}
        invalidos: list[str] = []
        for c in cnpjs:  # inválido (formato ou DV) não gasta requisição nem aborta o lote
            d = _digitos(c)
            if _cnpj_valido(d):
                lista[d] = None
            elif str(c) not in invalidos:
                invalidos.append(str(c))
        raw: dict[str, list] = {"cnpjs": [], "nao_encontrados": [], "invalidos": invalidos,
                                "indisponiveis": []}
        seguidos = 0
        for i, cnpj in enumerate(lista):
            if i:
                self._dormir(self.pausa)
            try:
                dados = self._consultar(cnpj)
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500:
                    raise
                seguidos += 1
                if seguidos >= self.max_indisponiveis_seguidos:
                    raise RuntimeError(
                        f"rfb: {seguidos} CNPJs seguidos sem resposta da BrasilAPI; serviço ou "
                        "rede fora do ar. Tente de novo mais tarde.") from e
                _log.warning("rfb: CNPJ %s indisponível na BrasilAPI após %d tentativas; seguindo",
                             cnpj, self.max_tentativas)
                raw["indisponiveis"].append(cnpj)
                continue
            seguidos = 0
            if dados is None:
                raw["nao_encontrados"].append(cnpj)
                continue
            self.save_raw(f"{cnpj}.json", dados)
            raw["cnpjs"].append(dados)
        return raw

    # ---------- normalize ----------

    def normalize(self, raw: dict) -> list[Fact]:
        """`empresa` por CNPJ e `socio` por integrante do QSA. Função pura."""
        facts: list[Fact] = []
        for d in raw.get("cnpjs", []):
            cnpj = _digitos(d.get("cnpj"))
            if len(cnpj) != 14:
                continue
            url = f"{BASE}/{cnpj}"
            cnae = _digitos(d.get("cnae_fiscal"))
            ibge = _digitos(d.get("codigo_municipio_ibge"))
            facts.append(Fact(
                tipo="empresa", chave=cnpj, fonte=FONTE, id_oficial=cnpj, url=url,
                atributos={
                    "razao_social": (d.get("razao_social") or "").strip(),
                    "situacao": d.get("descricao_situacao_cadastral"),
                    "cnae": cnae.zfill(7) if cnae else None,
                    "municipio_ibge": ibge if len(ibge) == 7 else None,
                    "nome_fantasia": (d.get("nome_fantasia") or "").strip() or None,
                    "uf": d.get("uf"), "abertura": d.get("data_inicio_atividade"),
                }))
            vistos: Counter[str] = Counter()
            for s in d.get("qsa") or []:
                nome = re.sub(r"\s+", " ", str(s.get("nome_socio") or "")).strip()
                if not nome:
                    continue
                base = f"{cnpj}:{_nome_norm(nome)}"
                vistos[base] += 1
                facts.append(Fact(
                    tipo="socio", chave=base if vistos[base] == 1 else f"{base}#{vistos[base]}",
                    fonte=FONTE, id_oficial=cnpj, url=url,
                    atributos={
                        "cnpj": cnpj, "nome": nome,
                        "cpf_cnpj": _documento_socio(s.get("cnpj_cpf_do_socio")),
                        "qualificacao": s.get("qualificacao_socio"),
                        "tipo_socio": _TIPO_SOCIO.get(s.get("identificador_de_socio")),
                        "entrada": s.get("data_entrada_sociedade"),
                    }))
        return facts
