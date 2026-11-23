"""Helpers comuns da resolução de entidades. Funções puras, sem I/O.

`normaliza_nome` é cópia deliberada de engine/predicates/circuito.py: ingest NÃO importa engine
(direção de dependência). Se uma mudar, mude a outra.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from contracts import Fact
from repo.links import Ambiguidade, EntityLink

# deputado_id só é gravado no fato quando o link tem ao menos este fator de certeza
CF_MIN_ENRIQUECER = 0.7


def normaliza_nome(nome: str | None) -> str:
    s = unicodedata.normalize("NFKD", nome or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().upper()


def _cpf11(texto: str | None) -> str | None:
    s = re.sub(r"[.\-\s]", "", str(texto or ""))
    return s if re.fullmatch(r"[\d*]{11}", s) else None


def cpf_pleno(texto: str | None) -> str | None:
    s = _cpf11(texto)
    return s if s and "*" not in s else None


def confronto_cpf(a: str | None, b: str | None) -> str:
    """'igual' | 'diferente' | 'compativel' (mascarado, dígitos visíveis batem) | 'desconhecido'."""
    x, y = _cpf11(a), _cpf11(b)
    if not x or not y:
        return "desconhecido"
    visiveis = [(p, q) for p, q in zip(x, y, strict=True) if p != "*" and q != "*"]
    if any(p != q for p, q in visiveis):
        return "diferente"
    if "*" not in x and "*" not in y:
        return "igual"
    return "compativel" if visiveis else "desconhecido"


def cnpj_valido(cnpj: str) -> bool:
    if len(cnpj) != 14 or not cnpj.isdigit() or len(set(cnpj)) == 1:
        return False
    for n in (12, 13):
        pesos = [*range(n - 7, 1, -1), *range(9, 1, -1)][:n]
        resto = sum(int(d) * p for d, p in zip(cnpj[:n], pesos, strict=True)) % 11
        if int(cnpj[n]) != (0 if resto < 2 else 11 - resto):
            return False
    return True


def nomes_do_deputado(d: Fact) -> set[str]:
    a = d.atributos
    return {n for n in (normaliza_nome(a.get("nome")), normaliza_nome(a.get("nome_civil"))) if n}


def deputados_unicos(deputados: list[Fact]) -> dict[str, Fact]:
    """A API da Câmara repete o deputado (uma linha por partido): vale a última por id."""
    return {d.chave: d for d in deputados}


@dataclass
class Resolucao:
    """Saída de toda resolução: fatos (enriquecidos quando couber), links, ambiguidades."""

    fatos: list[Fact] = field(default_factory=list)
    links: list[EntityLink] = field(default_factory=list)
    ambiguos: list[Ambiguidade] = field(default_factory=list)
    sem_match: list[str] = field(default_factory=list)  # origens "tipo:chave"
    ja_resolvidos: int = 0  # fatos que já vinham com deputado_id (não reprocessados)

    @property
    def origens(self) -> list[str]:
        """Todas as origens avaliadas que a resolução decidiu (para substituir links antigos)."""
        return ([lk.origem for lk in self.links] + [a.origem for a in self.ambiguos]
                + self.sem_match)

    def resumo(self) -> dict[str, int]:
        ligados = len({lk.origem for lk in self.links})
        return {"total": len(self.fatos), "ligados": ligados + self.ja_resolvidos,
                "ambiguos": len(self.ambiguos), "sem_match": len(self.sem_match)}
