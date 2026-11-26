"""Guarda de PII e segredos nos arquivos VERSIONADOS (`git ls-files`).

Reprova (saída 1) se achar:
  - CPF íntegro, com dígitos verificadores válidos, que não esteja em `CPFS_PERMITIDOS`;
  - padrões óbvios de segredo (chaves de nuvem, tokens, chave privada, `senha = "literal"`);
  - arquivo `.env*` versionado (só `.env.example`/`.env.sample`/`.env.template` podem ir ao git).

NUNCA imprime o valor encontrado: só `arquivo:linha` e o tipo. Pula binários e lockfiles.
CPF mascarado (`***.123.456-**`) e CNPJ não contam.

Uso: python -m scripts.checa_pii [--raiz .]   (make checa-pii)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

from ingest.pseudonimizar import CPF_EM_TEXTO, TOKEN_HASH, dv_ok

# CPFs SINTÉTICOS que podem aparecer nos arquivos versionados (só os 11 dígitos). Cada entrada
# precisa de um comentário dizendo onde é usada e por que não é uma pessoa real. Para um CPF novo
# de teste, prefira calculá-lo no próprio teste (como em tests/unit/test_checa_pii.py).
CPFS_PERMITIDOS: frozenset[str] = frozenset({
    "11144477735",  # exemplo clássico de validação de CPF; CPF de deputado/sancionado nas fixtures
    # tests/unit/fixtures/resolve_mg_amostra.json: CPFs inventados (prefixo 9000000) das
    # candidaturas, só para exercitar a resolução por CPF; não pertencem a pessoa conhecida.
    "90000000680", "90000000175", "90000000507", "90000000256", "90000000760",
    "90000000418", "90000000841", "90000000337", "90000000922",
    "98765432100",  # tests/unit/test_rules_r05_r08.py: CPF de sócio inventado ("diferente")
})

CPF_NUMERICO_EM_CHAVE = re.compile(r"""(?i)cpf\w*["']?\s*[:=]\s*["']?(\d{10})(?!\d)""")

LOCKFILES = frozenset({"uv.lock", "pnpm-lock.yaml", "package-lock.json", "yarn.lock",
                       "poetry.lock", "Pipfile.lock"})
ENV_PERMITIDOS = frozenset({".env.example", ".env.sample", ".env.template"})

_SEGREDOS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),                       # chave de acesso AWS
    re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),             # chave privada PEM
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),                      # token do GitHub
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),                      # token do Slack
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),                           # chave de API do Google
    re.compile(r"\b[sr]k_live_[0-9A-Za-z]{16,}\b"),                     # chave live (Stripe)
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),                         # chave de API de LLM
    re.compile(r"""(?ix)\b[\w-]*(?:api[_-]?key|secret|token|passw(?:or)?d|senha)[\w-]*
                   \s*[:=]\s*["'][^"'\s<>${}]{16,}["']"""),             # atribuição de literal
)


class Achado(NamedTuple):
    arquivo: str
    linha: int
    tipo: str  # "cpf" | "segredo" | "env"  (o valor encontrado nunca é guardado)


def _so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def achados_em_texto(arquivo: str, texto: str, *,
                     permitidos: frozenset[str] = CPFS_PERMITIDOS) -> list[Achado]:
    achados: list[Achado] = []
    for n, linha in enumerate(texto.splitlines(), start=1):
        sem_hash = TOKEN_HASH.sub(" ", linha)  # o hash do HMAC não é CPF, mesmo com 11 dígitos
        candidatos = [_so_digitos(m.group()) for m in CPF_EM_TEXTO.finditer(sem_hash)]
        # CPF numérico que perdeu o zero à esquerda, em chave `cpf*` ("cpf": 2998224725)
        candidatos += [m.group(1).zfill(11) for m in CPF_NUMERICO_EM_CHAVE.finditer(sem_hash)]
        if any(dv_ok(d) and d not in permitidos for d in candidatos):
            achados.append(Achado(arquivo, n, "cpf"))
        if any(rx.search(linha) for rx in _SEGREDOS):
            achados.append(Achado(arquivo, n, "segredo"))
    # uma linha com o mesmo tipo duas vezes vira um achado só
    return list(dict.fromkeys(achados))


def arquivos_versionados(raiz: Path) -> list[str]:
    saida = subprocess.run(["git", "ls-files", "-z"], cwd=raiz, check=True,
                           capture_output=True).stdout
    return [p for p in saida.decode("utf-8").split("\0") if p]


def _texto(caminho: Path) -> str | None:
    """Conteúdo do arquivo como texto, ou None se for binário/inexistente."""
    try:
        dados = caminho.read_bytes()
    except OSError:
        return None  # listado no índice, mas removido da árvore de trabalho
    if b"\0" in dados[:8192]:
        return None
    return dados.decode("utf-8", errors="replace")


def checar(raiz: Path, *, permitidos: frozenset[str] = CPFS_PERMITIDOS,
           arquivos: Iterable[str] | None = None) -> list[Achado]:
    achados: list[Achado] = []
    for rel in sorted(arquivos if arquivos is not None else arquivos_versionados(raiz)):
        nome = Path(rel).name
        if nome in LOCKFILES:
            continue
        if nome.startswith(".env") and nome not in ENV_PERMITIDOS:
            achados.append(Achado(rel, 1, "env"))
            continue
        texto = _texto(raiz / rel)
        if texto is not None:
            achados += achados_em_texto(rel, texto, permitidos=permitidos)
    return achados


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--raiz", default=".", help="raiz do repositório git (padrão: .)")
    args = ap.parse_args(argv)
    achados = checar(Path(args.raiz).resolve())
    for a in achados:
        print(f"{a.arquivo}:{a.linha}: {a.tipo}")
    if achados:
        print(f"\nchecagem de PII/segredos REPROVADA: {len(achados)} achado(s) (valores omitidos). "
              "CPF sintético legítimo entra em CPFS_PERMITIDOS (scripts/checa_pii.py), comentado.",
              file=sys.stderr)
        return 1
    print("checagem de PII/segredos: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
