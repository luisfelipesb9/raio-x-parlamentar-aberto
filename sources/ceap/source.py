"""CEAP — Cota para o Exercício da Atividade Parlamentar (camara.leg.br/cotas). Sem autenticação.

Arquivo anual oficial: https://www.camara.leg.br/cotas/Ano-{ano}.json.zip
(~9 MB zip / ~250 MB JSON por ano; ~230 mil linhas). Cada linha é um documento de despesa.
"""
from __future__ import annotations

import codecs
import hashlib
import json
import math
import re
import zipfile
from collections import Counter
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import IO, Any

import httpx

from contracts import Fact
from sources.base import Source

URL_ZIP = "https://www.camara.leg.br/cotas/Ano-{ano}.json.zip"
FONTE = "camara_ceap"

# Únicos campos do arquivo que o normalize usa; o resto (CPF do parlamentar, passageiro...) é
# descartado já na leitura, o que também derruba o uso de memória.
CAMPOS_USADOS = frozenset({
    "idDeputado", "idDocumento", "cnpjCPF", "fornecedor", "valorLiquido", "descricao",
    "dataEmissao", "urlDocumento", "ano", "mes", "numero", "parcela", "lote", "trecho"})

_INICIO_DADOS = re.compile(r'"dados"\s*:\s*\[')
_SEPARADORES = " \t\r\n,"

# "000.000.000/0000-1" é o que a Câmara grava quando não há fornecedor (ex.: telefonia funcional).
_PLACEHOLDER = re.compile(r"0+1?|(\d)\1+")


def _digitos(texto: Any) -> str:
    return re.sub(r"\D", "", str(texto or ""))


def _documento_fornecedor(texto: Any) -> dict[str, str]:
    """Devolve {"cnpj": ...} (14 dígitos) ou {"cpf": ...} (11) ou {} se ausente/placeholder."""
    d = _digitos(texto)
    if len(d) not in (11, 14) or _PLACEHOLDER.fullmatch(d):
        return {}
    return {"cnpj" if len(d) == 14 else "cpf": d}


def _id_documento(bruto: Any) -> int:
    """idDocumento como inteiro positivo; qualquer outra coisa (texto, vazio, 0, <0) vira 0."""
    if isinstance(bruto, bool) or not isinstance(bruto, (int, float, str)):
        return 0
    try:
        n = int(str(bruto).strip()) if isinstance(bruto, str) else int(bruto)
    except (ValueError, OverflowError):
        return 0
    return max(0, n)


def _data_iso(texto: Any) -> str | None:
    cand = str(texto or "")[:10]
    try:
        return date.fromisoformat(cand).isoformat()
    except ValueError:
        return None


def _valor(texto: Any) -> float | None:
    try:
        v = float(str(texto).strip())
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def iterar_dados(fluxo: IO[bytes], pedaco: int = 1 << 20, teto: int = 1 << 30) -> Iterator[dict]:
    """Percorre `{"dados": [ {...}, {...} ]}` objeto a objeto, sem carregar o JSON inteiro.

    Lê `pedaco` bytes por vez (UTF-8 incremental, não quebra caractere multibyte) e aborta com
    ValueError se consumir mais de `teto` bytes (defesa contra zip com tamanho declarado falso).
    """
    dec = json.JSONDecoder()
    utf8 = codecs.getincrementaldecoder("utf-8")()
    estado = {"lidos": 0, "fim": False}
    buf = ""

    def mais() -> str:
        b = fluxo.read(pedaco)
        if not b:
            estado["fim"] = True
            return utf8.decode(b"", final=True)
        estado["lidos"] += len(b)
        if estado["lidos"] > teto:
            raise ValueError(f"json descompactado passou do limite de {teto} bytes")
        return utf8.decode(b)

    while not (m := _INICIO_DADOS.search(buf)):
        if estado["fim"]:
            raise ValueError("json sem a lista 'dados'")
        buf += mais()
    pos = m.end()
    while True:
        while pos >= len(buf) or buf[pos] in _SEPARADORES:
            if pos < len(buf):
                pos += 1
                continue
            if estado["fim"]:
                raise ValueError("json incompleto: lista 'dados' não foi fechada")
            buf, pos = "", 0
            buf += mais()
        if buf[pos] == "]":
            return
        try:
            obj, fim = dec.raw_decode(buf, pos)
        except json.JSONDecodeError as e:
            if estado["fim"]:
                raise ValueError(f"json incompleto ou inválido: {e}") from e
            buf, pos = buf[pos:], 0
            buf += mais()
            continue
        yield obj
        pos = fim
        if pos > 1 << 16:
            buf, pos = buf[pos:], 0


