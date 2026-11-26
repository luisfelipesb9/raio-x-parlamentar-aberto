"""Juiz consultivo (ADR-008): escolhe UMA opção entre opções fechadas.

Só roteia (ex.: texto livre -> um dos objetivos do /perguntar). Nunca muda CF, regras nem
guardrails: a conclusão continua sendo calculada por `forward.py` e `backward.py`.

Hoje existe só o `NullJudge`: determinístico, sem rede e sem chave de API. O `JevJudge` do ADR-008
ainda NÃO está implementado; pedir `RAIO_X_JUDGE=jev` é erro. Este módulo ainda não está ligado
ao `/perguntar`.
"""
from __future__ import annotations

import os
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

ENV_JUDGE = "RAIO_X_JUDGE"


@dataclass(frozen=True)
class Decisao:
    """`opcao` None = o juiz não decidiu (nenhuma pista, empate ou nenhuma opção oferecida)."""

    opcao: str | None
    probabilidade: float
    confianca: float


@runtime_checkable
class Judge(Protocol):
    def decidir(self, pergunta: str, opcoes: Sequence[str]) -> Decisao: ...


# Pistas por objetivo do /perguntar (radicais, sem acento, em minúsculas).
PALAVRAS_CHAVE: dict[str, tuple[str, ...]] = {
    "alinhado_governo": ("governo", "governis", "alinhad", "basometro", "apoia"),
    "risco_integridade": ("integridade", "risco", "sancion", "fornecedor", "irregular", "ceis",
                          "cnep", "gasto", "outlier"),
    "concentracao_eleitoral_emendas": ("emenda", "concentra", "eleitoral", "municip", "pix"),
    "pontuacao_producao_legislativa": ("producao", "legislativ", "projeto", "proposic", "autoria",
                                       "relator"),
    "merece_atencao_fiscalizacao": ("atencao", "fiscaliz", "merece"),
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


class NullJudge:
    """Casa palavras-chave com as opções oferecidas. Vence a opção com mais pistas distintas;
    empate ou nenhuma pista = não decide. `probabilidade` é a fatia de pistas da vencedora;
    `confianca` é 0,5 com uma pista e 0,8 com duas ou mais (heurística, não calibrada)."""

    def decidir(self, pergunta: str, opcoes: Sequence[str]) -> Decisao:
        texto = _normalizar(pergunta)
        acertos = {o: sum(1 for p in PALAVRAS_CHAVE.get(o, ()) if p in texto) for o in opcoes}
        total = sum(acertos.values())
        if total == 0:
            return Decisao(None, 0.0, 0.0)
        melhor = max(acertos.values())
        vencedoras = [o for o, n in acertos.items() if n == melhor]
        if len(vencedoras) != 1:
            return Decisao(None, 0.0, 0.0)
        return Decisao(vencedoras[0], round(melhor / total, 3), 0.8 if melhor >= 2 else 0.5)


def get_judge(env: Mapping[str, str] | None = None) -> Judge:
    """Juiz escolhido por `RAIO_X_JUDGE` (padrão `null`)."""
    valor = ((env if env is not None else os.environ).get(ENV_JUDGE) or "null").strip().lower()
    if valor in ("", "null"):
        return NullJudge()
    if valor == "jev":
        raise NotImplementedError(
            f"{ENV_JUDGE}=jev: juiz jev ainda não implementado (ADR-008); use `null`.")
    raise ValueError(f"{ENV_JUDGE}={valor!r} desconhecido; valores aceitos: null")
