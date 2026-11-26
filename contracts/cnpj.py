"""CNPJ: forma e dígito verificador, numérico e alfanumérico. Funções puras, sem I/O.

Fonte oficial: Receita Federal, "Perguntas & Respostas - Novo CNPJ Alfanumérico", pergunta 14
(https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/
cnpj/cnpj-alfanumerico.pdf). A partir de julho de 2026 a Receita passa a emitir CNPJ com 14
posições: as 12 primeiras (raiz e ordem) em 0-9 e A-Z, e as 2 últimas (DV) sempre numéricas. Os
formatos numérico e alfanumérico coexistem, e a máscara é a mesma (`XX.XXX.XXX/XXXX-DV`).

DV por módulo 11: cada caractere vale `ord(c) - 48` (0-9 -> 0-9, A-Z -> 17-42), multiplicado pelos
pesos 5 4 3 2 9 8 7 6 5 4 3 2 (1º DV, sobre as 12 posições) e 6 5 4 3 2 9 8 7 6 5 4 3 2 (2º DV,
sobre as 12 mais o 1º DV). `resto = soma % 11`; DV = 0 se resto < 2, senão 11 - resto. (A regra
"resto < 2 vira 0" é a mesma do CNPJ numérico; o exemplo do documento não a exercita.)
Para CNPJ só de dígitos o resultado é idêntico ao algoritmo antigo.

Este módulo é a única implementação e vive em `contracts/` (puro, só stdlib, usado por todas as
camadas sem que uma fonte importe a outra): `sources/*`, `ingest`, `graph` e `engine`. Não faz
parte dos tipos do contrato, então não muda `CONTRACT_VERSION`. `sources/rfb/normalizacao.py`
reexporta os mesmos nomes.
"""
from __future__ import annotations

import re
from typing import Any

_PESOS_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_2 = (6, *_PESOS_1)
_SEPARADORES = re.compile(r"[.\-/\s]")
_FORMA = re.compile(r"[A-Z0-9]{12}[0-9]{2}")
_BASE = re.compile(r"[A-Z0-9]{12}")


def _dv(texto: str, pesos: tuple[int, ...]) -> int:
    resto = sum((ord(c) - 48) * p for c, p in zip(texto, pesos, strict=True)) % 11
    return 0 if resto < 2 else 11 - resto


def dv_cnpj(base: str) -> str:
    """Os 2 dígitos verificadores das 12 primeiras posições (0-9 e A-Z maiúsculas)."""
    if not _BASE.fullmatch(base):
        raise ValueError(f"base de CNPJ precisa de 12 posições em A-Z/0-9, recebi {base!r}")
    d1 = _dv(base, _PESOS_1)
    return f"{d1}{_dv(base + str(d1), _PESOS_2)}"


def normalizar_cnpj(texto: Any) -> str | None:
    """CNPJ sem máscara e em maiúsculas (14 posições, DV numérico) ou None. Só confere a FORMA,
    não o DV (use `cnpj_valido`). 11 posições (CPF), CPF mascarado e hash não são CNPJ."""
    if not isinstance(texto, str):
        return None
    limpo = _SEPARADORES.sub("", texto).upper()
    return limpo if _FORMA.fullmatch(limpo) else None


def cnpj_valido(texto: Any) -> bool:
    """Forma + DV (módulo 11, numérico ou alfanumérico). Recusa sequência de um caractere só
    (ex.: 11111111111111), que passa no módulo 11 mas a Receita não emite."""
    cnpj = normalizar_cnpj(texto)
    if cnpj is None or len(set(cnpj)) == 1:
        return False
    return dv_cnpj(cnpj[:12]) == cnpj[12:]
