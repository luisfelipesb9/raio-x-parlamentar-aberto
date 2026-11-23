"""Pseudonimização do CPF de TERCEIROS (LGPD): HMAC-SHA256 com sal secreto.

Terceiro = doador de campanha, sócio, fornecedor pessoa física, sancionado, PEP. CPF de deputado e
de candidato é dado cadastral público (ADR-002) e fica íntegro. CPF já mascarado pela fonte
(`***123456**`) e CNPJ não são CPF íntegro: ficam como estão.

O hash é determinístico (mesmo CPF + mesmo sal = mesmo hash), então igualdade entre fatos
continua verificável. No doador gravamos também `doador_cpf_visivel` (os 6 dígitos das posições
4–9, exatamente o que o CPF mascarado do sócio mostra), para o casamento por dígitos visíveis
(R06b) seguir descartando homônimos.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
from collections.abc import Iterable, Mapping
from typing import Any

from contracts import Fact

ENV_SALT = "RAIO_X_ID_SALT"
PREFIXO = "hmac:"
_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")
# CPF solto em texto livre (plano ou formatado)
CPF_EM_TEXTO = (re.compile(r"(?<!\d)\d{11}(?!\d)"), re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)"))
# tipos cujo CPF é dado cadastral público (ADR-002): nada é trocado neles
PUBLICOS = ("deputado", "candidatura")
# o próprio hash (32 hex) pode conter, por acaso, 11 dígitos seguidos: nunca é tratado como CPF
TOKEN_HASH = re.compile(r"hmac:[0-9a-f]{32}")
# (tipo, atributo) cujo valor pode ser CPF de terceiro (texto ou lista de textos)
CAMPOS: dict[str, tuple[str, ...]] = {
    "doacao": ("doador_cpf_cnpj",), "socio": ("cpf_cnpj",), "despesa_ceap": ("cpf",),
    "sancao": ("cpf",), "pep": ("cpf", "cpfs"),
}


def salt_do_ambiente(env: Mapping[str, str] | None = None) -> str:
    salt = (os.environ if env is None else env).get(ENV_SALT, "").strip()
    if not salt:
        raise ValueError(f"--pseudonimizar exige o sal secreto na variável de ambiente {ENV_SALT} "
                         "(não vai para o repositório; guarde-o fora dele)")
    return salt


def cpf_integro(valor: Any) -> str | None:
    """Os 11 dígitos se `valor` é um CPF íntegro (com ou sem pontuação); senão None."""
    s = str(valor or "").strip()
    return re.sub(r"\D", "", s) if _CPF.fullmatch(s) else None


def dv_ok(d: str) -> bool:
    """Dígitos verificadores do CPF (11 dígitos; sequência repetida não vale)."""
    if len(d) != 11 or not d.isdigit() or len(set(d)) == 1:
        return False
    for n in (9, 10):
        soma = sum(int(c) * p for c, p in zip(d[:n], range(n + 1, 1, -1), strict=True))
        if int(d[n]) != (soma * 10 % 11) % 10:
            return False
    return True


def hash_cpf(cpf11: str, salt: str) -> str:
    return PREFIXO + hmac.new(salt.encode(), cpf11.encode(), hashlib.sha256).hexdigest()[:32]


def pseudonimizar_fatos(fatos: Iterable[Fact], salt: str) -> list[Fact]:
    """Cópias dos fatos com o CPF íntegro de terceiros trocado pelo hash. Entrada não muda."""
    return [_um(f, salt) for f in fatos]


def _em_texto(valor: Any, salt: str) -> Any:
    """Troca CPF válido solto dentro de texto (ex.: nome do fornecedor + CPF) pelo hash."""
    if isinstance(valor, str):
        tokens = TOKEN_HASH.findall(valor)
        partes = TOKEN_HASH.split(valor)
        for rx in CPF_EM_TEXTO:
            partes = [rx.sub(lambda m: hash_cpf(re.sub(r"\D", "", m.group()), salt)
                             if dv_ok(re.sub(r"\D", "", m.group())) else m.group(), p)
                      for p in partes]
        saida = partes[0]
        for tok, resto in zip(tokens, partes[1:], strict=True):
            saida += tok + resto
        return saida
    if isinstance(valor, list):
        return [_em_texto(v, salt) for v in valor]
    if isinstance(valor, dict):
        return {k: _em_texto(v, salt) for k, v in valor.items()}
    return valor


def _um(f: Fact, salt: str) -> Fact:
    if f.tipo in PUBLICOS:
        return f
    f = _estruturado(f, salt)
    texto = {k: _em_texto(v, salt) for k, v in f.atributos.items()}
    return f.model_copy(update={"atributos": texto}) if texto != f.atributos else f


def _estruturado(f: Fact, salt: str) -> Fact:
    campos = CAMPOS.get(f.tipo)
    if not campos:
        return f
    novos: dict[str, Any] = {}
    for campo in campos:
        v = f.atributos.get(campo)
        if isinstance(v, list):
            if any(cpf_integro(x) for x in v):
                novos[campo] = [hash_cpf(c, salt) if (c := cpf_integro(x)) else x for x in v]
        elif c := cpf_integro(v):
            novos[campo] = hash_cpf(c, salt)
            if f.tipo == "doacao":
                novos["doador_cpf_visivel"] = c[3:9]
            elif f.tipo == "socio":
                novos["cpf_visivel"] = c[3:9]  # o que o CPF mascarado dos demais sócios mostra
    return f.model_copy(update={"atributos": {**f.atributos, **novos}}) if novos else f
