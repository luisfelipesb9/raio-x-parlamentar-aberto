"""Confere o que seria enviado ao ar: só a base pública, limpa de CPF íntegro de terceiros, e um sal forte.

Falha (exit 1) se: a base pública não existe ou tem CPF íntegro de terceiro; existe QUALQUER
outro `*.duckdb` / `*.duckdb.wal` na árvore (a base de trabalho tem CPF íntegro); existe um
`.env`/`.env.*` local (segredo; só `.env.example`/`.sample`/`.template` passam); ou o
`RAIO_X_ID_SALT` do ambiente (o que gerou a base pública) está ausente, tem menos de 32
caracteres ou é um valor público conhecido (versão antiga, demo, testes). O valor do sal nunca é
impresso. Ignora .git, .venv, node_modules, .next e caches.

Uso: python -m ingest.deploy_check [--raiz .] [--publico data/sample/raio_x_publico.duckdb]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ingest.pseudonimizar import ENV_SALT

PUBLICO = Path("data/sample/raio_x_publico.duckdb")
IGNORAR = {".git", ".venv", "node_modules", ".next", ".pytest_cache", ".ruff_cache",
           "__pycache__"}
ENV_DE_EXEMPLO = {".env.example", ".env.sample", ".env.template"}
TAMANHO_MINIMO_SAL = 32
# Sais que estão (ou estiveram) no repositório: com eles o HMAC do CPF se desfaz por força bruta.
SAIS_PUBLICOS = frozenset({
    "raio-x-v1",                 # sal padrão das versões antigas
    "sal-fixo-da-demonstracao",  # demo fictícia (scripts/seed_demo.py, make dev-demo)
    "sal-somente-para-testes",   # testes e CI
    "sal-de-teste",              # testes
})


def verificar_sal(sal: str | None) -> list[str]:
    """Erros do sal usado na base pública (sem nunca repetir o valor)."""
    valor = (sal or "").strip()
    if not valor:
        return [f"{ENV_SALT} ausente: exporte o mesmo sal secreto que gerou a base pública"]
    if valor in SAIS_PUBLICOS:
        return [(f"{ENV_SALT} é um valor público (está no repositório): gere um sal secreto novo "
                "e refaça a base com `make sample-publico`")]
    if len(valor) < TAMANHO_MINIMO_SAL:
        return [(f"{ENV_SALT} curto demais ({len(valor)} caracteres; mínimo {TAMANHO_MINIMO_SAL}): "
                "gere um sal secreto novo e refaça a base com `make sample-publico`")]
    return []


def _arquivos(raiz: Path) -> list[Path]:
    achados = []
    for pasta, dirs, arquivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in IGNORAR]
        achados += [Path(pasta) / a for a in arquivos]
    return achados


def _e_banco(p: Path) -> bool:
    return p.name.endswith((".duckdb", ".duckdb.wal"))


def _e_segredo_local(p: Path) -> bool:
    return (p.name == ".env" or p.name.startswith(".env.")) and p.name not in ENV_DE_EXEMPLO


def verificar_envio(raiz: Path | str, publico: Path | str = PUBLICO) -> list[str]:
    from ingest.varredura import varrer_banco
    from repo.store import Store
    raiz = Path(raiz).resolve()
    pub = Path(publico)
    pub = (pub if pub.is_absolute() else raiz / pub).resolve()
    arquivos = sorted(_arquivos(raiz))
    erros = [f"banco fora da base pública no que seria enviado: {p.relative_to(raiz)}"
             for p in arquivos if _e_banco(p) and p.resolve() != pub]
    erros += [f"arquivo de segredo local no que seria enviado: {p.relative_to(raiz)} "
              "(mova o valor para as variáveis de ambiente da plataforma)"
              for p in arquivos if _e_segredo_local(p)]
    if not pub.exists():
        return [f"a base pública não existe: {pub.relative_to(raiz) if pub.is_relative_to(raiz) else pub}",
                *erros]
    achados = varrer_banco(Store(pub, read_only=True))
    if achados:
        erros.append(f"{len(achados)} ocorrência(s) de CPF íntegro de terceiro na base pública "
                     "(rode ingest.varredura para ver onde)")
    return erros


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--publico", default=str(PUBLICO))
    a = ap.parse_args(argv)
    erros = verificar_sal(os.environ.get(ENV_SALT)) + verificar_envio(a.raiz, a.publico)
    for e in erros:
        print(f"REPROVADO: {e}")
    print("deploy-check: " + ("reprovado" if erros else "ok (só a base pública, sem CPF de terceiros, sal forte)"))
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
