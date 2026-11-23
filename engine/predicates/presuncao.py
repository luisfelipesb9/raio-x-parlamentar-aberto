"""R08 — Guardrail: presunção de inocência e lacuna de dados."""
from __future__ import annotations

from engine.factbase import FactBase
from engine.predicates.registry import guardrail

# tipos de fato que atribuem algo ao deputado via `deputado_id`
_TIPOS_COM_DEPUTADO = ("voto", "despesa_ceap", "autoria", "emenda", "processo")


@guardrail("presuncao_inocencia_lacuna")
def presuncao_inocencia_lacuna(fb: FactBase, params: dict) -> tuple[int, str]:
    """1) `processo` sem trânsito em julgado sai da base: nenhuma regra pode usá-lo.
    2) Registra deputados sem NENHUM dado. Os predicados só geram candidatos a partir de fatos
       existentes, então esses deputados ficam sem conclusão (nada é imputado); a média do
       partido só circula em `valores` como contexto (ver R05).
    """
    n = fb.exclude("processo", lambda f: f.atributos.get("transitado_em_julgado") is not True,
                   motivo="R08_presuncao_inocencia")
    com_dado = {f.atributos["deputado_id"] for t in _TIPOS_COM_DEPUTADO for f in fb.of(t)
                if f.atributos.get("deputado_id")}
    com_dado |= {c.atributos["deputado_id"] for c in fb.of("candidatura")
                 if c.atributos.get("deputado_id")}
    sem_dado = [d for d in fb.of("deputado") if d.chave not in com_dado]
    return n, (f"{n} processo(s) sem trânsito em julgado removidos; "
               f"{len(sem_dado)} deputado(s) sem nenhum dado: nenhuma regra inventa valor para eles")
