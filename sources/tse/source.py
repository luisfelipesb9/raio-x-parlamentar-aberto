"""TSE — Dados Abertos (cdn.tse.jus.br/estatistica/sead/odsele). Sem autenticação. Eleição 2022.

Três zips por eleição, cada um com um CSV por UF (latin-1, ';', tudo entre aspas, vírgula decimal):
- consulta_cand/consulta_cand_2022.zip (~5 MB)                       → `candidatura`
- prestacao_contas/prestacao_de_contas_eleitorais_candidatos_2022.zip (~500 MB) → `doacao`
- votacao_candidato_munzona/votacao_candidato_munzona_2022.zip (~590 MB; MG sozinho = 1 GB de CSV)
  → `votos_municipio`
Os zips grandes NÃO são baixados inteiros: o servidor aceita HTTP Range, então só o diretório
central do zip e o membro da UF pedida (receitas MG ≈ 2 MB; votação MG ≈ 70 MB comprimidos) são
transferidos, em streaming. Só linhas de Deputado Federal são mantidas e os votos por zona são
somados por (candidato, município) já no fetch.

O TSE identifica o município por código próprio (CD_MUNICIPIO), não pelo do IBGE. O código IBGE vem
do casamento (UF, nome normalizado) com a API de localidades do IBGE; 14 nomes divergem entre as
duas bases e estão numa tabela de alias (_ALIAS_IBGE).
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import ExitStack
from datetime import datetime
from typing import Any

import httpx

from contracts import Fact
from sources.base import Source

CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"
URL_IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
FONTE_CANDIDATURA = "tse_consulta_cand"
FONTE_DOACAO = "tse_prestacao_contas"
FONTE_VOTOS = "tse_votacao_munzona"

# conjunto → (url do zip, nome do membro por UF, colunas que o normalize usa)
_CONJUNTOS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "candidatos": (
        f"{CDN}/consulta_cand/consulta_cand_{{ano}}.zip", "consulta_cand_{ano}_{uf}.csv",
        ("ANO_ELEICAO", "SQ_CANDIDATO", "NR_CPF_CANDIDATO", "NM_CANDIDATO", "NM_URNA_CANDIDATO",
         "DS_CARGO", "SG_UF", "SG_PARTIDO", "DS_SIT_TOT_TURNO")),
    "receitas": (
        f"{CDN}/prestacao_contas/prestacao_de_contas_eleitorais_candidatos_{{ano}}.zip",
        "receitas_candidatos_{ano}_{uf}.csv",
        ("AA_ELEICAO", "SQ_CANDIDATO", "DS_CARGO", "SQ_RECEITA", "NM_DOADOR", "NM_DOADOR_RFB",
         "NR_CPF_CNPJ_DOADOR", "DS_ORIGEM_RECEITA", "DT_RECEITA", "VR_RECEITA")),
    "votacao": (
        f"{CDN}/votacao_candidato_munzona/votacao_candidato_munzona_{{ano}}.zip",
        "votacao_candidato_munzona_{ano}_{uf}.csv",
        ("ANO_ELEICAO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "DS_CARGO", "SQ_CANDIDATO",
         "QT_VOTOS_NOMINAIS_VALIDOS")),
}
_CARGO = "deputado federal"
_CHUNK = 1 << 20  # cada GET com Range traz até 1 MiB


def _sem_acento(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm_municipio(nome: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", _sem_acento(nome).upper())


def _eh_deputado_federal(cargo: Any) -> bool:
    return _sem_acento(str(cargo or "")).strip().lower() == _CARGO


def _limpo(texto: Any) -> str | None:
    """Texto sem os marcadores de nulo do TSE ('#NULO', '#NULO#', '#NE')."""
    s = str(texto or "").strip()
    return None if not s or s.startswith("#") else s


def _documento(texto: Any, tamanhos: tuple[int, ...] = (11, 14)) -> str | None:
    d = re.sub(r"\D", "", str(texto or ""))
    return d if len(d) in tamanhos else None


def _data_iso(texto: Any) -> str | None:
    try:
        return datetime.strptime(str(texto or "").strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _valor(texto: Any) -> float | None:
    s = str(texto if texto is not None else "").strip()
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def _inteiro(texto: Any) -> int | None:
    s = str(texto if texto is not None else "").strip()
    return int(s) if re.fullmatch(r"\d+", s) else None


def _ano(texto: Any, padrao: int) -> int:
    return _inteiro(texto) or padrao


# Nomes do TSE que diferem do IBGE (renomeações e grafia). Chave: (UF, nome TSE) → código IBGE.
# "Governador Edison Lobão" (MA) foi pareado por eliminação: é o único município do MA sem par.
_ALIAS_IBGE: dict[tuple[str, str], str] = {
    (uf, _norm_municipio(nome)): ibge for uf, nome, ibge in (
        ("RN", "BOA SAÚDE", "2405306"), ("MG", "DONA EUSÉBIA", "3122900"),
        ("SE", "AMPARO DE SÃO FRANCISCO", "2800100"), ("RR", "SÃO LUIZ", "1400605"),
        ("RO", "ALVORADA DO OESTE", "1100346"), ("MG", "BARÃO DE MONTE ALTO", "3105509"),
        ("SP", "SÃO LUÍS DO PARAITINGA", "3550001"), ("MG", "SÃO THOMÉ DAS LETRAS", "3165206"),
        ("MT", "SANTO ANTÔNIO DO LEVERGER", "5107800"), ("PA", "ELDORADO DOS CARAJÁS", "1502954"),
        ("RO", "ESPIGÃO DO OESTE", "1100098"), ("MA", "GOVERNADOR EDISON LOBÃO", "2104552"),
        ("PA", "SANTA ISABEL DO PARÁ", "1506500"), ("BA", "CAMACÃ", "2905602"),
    )
}


class _RangeFile(io.RawIOBase):
    """Arquivo remoto somente-leitura e "seekable" sobre HTTP Range (para zipfile)."""

    def __init__(self, client: httpx.Client, url: str):
        super().__init__()
        self._client, self._url, self._pos = client, url, 0
        r = client.head(url, follow_redirects=True)
        r.raise_for_status()
        self._size = int(r.headers["content-length"])

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self._size}[whence]
        self._pos = max(0, base + offset)
        return self._pos

    def readinto(self, b: Any) -> int:
        n = min(len(b), self._size - self._pos)
        if n <= 0:
            return 0
        r = self._client.get(self._url, follow_redirects=True,
                             headers={"Range": f"bytes={self._pos}-{self._pos + n - 1}"})
        r.raise_for_status()
        if r.status_code != 206:
            raise RuntimeError(f"{self._url}: o servidor ignorou o cabeçalho Range "
                               f"(status {r.status_code}); não vou baixar o zip inteiro")
        b[:len(r.content)] = r.content
        self._pos += len(r.content)
        return len(r.content)


class TseSource(Source):
    nome = "tse"
    fontes_fato = (FONTE_CANDIDATURA, FONTE_DOACAO, FONTE_VOTOS)

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=120, follow_redirects=True)

    # ---------- fetch ----------

    def _abrir_zip(self, url: str) -> zipfile.ZipFile:
        return zipfile.ZipFile(io.BufferedReader(_RangeFile(self.client, url), _CHUNK))

    @staticmethod
    def _ufs_do_zip(z: zipfile.ZipFile, conjunto: str, ano: int) -> list[str]:
        modelo = _CONJUNTOS[conjunto][1]
        pre, pos = (re.escape(p) for p in modelo.format(ano=ano, uf="\0").split("\0"))
        rx = re.compile(f"^{pre}([A-Z]{{2}}){pos}$")
        siglas = {m.group(1) for n in z.namelist() if (m := rx.match(n))}
        return sorted(siglas - {"BR", "ZZ"})  # BR = presidente, ZZ = exterior

    @staticmethod
    def _linhas(z: zipfile.ZipFile, membro: str, colunas: tuple[str, ...]) -> Iterator[dict]:
        """Linhas de Deputado Federal do CSV, em streaming, só com as colunas pedidas."""
        with z.open(membro) as bruto, io.TextIOWrapper(bruto, encoding="latin-1",
                                                       newline="") as f:
            leitor = csv.reader(f, delimiter=";")
            cab = next(leitor, [])
            faltam = [c for c in colunas if c not in cab]
            if faltam:
                raise ValueError(f"{membro}: colunas ausentes no cabeçalho: {faltam}")
            idx = {c: cab.index(c) for c in colunas}
            ultimo, i_cargo = max(idx.values()), idx["DS_CARGO"]
            for linha in leitor:
                if len(linha) > ultimo and _eh_deputado_federal(linha[i_cargo]):
                    yield {c: linha[i] for c, i in idx.items()}

    def _municipios_ibge(self) -> list[dict]:
        r = self.client.get(URL_IBGE, follow_redirects=True)
        r.raise_for_status()
        out = []
        for m in r.json():
            ufo = (((m.get("microrregiao") or {}).get("mesorregiao") or {}).get("UF")
                   or m["regiao-imediata"]["regiao-intermediaria"]["UF"])
            out.append({"id": m["id"], "nome": m["nome"], "uf": ufo["sigla"]})
        return out

    def _parte_em_disco(self, uf: str, ano: int, conjuntos: tuple[str, ...]) -> dict | None:
        """O bruto já gravado desta UF (data/raw/tse/tse_{ano}_{UF}.json), ou None se ausente,
        ilegível ou incompleto (outro ano/UF, falta algum dos `conjuntos` pedidos ou, havendo
        votação, a lista de municípios): nesse caso a UF é baixada de novo."""
        try:
            parte = json.loads(self.raw_path(f"tse_{ano}_{uf}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(parte, dict) or parte.get("ano") != ano or parte.get("uf") != uf:
            return None
        if any(not isinstance(parte.get(c), list) for c in conjuntos):
            return None
        if "votacao" in conjuntos and not isinstance(parte.get("municipios_ibge"), list):
            return None
        return parte

    def fetch_por_uf(self, uf: str | None = None, ano: int = 2022,
                     conjuntos: tuple[str, ...] = ("candidatos", "receitas", "votacao"),
                     reusar_raw: bool = False) -> Iterator[dict]:
        """Gerador: lê UF por UF e devolve {"ano", "uf", <conjuntos>, "municipios_ibge"} de cada
        uma, já gravado em data/raw/tse/tse_{ano}_{UF}.json. Só uma UF fica em memória por vez;
        é o modo para rodar o país inteiro (normalize cada parte e grave os fatos antes da
        próxima; solte a referência à parte antes de pedir a seguinte). Os zips são lidos por
        HTTP Range, só o membro da UF.

        Com `reusar_raw`, a UF que já tem o bruto completo em disco é devolvida dele, sem ler o
        membro do zip nem consultar o IBGE (retomada de uma rodada interrompida); bruto ausente,
        corrompido ou incompleto é baixado de novo. Sem UF explícita ainda é preciso abrir o
        diretório dos zips (poucos KB por Range) para saber quais UFs existem."""
        if uf is not None and not re.fullmatch(r"[A-Za-z]{2}", uf):
            raise ValueError(f"uf inválida: {uf!r} (esperado sigla de 2 letras, ex.: 'MG')")
        desconhecidos = [c for c in conjuntos if c not in _CONJUNTOS]
        if desconhecidos:
            raise ValueError(f"conjunto desconhecido: {desconhecidos} (use {list(_CONJUNTOS)})")
        uf = uf.upper() if uf else None
        with ExitStack() as pilha:
            zips: dict[str, zipfile.ZipFile] = {}

            def abrir() -> dict[str, zipfile.ZipFile]:
                if not zips:
                    for c in conjuntos:
                        zips[c] = pilha.enter_context(
                            self._abrir_zip(_CONJUNTOS[c][0].format(ano=ano)))
                return zips

            lidos: dict[str, dict | None] = {}  # bruto de disco já lido (lê cada arquivo uma vez)

            def em_disco(sigla: str) -> dict | None:
                if not reusar_raw:
                    return None
                if sigla not in lidos:
                    lidos[sigla] = self._parte_em_disco(sigla, ano, conjuntos)
                return lidos[sigla]

            if uf:
                ufs = [uf]
                if em_disco(uf) is None:
                    for c, z in abrir().items():
                        nome = _CONJUNTOS[c][1].format(ano=ano, uf=uf)
                        if nome not in z.namelist():
                            raise ValueError(f"zip do TSE sem o arquivo {nome}")
            else:
                ufs = sorted({u for c, z in abrir().items() for u in self._ufs_do_zip(z, c, ano)})
            municipios: list[dict] | None = None
            for sigla in ufs:
                if (do_disco := em_disco(sigla)) is not None:
                    lidos.pop(sigla, None)
                    yield do_disco
                    del do_disco
                    continue
                lidos.pop(sigla, None)
                if municipios is None and "votacao" in conjuntos:
                    municipios = self._municipios_ibge()
                parte: dict[str, Any] = {"ano": ano, "uf": sigla}
                for c, z in abrir().items():
                    modelo, colunas = _CONJUNTOS[c][1], _CONJUNTOS[c][2]
                    membro = modelo.format(ano=ano, uf=sigla)
                    linhas = self._linhas(z, membro, colunas) if membro in z.namelist() else iter(())
                    parte[c] = self._somar_zonas(linhas) if c == "votacao" else list(linhas)
                if municipios is not None:
                    parte["municipios_ibge"] = municipios
                self.save_raw(f"tse_{ano}_{sigla}.json", parte)
                yield parte
                del parte  # solta a UF antes de ler a próxima (o chamador também deve soltar)

    def fetch(self, uf: str | None = None, ano: int = 2022,
              conjuntos: tuple[str, ...] = ("candidatos", "receitas", "votacao"),
              reusar_raw: bool = False) -> dict:
        """Lê os zips do TSE por HTTP Range e devolve só Deputado Federal.

        `uf` (ex.: "MG") limita a um estado — use para amostra. Sem `uf` percorre as 27 UFs,
        grava um arquivo bruto por UF (nunca um consolidado) e devolve tudo junto em memória:
        só serve para amostra e testes; para o país inteiro use `fetch_por_uf` (é o que o
        pipeline faz). `reusar_raw`: ver `fetch_por_uf`. Devolve {"ano", "uf", "candidatos",
        "receitas", "votacao", "municipios_ibge"}; a votação vem somada por (candidato,
        município). Validado para ano=2022.
        """
        raw: dict[str, Any] = {"ano": ano, "uf": uf.upper() if uf else None}
        for c in conjuntos:
            raw[c] = []
        for parte in self.fetch_por_uf(uf, ano, conjuntos, reusar_raw):
            for c in conjuntos:
                raw[c] += parte[c]
            if "municipios_ibge" in parte:
                raw["municipios_ibge"] = parte["municipios_ibge"]
        if "votacao" in conjuntos:
            raw.setdefault("municipios_ibge", [])
        return raw

    @staticmethod
    def _somar_zonas(linhas: Iterator[dict]) -> list[dict]:
        soma: dict[tuple[str, str], dict] = {}
        for r in linhas:
            qt = _inteiro(r["QT_VOTOS_NOMINAIS_VALIDOS"])
            if qt is None:
                continue
            chave = (r["SQ_CANDIDATO"], r["CD_MUNICIPIO"])
            if chave in soma:
                soma[chave]["QT_VOTOS_NOMINAIS_VALIDOS"] += qt
            else:
                soma[chave] = {**r, "QT_VOTOS_NOMINAIS_VALIDOS": qt}
        return [{**r, "QT_VOTOS_NOMINAIS_VALIDOS": str(r["QT_VOTOS_NOMINAIS_VALIDOS"])}
                for r in soma.values()]

    # ---------- normalize ----------

    def normalize(self, raw: dict) -> list[Fact]:
        """Funções puras. Só Deputado Federal. Aceita votos por zona ou já somados."""
        ano = _ano(raw.get("ano"), 2022)
        return [*self._candidaturas(raw.get("candidatos", []), ano),
                *self._doacoes(raw.get("receitas", []), ano),
                *self._votos(raw.get("votacao", []), raw.get("municipios_ibge") or [], ano)]

    @staticmethod
    def _candidaturas(linhas: list[dict], ano: int) -> list[Fact]:
        facts = []
        for r in linhas:
            sq = str(r.get("SQ_CANDIDATO") or "").strip()
            if not sq or not _eh_deputado_federal(r.get("DS_CARGO")):
                continue
            a = _ano(r.get("ANO_ELEICAO"), ano)
            facts.append(Fact(
                tipo="candidatura", chave=sq, fonte=FONTE_CANDIDATURA, id_oficial=sq,
                url=_CONJUNTOS["candidatos"][0].format(ano=a),
                atributos={
                    "ano": a, "cpf": _documento(r.get("NR_CPF_CANDIDATO"), (11,)),
                    "nome": _limpo(r.get("NM_CANDIDATO")),
                    "nome_urna": _limpo(r.get("NM_URNA_CANDIDATO")),
                    "cargo": "Deputado Federal", "uf": _limpo(r.get("SG_UF")),
                    "partido": _limpo(r.get("SG_PARTIDO")),
                    "situacao": _limpo(r.get("DS_SIT_TOT_TURNO")),
                }))
        return facts

    @staticmethod
    def _tipo_doador(origem: str, doc: str | None) -> str | None:
        o = _sem_acento(origem).lower()
        if "proprios" in o:
            return "proprio"
        if "partido" in o:
            return "partido"
        return {14: "PJ", 11: "PF"}.get(len(doc or ""))

    def _doacoes(self, linhas: list[dict], ano: int) -> list[Fact]:
        """Uma `doacao` por receita. O TSE repete SQ_RECEITA em receitas estimáveis distintas
        (itens diferentes do mesmo doador): a 2ª ocorrência vira `<sq>:2`, e assim por diante."""
        facts, vistas = [], Counter()
        for r in linhas:
            sq = str(r.get("SQ_RECEITA") or "").strip()
            valor = _valor(r.get("VR_RECEITA"))
            if (not sq or sq == "-1" or valor is None
                    or not _eh_deputado_federal(r.get("DS_CARGO"))):
                continue  # "-1" = candidato sem receita (linha placeholder do TSE)
            vistas[sq] += 1
            doc = _documento(r.get("NR_CPF_CNPJ_DOADOR"))
            origem = str(r.get("DS_ORIGEM_RECEITA") or "")
            a = _ano(r.get("AA_ELEICAO"), ano)
            facts.append(Fact(
                tipo="doacao", chave=sq if vistas[sq] == 1 else f"{sq}:{vistas[sq]}",
                fonte=FONTE_DOACAO, id_oficial=sq,
                url=_CONJUNTOS["receitas"][0].format(ano=a),
                atributos={
                    "ano": a, "sq_candidato": str(r.get("SQ_CANDIDATO") or "").strip(),
                    "doador_nome": _limpo(r.get("NM_DOADOR_RFB")) or _limpo(r.get("NM_DOADOR")),
                    "doador_cpf_cnpj": doc, "valor": valor,
                    "data": _data_iso(r.get("DT_RECEITA")),
                    "tipo_doador": self._tipo_doador(origem, doc),
                    "origem": _limpo(origem),
                }))
        return facts

    @staticmethod
    def _votos(linhas: list[dict], municipios: list[dict], ano: int) -> list[Fact]:
        """`votos_municipio` por (candidato, município). `votos_validos_municipio` = votos
        nominais válidos de TODOS os candidatos a Deputado Federal no município (a base de votos
        de legenda não vem neste arquivo)."""
        ibge = {(m["uf"], _norm_municipio(m["nome"])): str(m["id"]) for m in municipios}
        total: dict[str, int] = defaultdict(int)
        por_cand: dict[tuple[str, str], dict] = {}
        for r in linhas:
            uf = str(r.get("SG_UF") or "").strip().upper()
            sq = str(r.get("SQ_CANDIDATO") or "").strip()
            cd = str(r.get("CD_MUNICIPIO") or "").strip()
            qt = _inteiro(r.get("QT_VOTOS_NOMINAIS_VALIDOS"))
            if (uf in ("", "ZZ") or not sq or not cd or qt is None
                    or not _eh_deputado_federal(r.get("DS_CARGO"))):
                continue
            total[cd] += qt
            if (sq, cd) in por_cand:
                por_cand[(sq, cd)]["votos"] += qt
            else:
                por_cand[(sq, cd)] = {
                    "votos": qt, "uf": uf, "nome": str(r.get("NM_MUNICIPIO") or ""),
                    "ano": _ano(r.get("ANO_ELEICAO"), ano)}
        facts = []
        for (sq, cd), v in por_cand.items():
            chave_nome = (v["uf"], _norm_municipio(v["nome"]))
            cod = ibge.get(chave_nome) or _ALIAS_IBGE.get(chave_nome)
            facts.append(Fact(
                tipo="votos_municipio", chave=f"{v['ano']}:{sq}:{cod or 'tse' + cd}",
                fonte=FONTE_VOTOS, id_oficial=f"{sq}:{cd}",
                url=_CONJUNTOS["votacao"][0].format(ano=v["ano"]),
                atributos={"ano": v["ano"], "sq_candidato": sq, "municipio_ibge": cod,
                           "uf": v["uf"], "votos": v["votos"],
                           "votos_validos_municipio": total[cd],
                           "municipio_tse": cd, "municipio_nome": v["nome"]}))
        return facts
