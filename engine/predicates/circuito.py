"""R06 — Circuito doador–sócio–fornecedor.

Deputado paga (CEAP) uma empresa cujo sócio (QSA da Receita) tem o mesmo nome de um doador
pessoa física da campanha do próprio deputado. Casamento é por NOME NORMALIZADO, portanto sujeito
a homonímia: o CPF decide (íntegro igual = confirmado; íntegro diferente = descartado; mascarado
= só indício, e dígitos visíveis incompatíveis também descartam).
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from contracts import Evidence, Fact
from engine.factbase import FactBase
from engine.predicates.registry import Candidate, predicate


def normaliza_nome(nome: str | None) -> str:
    s = unicodedata.normalize("NFKD", nome or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().upper()


def _limpa(v: object) -> str:
    return re.sub(r"[.\-/\s]", "", str(v or ""))


def _padrao_cpf(cpf: str | None) -> str | None:
    """11 posições, dígitos conhecidos ou '*'; None se não for um CPF (hash, PJ, vazio)."""
    s = _limpa(cpf)
    return s if len(s) == 11 and re.fullmatch(r"[0-9*]{11}", s) else None


def _lado(cpf: str | None, visivel: object) -> tuple[str | None, str | None]:
    """(padrão de 11 posições, hash) de um lado do confronto.

    `hmac:` vem SEMPRE de CPF íntegro (mascarado permanece mascarado): o hash é comparável por
    igualdade, e `*_visivel` (6 dígitos das posições 4–9) serve para confrontar com um CPF
    mascarado do outro lado. Hash sem visível contra mascarado => indeterminado.
    """
    padrao = _padrao_cpf(cpf)
    if padrao and "*" not in padrao:
        return padrao, None  # CPF íntegro em claro: o visível é irrelevante
    vis = _limpa(visivel)
    derivado = f"***{vis}**" if re.fullmatch(r"\d{6}", vis) else _padrao_cpf(vis)
    if str(cpf or "").startswith("hmac:"):
        return derivado, str(cpf)
    return derivado or padrao, None


def _confronto_cpf(socio: tuple[str | None, str | None], doador: tuple[str | None, str | None],
                   socio_bruto: str | None = None) -> str:
    """'igual' | 'diferente' | 'indeterminado' (CPF não confirmável ou dado ausente).

    Dois hashes: iguais => igual, diferentes => diferente. Senão, dígitos conhecidos
    dos dois lados que divergem => diferente; 'igual' só com os dois CPFs íntegros e iguais.
    """
    bruto = _limpa(socio_bruto)
    if len(bruto) == 14 and "*" not in bruto:
        return "diferente"  # sócio é pessoa jurídica: não é o doador PF
    (ps, hs), (pd, hd) = socio, doador
    if hs and hd:
        return "igual" if hs == hd else "diferente"
    if ps is None or pd is None:
        return "indeterminado"
    if any(a.isdigit() and b.isdigit() and a != b for a, b in zip(ps, pd)):
        return "diferente"
    return "igual" if "*" not in ps and "*" not in pd else "indeterminado"


@predicate("circuito_doador_socio")
def circuito_doador_socio(fb: FactBase, params: dict) -> list[Candidate]:
    """params.modo: 'confirmado' (CPF íntegro igual) ou 'indicio' (CPF não confirmável).

    Os dois modos alimentam regras distintas (R06 e R06b), para que um sócio confirmado nunca
    empreste CF alto a outro cuja identidade não foi confirmada.
    """
    confirmado = params.get("modo", "confirmado") == "confirmado"
    alvo = "igual" if confirmado else "indeterminado"
    sq_dep = {c.chave: c.atributos["deputado_id"] for c in fb.of("candidatura")
              if c.atributos.get("deputado_id")}
    sq_cf = {c.chave: float(c.atributos.get("deputado_cf", 1.0)) for c in fb.of("candidatura")}
    doadores: dict[str, dict[str, list[Fact]]] = defaultdict(lambda: defaultdict(list))
    for d in fb.of("doacao"):
        dep = sq_dep.get(d.atributos.get("sq_candidato"))
        nome = normaliza_nome(d.atributos.get("doador_nome"))
        if dep and nome and d.atributos.get("tipo_doador") == "PF":
            doadores[dep][nome].append(d)
    socios: dict[str, list[Fact]] = defaultdict(list)
    for s in fb.of("socio"):
        socios[s.atributos["cnpj"]].append(s)
    pago: dict[tuple[str, str], list[Fact]] = defaultdict(list)
    for d in fb.of("despesa_ceap"):
        if d.atributos.get("cnpj"):
            pago[(d.atributos["deputado_id"], d.atributos["cnpj"])].append(d)

    out: dict[str, Candidate] = {}
    cnpjs_somados: set[tuple[str, str]] = set()
    doacoes_somadas: set[tuple[str, str]] = set()
    evid: dict[str, set[tuple[str, str]]] = defaultdict(set)
    pares: set[tuple[str, str, str, str]] = set()

    def add_ev(dep: str, c: Candidate, ev: Evidence) -> None:
        if (ev.tipo, ev.id_oficial) not in evid[dep]:
            evid[dep].add((ev.tipo, ev.id_oficial))
            c.evidencias.append(ev)

    for (dep, cnpj), despesas in pago.items():
        for s in socios.get(cnpj, []):
            nome = normaliza_nome(s.atributos.get("nome"))
            for doacao in doadores.get(dep, {}).get(nome, []):
                conf = _confronto_cpf(
                    _lado(s.atributos.get("cpf_cnpj"), s.atributos.get("cpf_visivel")),
                    _lado(doacao.atributos.get("doador_cpf_cnpj"),
                          doacao.atributos.get("doador_cpf_visivel")),
                    s.atributos.get("cpf_cnpj"))
                if conf != alvo or (dep, cnpj, s.chave, doacao.chave) in pares:
                    continue
                pares.add((dep, cnpj, s.chave, doacao.chave))
                c = out.setdefault(dep, Candidate(dep, {
                    "n_circuitos": 0, "n_confirmados": 0, "valor_ceap": 0.0, "valor_doado": 0.0,
                    "cnpjs": []}))
                v = c.valores
                v["n_circuitos"] += 1
                v["n_confirmados"] += int(confirmado)
                if (dep, cnpj) not in cnpjs_somados:  # CEAP: uma vez por (deputado, cnpj)
                    cnpjs_somados.add((dep, cnpj))
                    v["valor_ceap"] = round(v["valor_ceap"] + sum(
                        float(x.atributos.get("valor", 0)) for x in despesas), 2)
                    v["cnpjs"].append(cnpj)
                    for x in despesas[:5]:
                        add_ev(dep, c, Evidence(tipo="despesa_ceap", id_oficial=x.id_oficial,
                                                url=x.url))
                c.premissas_cf.append(sq_cf.get(doacao.atributos.get("sq_candidato"), 1.0))
                if (dep, doacao.chave) not in doacoes_somadas:  # doação: uma vez por doação
                    doacoes_somadas.add((dep, doacao.chave))
                    v["valor_doado"] = round(v["valor_doado"]
                                             + float(doacao.atributos.get("valor", 0)), 2)
                    add_ev(dep, c, Evidence(tipo="doacao", id_oficial=doacao.id_oficial,
                                            url=doacao.url))
                if confirmado:  # identidade não confirmada: não expõe o sócio PF (LGPD)
                    v.setdefault("socios", [])
                    if nome not in v["socios"]:
                        v["socios"].append(nome)
                    add_ev(dep, c, Evidence(tipo="socio", id_oficial=s.id_oficial, url=s.url))
    for c in out.values():
        c.valores["confirmado_por_cpf"] = confirmado
        c.valores["ressalva"] = (
            "identidade confirmada pelo CPF" if confirmado else
            "indício sujeito a confirmação de identidade, pois o CPF do sócio não pôde ser "
            "conferido (mascarado ou ausente) e o casamento foi feito só pelo nome")
    return list(out.values())
