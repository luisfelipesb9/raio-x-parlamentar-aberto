"""CGU — Portal da Transparência: sanções (CEIS/CNEP) e emendas parlamentares. Sem autenticação.

Só os downloads abertos (a API da CGU exige chave e NÃO é usada):
- https://portaldatransparencia.gov.br/download-de-dados/ceis/{AAAAMMDD}  (zip com 1 CSV, ~3 MB)
- https://portaldatransparencia.gov.br/download-de-dados/cnep/{AAAAMMDD}  (zip com 1 CSV, ~0,2 MB)
- https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO (~47 MB)
O portal responde 302 para o CDN da CGU. CEIS/CNEP são arquivos diários: a data publicada mais
recente é lida na página `download-de-dados/{cadastro}` (um GET com data inexistente dá 403).
CSV: separador ';', aspas duplas, latin-1, fim de linha CRLF, datas dd/mm/aaaa, decimal com vírgula.
"""
from __future__ import annotations

import csv
import io
import math
import re
import unicodedata
import zipfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

from contracts import Fact
from sources.base import Source

BASE = "https://portaldatransparencia.gov.br/download-de-dados"
FONTE_CEIS = "cgu_ceis"
FONTE_CNEP = "cgu_cnep"
FONTE_EMENDAS = "cgu_emendas"

_COLS_SANCAO = ("CÓDIGO DA SANÇÃO", "TIPO DE PESSOA", "CPF OU CNPJ DO SANCIONADO",
                "NOME DO SANCIONADO", "CATEGORIA DA SANÇÃO", "DATA INÍCIO SANÇÃO",
                "DATA FINAL SANÇÃO", "ÓRGÃO SANCIONADOR")
_COLS = {
    "ceis": _COLS_SANCAO,
    "cnep": (*_COLS_SANCAO, "VALOR DA MULTA"),
    "emendas": ("Código da Emenda", "Ano da Emenda", "Tipo de Emenda",
                "Código do Autor da Emenda", "Nome do Autor da Emenda",
                "Código Município IBGE", "Valor Empenhado", "Valor Pago"),
}
_PAGINA_DATA = re.compile(r'"ano"\s*:\s*"(\d{4})"\s*,\s*"mes"\s*:\s*"(\d{1,2})"\s*,'
                          r'\s*"dia"\s*:\s*"(\d{1,2})"')
_SEM_INFO = "sem informacao"


def _sem_acento(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in s if not unicodedata.combining(c))


