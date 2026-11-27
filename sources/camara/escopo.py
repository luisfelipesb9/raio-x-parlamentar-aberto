"""Escopo de um bruto da Câmara: o que mudaria o conteúdo do `camara_<início>_<fim>.json`.

O `fetch` grava isso no próprio bruto (`_escopo`) e o pipeline confere ao reaproveitar o arquivo
(`--reusar-raw`): um bruto de amostra (teto de votações, outra fonte de votos, outra legislatura)
não pode alimentar uma rodada nacional em silêncio. Funções puras, sem rede nem disco.
"""
from __future__ import annotations

from typing import Any


def escopo_da_coleta(*, legislatura_completa: bool, janela_inicio: str, janela_fim: str,
                     fonte_votos: str, max_votacoes: int | None,
                     legislatura: int | None = None) -> dict[str, Any]:
    """`max_votacoes=None` é "sem teto". `legislatura` é informativa: só pesa a escolha entre
    em exercício e legislatura completa (`legislatura_completa`)."""
    return {"legislatura": legislatura, "legislatura_completa": legislatura_completa,
            "janela": [janela_inicio, janela_fim], "fonte_votos": fonte_votos,
            "max_votacoes": max_votacoes}


def avaliar_reuso(gravado: Any, pedido: dict[str, Any], *, estrito: bool) -> tuple[bool, str]:
    """(pode reaproveitar, mensagem). Mensagem vazia = sem nada a dizer.

    `estrito`: rodada que cobre todos os deputados (nacional ou sem escopo). Um bruto sem registro
    de escopo (coletado antes do registro existir, com a legislatura inteira) só serve a uma
    rodada de amostra, e com aviso; na estrita é recusado.
    """
    if not isinstance(gravado, dict):
        msg = ("sem registro de escopo no bruto (coletado antes de ele existir; pode ter a "
               "legislatura inteira e o teto de votações de uma rodada antiga)")
        return (False, f"{msg}; apague-o para coletar de novo") if estrito else (True, msg)
    if gravado.get("legislatura_completa") != pedido.get("legislatura_completa"):
        return False, (f"legislatura completa = {gravado.get('legislatura_completa')} no bruto, "
                       f"{pedido.get('legislatura_completa')} no pedido")
    if gravado.get("janela") != pedido.get("janela"):
        return False, f"janela de votos {gravado.get('janela')} no bruto, {pedido.get('janela')} no pedido"
    if gravado.get("fonte_votos") != pedido.get("fonte_votos"):
        return False, (f"fonte de votos {gravado.get('fonte_votos')!r} no bruto, "
                       f"{pedido.get('fonte_votos')!r} no pedido")
    teto, quer = gravado.get("max_votacoes"), pedido.get("max_votacoes")
    if teto is not None and (quer is None or quer > teto):
        return False, (f"o bruto guarda só as primeiras {teto} votações e o pedido quer "
                       f"{'todas' if quer is None else quer}")
    return True, ""
