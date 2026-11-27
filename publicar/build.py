"""Do banco pseudonimizado e com findings ao arquivo público enxuto (ADR-011).

Fica entre `graph` e `api` na regra de dependência: pode importar tudo à esquerda; só a `api/` lê o
resultado. Roda no banco COMPLETO (grafo, inferência e contagens saem dos fatos todos) e grava, num
arquivo novo e sem chave primária, só o que a API ainda consulta. Falha, sem deixar arquivo, se o
resultado tiver CPF íntegro de terceiro.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from contracts import CONTRACT_VERSION, Finding
from engine import forward
from engine.factbase import FactBase
from engine.rules import load_rules
from graph import project, sal_do_ambiente
from ingest.varredura import varrer_banco
from repo.store import Store

# Fatos que a API lê por deputado (ficha, votos, afinidade) ou que dão nome a nó: ficam por inteiro.
# Os demais (despesa_ceap, votos_municipio, doacao, emenda, empresa, socio, pep, ...) só ficam se algum
# finding os cita como evidência; o grafo já foi materializado antes do corte, então o nome de empresa
# ou município do nó vem de `graph_node`, não dos fatos.
TIPOS_INTEGRAIS = ("deputado", "votacao", "voto", "proposicao", "autoria", "candidatura", "sancao")


class PublicacaoErro(RuntimeError):
    """Pré-condição ou verificação final da publicação falhou (nada é gravado em `destino`)."""


@dataclass(frozen=True)
class ResumoPublicacao:
    destino: Path
    n_fatos_origem: int
    n_fatos_publicados: int
    fatos_por_tipo: dict[str, int]
    n_findings: int
    n_nos: int
    n_arestas: int
    bytes_destino: int
    sha256_origem: str


def _sha256(arquivo: Path) -> str:
    h = hashlib.sha256()
    with arquivo.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _iso(momento: datetime | None) -> str | None:
    return momento.astimezone(UTC).isoformat() if momento else None


def _conferir_findings(tabela: list[Finding], motor: list[Finding]) -> None:
    """A tabela `finding` e o motor precisam concordar: `/findings` lê a tabela e `/perguntar`, a
    inferência. Se divergem, a origem está desatualizada em relação aos fatos."""
    a = {f.id: f.cf for f in tabela}
    b = {f.id: f.cf for f in motor}
    if a.keys() != b.keys() or any(abs(a[i] - b[i]) > 1e-9 for i in a):
        raise PublicacaoErro(
            f"os findings do banco de origem ({len(a)}) não batem com os do motor ({len(b)}): "
            "rode `make infer` sobre a origem e publique de novo")


def _meta(*, origem_sha: str, agora: datetime, hoje: date, por_tipo: dict[str, int],
          mantidos: dict[str, int], fontes: list[Any], janela: Any, n_findings: int, n_nos: int,
          n_arestas: int) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "gerado_em": agora.astimezone(UTC).isoformat(),
        "grafo_em": hoje.isoformat(),  # data usada para "sanção vigente" nos nós de empresa
        "origem_sha256": origem_sha,
        "n_fatos_origem": sum(por_tipo.values()),
        "contagem_por_tipo": por_tipo,
        "fatos_publicados_por_tipo": mantidos,
        "tipos_integrais": list(TIPOS_INTEGRAIS),
        "cobertura_fontes": [
            {"fonte": f.fonte, "tipos": f.tipos, "n_fatos": f.n_fatos,
             "coletado_em_min": _iso(f.coletado_em_min), "coletado_em_max": _iso(f.coletado_em_max)}
            for f in fontes],
        "janela_votos": {
            "inicio": janela.inicio.isoformat() if janela.inicio else None,
            "fim": janela.fim.isoformat() if janela.fim else None,
            "n_votacoes": janela.n_votacoes, "n_votacoes_nominais": janela.n_votacoes_nominais,
            "n_votacoes_com_orientacao": janela.n_votacoes_com_orientacao},
        "n_deputados": por_tipo.get("deputado", 0),
        "n_findings": n_findings, "n_nos": n_nos, "n_arestas": n_arestas,
    }


def _apagar(tmp: Path) -> None:
    for sufixo in ("", ".wal"):
        Path(f"{tmp}{sufixo}").unlink(missing_ok=True)


def publicar(origem: Path | str, destino: Path | str, *, sal_id: str | None = None,
             hoje: date | None = None, agora: datetime | None = None) -> ResumoPublicacao:
    """Gera `destino` a partir de `origem` (já pseudonimizada e com findings). `sal_id`: o mesmo
    `RAIO_X_ID_SALT` da pseudonimização (padrão: o do ambiente; sem ele, `SalAusenteError`)."""
    origem, destino = Path(origem), Path(destino)
    if not origem.is_file():
        raise PublicacaoErro(f"banco de origem não existe: {origem}")
    if destino.resolve() == origem.resolve():
        raise PublicacaoErro("origem e destino são o mesmo arquivo")
    if destino.exists():
        raise PublicacaoErro(f"o destino já existe: {destino} (apague-o antes; não sobrescrevo arquivo)")
    sal = sal_id if sal_id is not None else sal_do_ambiente()  # falha antes de criar qualquer arquivo
    hoje, agora = hoje or date.today(), agora or datetime.now(UTC)
    sha = _sha256(origem)

    src = Store(origem, read_only=True)
    try:
        fatos, findings = src.load_facts(), src.load_findings()
        nos, arestas = project(fatos, findings, sal_id=sal, hoje=hoje)  # sobre os fatos COMPLETOS
        resultado = forward.run(FactBase(fatos), load_rules())
        _conferir_findings(findings, resultado.findings)
        por_tipo, fontes, janela = src.contagem_por_tipo(), src.cobertura_fontes(), src.janela_votos()
    finally:
        src.con.close()
    del fatos

    tmp = destino.with_name(destino.name + ".tmp")
    _apagar(tmp)
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        pub = Store.novo_publico(tmp)
        try:
            mantidos = pub.copiar_enxuto(origem, tipos_integrais=TIPOS_INTEGRAIS)
            pub.save_graph(nos, arestas)
            pub.save_inferencia(resultado.findings)
            pub.save_publicacao_meta(_meta(
                origem_sha=sha, agora=agora, hoje=hoje, por_tipo=por_tipo, mantidos=mantidos,
                fontes=fontes, janela=janela, n_findings=len(findings), n_nos=len(nos),
                n_arestas=len(arestas)))
            pub.checkpoint()
        finally:
            pub.con.close()
        conferencia = Store(tmp, read_only=True)
        try:
            achados = varrer_banco(conferencia)
        finally:
            conferencia.con.close()
        if achados:
            raise PublicacaoErro(
                f"{len(achados)} ocorrência(s) de CPF íntegro de terceiro no banco público: a origem "
                "não está pseudonimizada (rode `python -m ingest.varredura` nela para ver onde)")
        tmp.replace(destino)
    except BaseException:
        _apagar(tmp)
        raise
    return ResumoPublicacao(
        destino=destino, n_fatos_origem=sum(por_tipo.values()), n_fatos_publicados=sum(mantidos.values()),
        fatos_por_tipo=mantidos, n_findings=len(findings), n_nos=len(nos), n_arestas=len(arestas),
        bytes_destino=destino.stat().st_size, sha256_origem=sha)