def _data_iso(texto: Any) -> str | None:
    try:
        return datetime.strptime(str(texto or "").strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _valor(texto: Any) -> float | None:
    s = str(texto if texto is not None else "").strip()
    if not s:
        return None
    if "," in s:  # "1.234,56" → 1234.56
        s = s.replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _limpo(texto: Any) -> str | None:
    s = str(texto or "").strip()
    return None if not s or _sem_acento(s).lower() == _SEM_INFO else s


def _incompleta(row: dict, colunas: tuple[str, ...]) -> bool:
    """csv.DictReader preenche com None as colunas que faltam numa linha truncada."""
    return any(row.get(c) is None for c in colunas)


class CguSource(Source):
    nome = "cgu"
    fontes_fato = (FONTE_CEIS, FONTE_CNEP, FONTE_EMENDAS)

    def __init__(self, client: httpx.Client | None = None,
                 max_bytes_descomprimido: int = 1 << 30):
        self.client = client or httpx.Client(timeout=120, follow_redirects=True)
        self.max_bytes_descomprimido = max_bytes_descomprimido  # proteção contra zip bomba

    # ---------- fetch ----------

    def _baixar(self, url: str, destino: Path) -> None:
        parcial = destino.with_name(destino.name + ".part")
        try:
            with self.client.stream("GET", url, follow_redirects=True) as r:
                r.raise_for_status()
                with parcial.open("wb") as f:
                    for pedaco in r.iter_bytes():
                        f.write(pedaco)
            parcial.replace(destino)
        finally:
            parcial.unlink(missing_ok=True)

    def _data_mais_recente(self, cadastro: str) -> date:
        r = self.client.get(f"{BASE}/{cadastro}", follow_redirects=True)
        r.raise_for_status()
        datas = [date(int(a), int(m), int(d)) for a, m, d in _PAGINA_DATA.findall(r.text)]
        if not datas:
            raise ValueError(f"{cadastro}: página do portal sem data de arquivo publicada")
        return max(datas)

    def _ler_csv(self, caminho: Path, cadastro: str) -> list[dict]:
        colunas = _COLS[cadastro]
        with zipfile.ZipFile(caminho) as z:
            csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
            membro = ("EmendasParlamentares.csv" if cadastro == "emendas"
                      else next(iter(csvs), None))
            if membro not in csvs:
                raise ValueError(f"{caminho.name}: zip sem o csv esperado ({z.namelist()})")
            tamanho = z.getinfo(membro).file_size
            if tamanho > self.max_bytes_descomprimido:
                raise ValueError(f"{caminho.name}: {membro} ficaria com {tamanho} bytes "
                                 f"descompactado (limite {self.max_bytes_descomprimido})")
            with z.open(membro) as bruto, io.TextIOWrapper(bruto, encoding="latin-1",
                                                           newline="") as f:
                leitor = csv.DictReader(f, delimiter=";")
                faltam = [c for c in colunas if c not in (leitor.fieldnames or [])]
                if faltam:
                    raise ValueError(f"{caminho.name}: colunas ausentes no cabeçalho: {faltam}")
                return [{c: r.get(c) for c in colunas} for r in leitor]

    def fetch(self, cadastros: tuple[str, ...] = ("ceis", "cnep", "emendas")) -> dict:
        """Baixa os zips (guardados intactos em data/raw/cgu/) e devolve as linhas por cadastro.

        Devolve {"ceis": [...], "cnep": [...], "emendas": [...], "data_ceis": "AAAA-MM-DD", ...}.
        Cada linha é um dict com os nomes ORIGINAIS de coluna (só as que `normalize` usa).
        """
        invalidos = [c for c in cadastros if c not in _COLS]
        if invalidos:
            raise ValueError(f"cadastro desconhecido: {invalidos} (use {sorted(_COLS)})")
        raw: dict[str, Any] = {}
        for cad in cadastros:
            if cad == "emendas":
                url, arquivo = f"{BASE}/emendas-parlamentares/UNICO", "EmendasParlamentares.zip"
            else:
                dia = self._data_mais_recente(cad)
                url = f"{BASE}/{cad}/{dia:%Y%m%d}"
                arquivo = f"{dia:%Y%m%d}_{cad.upper()}.zip"
                raw[f"data_{cad}"] = dia.isoformat()
            destino = self.raw_path(arquivo)
            self._baixar(url, destino)
            self.registrar_raw(destino.name)
            raw[cad] =self._ler_csv(destino, cad)
        return raw

    # ---------- normalize ----------

    def normalize(self, raw: dict) -> list[Fact]:
        """Funções puras. `sancao` por linha de CEIS/CNEP; `emenda` por (código, município)."""
        facts: list[Fact] = []
        for cad, fonte in (("ceis", FONTE_CEIS), ("cnep", FONTE_CNEP)):
            facts += [f for r in raw.get(cad, []) if (f := self._sancao(r, cad, fonte))]
        facts += self._emendas(raw.get("emendas", []))
        return facts

    @staticmethod
    def _sancao(r: dict, cad: str, fonte: str) -> Fact | None:
        if _incompleta(r, _COLS[cad]):
            return None
        codigo = r["CÓDIGO DA SANÇÃO"].strip()
        if not codigo:
            return None
        doc = re.sub(r"\D", "", r["CPF OU CNPJ DO SANCIONADO"])
        multa = _valor(r.get("VALOR DA MULTA")) if cad == "cnep" else None
        return Fact(
            tipo="sancao", chave=f"{cad.upper()}:{codigo}", fonte=fonte, id_oficial=codigo,
            url=f"{BASE}/{cad}",
            atributos={
                "cnpj": doc if len(doc) == 14 else None,
                "cpf": doc if len(doc) == 11 else None,
                "cadastro": cad.upper(),
                "inicio": _data_iso(r["DATA INÍCIO SANÇÃO"]),
                "fim": _data_iso(r["DATA FINAL SANÇÃO"]),
                "orgao": _limpo(r["ÓRGÃO SANCIONADOR"]),
                "nome": _limpo(r["NOME DO SANCIONADO"]),
                "tipo_pessoa": r["TIPO DE PESSOA"].strip().upper() or None,
                "categoria": _limpo(r["CATEGORIA DA SANÇÃO"]),
                "valor_multa": multa,
            })

    @staticmethod
    def _tipo_emenda(texto: str) -> str:
        t = _sem_acento(texto).lower()
        if "transferencias especiais" in t:
            return "pix"
        for chave in ("relator", "bancada", "comissao", "individual"):
            if chave in t:
                return chave
        return "outro"

    def _emendas(self, linhas: list[dict]) -> list[Fact]:
        """Uma `emenda` por (código, município): linhas repetidas (outra ação/função do mesmo
        código e município) somam valores. Linhas sem código oficial ("Sem informação") ficam
        de fora — não há id para rastrear nem autor para atribuir.
        """
        grupos: dict[tuple[str, str | None], dict] = {}
        for r in linhas:
            if _incompleta(r, _COLS["emendas"]):
                continue
            codigo = _limpo(r["Código da Emenda"])
            empenhado, pago = _valor(r["Valor Empenhado"]), _valor(r["Valor Pago"])
            if codigo is None or empenhado is None or pago is None:
                continue
            ibge = r["Código Município IBGE"].strip()
            ibge = ibge if re.fullmatch(r"\d{7}", ibge) else None
            g = grupos.get((codigo, ibge))
            if g:
                g["valor_empenhado"] += empenhado
                g["valor_pago"] += pago
                continue
            ano = r["Ano da Emenda"].strip()
            grupos[(codigo, ibge)] = {
                "autor_nome": _limpo(r["Nome do Autor da Emenda"]),
                "autor_codigo": _limpo(r["Código do Autor da Emenda"]),
                "ano": int(ano) if ano.isdigit() else None,
                "valor_empenhado": empenhado, "valor_pago": pago, "municipio_ibge": ibge,
                "tipo": self._tipo_emenda(r["Tipo de Emenda"]),
                "tipo_emenda": r["Tipo de Emenda"].strip(),
            }
        por_codigo = Counter(codigo for codigo, _ in grupos)
        return [
            Fact(tipo="emenda",
                 chave=codigo if por_codigo[codigo] == 1 else f"{codigo}:{ibge or 'ND'}",
                 fonte=FONTE_EMENDAS, id_oficial=codigo,
                 url=f"{BASE}/emendas-parlamentares", atributos=a)
            for (codigo, ibge), a in grupos.items()
        ]