class CeapSource(Source):
    nome = "ceap"

    def __init__(self, client: httpx.Client | None = None, tamanho_pedaco: int = 1 << 20,
                 max_descompactado: int = 1 << 30):
        """`max_descompactado`: teto em bytes do JSON dentro do zip (o de 2024 tem ~250 MB)."""
        self.client = client or httpx.Client(timeout=120, follow_redirects=True)
        self.tamanho_pedaco = tamanho_pedaco
        self.max_descompactado = max_descompactado

    # ---------- fetch ----------

    def _baixar(self, url: str, destino: Path) -> None:
        parcial = destino.with_name(destino.name + ".part")
        try:
            with self.client.stream("GET", url) as r:
                r.raise_for_status()
                with parcial.open("wb") as f:
                    for pedaco in r.iter_bytes():
                        f.write(pedaco)
            parcial.replace(destino)
        finally:
            parcial.unlink(missing_ok=True)

    def fetch(self, ano: int, max_linhas: int | None = None,
              max_deputados: int | None = None) -> dict:
        """Baixa o zip do ano (guardado intacto em data/raw/ceap/) e devolve {"ano", "dados"}.

        O JSON é lido em streaming e cada linha é reduzida a `CAMPOS_USADOS`, então o ano
        completo cabe em memória sem o pico de ~1,5 GB do `json.load`.
        `max_linhas` / `max_deputados` geram amostra: só contam linhas de deputado (as de
        lideranças, sem `idDeputado`, são descartadas quando algum limite é usado) e
        `max_linhas` interrompe a leitura assim que for atingido.
        """
        destino = self.raw_path(f"Ano-{ano}.json.zip")
        self._baixar(URL_ZIP.format(ano=ano), destino)
        amostra = max_linhas is not None or max_deputados is not None
        deputados: set = set()
        dados: list[dict] = []
        with zipfile.ZipFile(destino) as z:
            membro = next((i for i in z.infolist() if i.filename.lower().endswith(".json")), None)
            if membro is None:
                raise ValueError(f"{destino.name}: zip sem arquivo json ({z.namelist()})")
            if membro.file_size > self.max_descompactado:
                raise ValueError(f"{membro.filename}: {membro.file_size} bytes passa do "
                                 f"limite de {self.max_descompactado}")
            with z.open(membro) as f:
                for r in iterar_dados(f, self.tamanho_pedaco, self.max_descompactado):
                    linha = {k: v for k, v in r.items() if k in CAMPOS_USADOS}
                    dep = linha.get("idDeputado")
                    if amostra:
                        if not dep:
                            continue
                        if max_deputados is not None and dep not in deputados:
                            if len(deputados) >= max_deputados:
                                continue
                            deputados.add(dep)
                    dados.append(linha)
                    if max_linhas is not None and len(dados) >= max_linhas:
                        break
        return {"ano": ano, "dados": dados}

    # ---------- normalize ----------

    def normalize(self, raw: dict) -> list[Fact]:
        """Uma `despesa_ceap` por documento. Pura (testável com fixture).

        - Linhas sem `idDeputado` (lideranças) e sem `valorLiquido` numérico são descartadas.
        - `chave` = `<idDocumento>:<hash10>` (ou `sem-doc:<hash10>` quando o id é 0), com o hash
          sobre o conteúdo da linha. Depende só da linha, nunca do lote: amostra e ano completo
          geram a mesma chave. O id sozinho não serve: 9 mil ids se repetem (créditos/ajustes do
          mesmo bilhete) e 9,8 mil linhas de telefonia vêm com id 0. Linhas 100% idênticas
          ganham sufixo `-2`, `-3`... pela ordem em que aparecem.
        """
        usadas: Counter[str] = Counter()
        facts: list[Fact] = []
        for r in raw.get("dados", []):
            if not r.get("idDeputado"):
                continue
            valor = _valor(r.get("valorLiquido"))
            if valor is None:
                continue
            doc = _id_documento(r.get("idDocumento"))
            forn = _documento_fornecedor(r.get("cnpjCPF"))
            chave = self._chave(r, doc, forn, usadas)
            ano = r.get("ano")
            url = r.get("urlDocumento") or (URL_ZIP.format(ano=ano) if ano else None)
            facts.append(Fact(
                tipo="despesa_ceap", chave=chave, fonte=FONTE,
                id_oficial=str(doc) if doc else chave, url=url,
                atributos={"deputado_id": str(r["idDeputado"]), **forn,
                           "fornecedor": (r.get("fornecedor") or "").strip(), "valor": valor,
                           "categoria": (r.get("descricao") or "").strip(),
                           "data": _data_iso(r.get("dataEmissao"))}))
        return facts

    @staticmethod
    def _chave(r: dict, doc: int, forn: dict[str, str], usadas: Counter[str]) -> str:
        campos = [r.get("idDeputado"), r.get("ano"), r.get("mes"), r.get("numero"),
                  r.get("parcela"), r.get("lote"), r.get("valorLiquido"), r.get("fornecedor"),
                  r.get("descricao"), r.get("dataEmissao"), r.get("trecho"), *forn.values()]
        bruto = r.get("idDocumento")
        if not doc and str(bruto or "").strip() not in ("", "0"):
            campos.append(f"id:{bruto}")  # id não numérico também distingue a linha
        h = hashlib.sha1("|".join(str(c) for c in campos).encode("utf-8")).hexdigest()[:10]
        chave = f"{doc or 'sem-doc'}:{h}"
        usadas[chave] += 1
        return chave if usadas[chave] == 1 else f"{chave}-{usadas[chave]}"
