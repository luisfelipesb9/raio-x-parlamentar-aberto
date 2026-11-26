"""Manifesto do bruto: `data/raw/manifest.json` guarda, por arquivo coletado, de onde veio e o hash.

Cada item: {fonte, arquivo, sha256, bytes, coletado_em, origem}. `fonte` é a pasta da fonte
(`camara`, `ceap`, ...); `arquivo` é o caminho dentro dela; `origem` é "coleta" (gravado na hora do
download) ou "retroativo" (hash de um arquivo que já existia, ver `gerar_retroativo`).

Quem coleta chama `registrar`; quem confere chama `verificar`. A escrita é atômica (arquivo
temporário + `os.replace`). Não há trava entre processos: não rode duas coletas ao mesmo tempo.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

NOME = "manifest.json"
VERSAO = 1
_PEDACO = 1 << 20


class Problema(NamedTuple):
    arquivo: str  # "<fonte>/<arquivo>"
    tipo: str  # sha256_diferente | ausente | nao_registrado
    detalhe: str


def raw_dir_padrao() -> Path:
    """Pasta dos brutos: $RAIO_X_RAW ou data/raw do projeto."""
    from sources.base import RAW_DIR  # import tardio: sources.base importa este módulo
    return Path(os.environ.get("RAIO_X_RAW") or RAW_DIR)


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        while pedaco := f.read(_PEDACO):
            h.update(pedaco)
    return h.hexdigest()


def carregar(raw_dir: Path) -> dict[str, Any]:
    """Manifesto da pasta; vazio se ainda não existe. Arquivo ilegível é erro (nunca é refeito)."""
    caminho = Path(raw_dir) / NOME
    if not caminho.exists():
        return {"versao": VERSAO, "arquivos": []}
    try:
        corpo = json.loads(caminho.read_text(encoding="utf-8"))
        valido = isinstance(corpo, dict) and isinstance(corpo.get("arquivos"), list)
        erro = None if valido else "formato inesperado"
    except (ValueError, OSError) as e:
        erro = str(e)
    if erro:
        raise ValueError(f"{caminho} ilegível ({erro}): corrija ou apague o {NOME} e gere de novo "
                         "com `--gerar-manifesto`")
    return corpo


def _gravar(raw_dir: Path, corpo: dict[str, Any]) -> None:
    corpo["arquivos"].sort(key=lambda i: (i["fonte"], i["arquivo"]))
    destino = Path(raw_dir) / NOME
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="manifest.", suffix=".tmp", dir=destino.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(corpo, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, destino)
    finally:
        Path(tmp).unlink(missing_ok=True)


def _item(raw_dir: Path, fonte: str, arquivo: str, origem: str,
          coletado_em: datetime | None = None) -> dict[str, Any]:
    caminho = Path(raw_dir) / fonte / arquivo
    return {"fonte": fonte, "arquivo": arquivo, "sha256": sha256_arquivo(caminho),
            "bytes": caminho.stat().st_size,
            "coletado_em": (coletado_em or datetime.now(UTC)).isoformat(), "origem": origem}


def registrar(raw_dir: Path, fonte: str, arquivo: str) -> dict[str, Any]:
    """Grava (ou atualiza) o item de `raw_dir/<fonte>/<arquivo>`, que já deve estar no disco."""
    corpo = carregar(raw_dir)
    item = _item(raw_dir, fonte, arquivo, "coleta")
    corpo["arquivos"] = [i for i in corpo["arquivos"]
                         if (i["fonte"], i["arquivo"]) != (fonte, arquivo)] + [item]
    _gravar(raw_dir, corpo)
    return item


def _arquivos_em_disco(raw_dir: Path) -> list[tuple[str, str]]:
    """(fonte, arquivo) de tudo que está sob raw_dir/<fonte>/, sem o manifesto nem downloads
    incompletos (`.part`)."""
    achados = []
    for pasta in sorted(p for p in Path(raw_dir).iterdir() if p.is_dir()):
        for f in sorted(p for p in pasta.rglob("*") if p.is_file() and p.suffix != ".part"):
            achados.append((pasta.name, f.relative_to(pasta).as_posix()))
    return achados


def verificar(raw_dir: Path) -> list[Problema]:
    """Compara o manifesto com o disco: hash diferente, arquivo ausente ou fora do manifesto."""
    raw_dir = Path(raw_dir)
    registrados = {(i["fonte"], i["arquivo"]): i for i in carregar(raw_dir)["arquivos"]}
    em_disco = set(_arquivos_em_disco(raw_dir)) if raw_dir.is_dir() else set()
    problemas: list[Problema] = []
    for (fonte, arquivo), item in sorted(registrados.items()):
        rotulo = f"{fonte}/{arquivo}"
        caminho = raw_dir / fonte / arquivo
        if not caminho.is_file():
            problemas.append(Problema(rotulo, "ausente", "listado no manifesto, não está no disco"))
        elif (atual := sha256_arquivo(caminho)) != item["sha256"]:
            problemas.append(Problema(
                rotulo, "sha256_diferente", f"manifesto {item['sha256'][:12]}…, disco {atual[:12]}…"))
    for fonte, arquivo in sorted(em_disco - registrados.keys()):
        problemas.append(Problema(f"{fonte}/{arquivo}", "nao_registrado",
                                  "está no disco, não está no manifesto"))
    return problemas


def gerar_retroativo(raw_dir: Path) -> int:
    """Registra os arquivos que já estão no disco e ainda não constam no manifesto.

    `coletado_em` = data de modificação do arquivo e `origem` = "retroativo": é o melhor que se
    sabe, não o momento exato do download. Itens existentes não são tocados. Devolve quantos entraram."""
    raw_dir = Path(raw_dir)
    corpo = carregar(raw_dir)
    ja = {(i["fonte"], i["arquivo"]) for i in corpo["arquivos"]}
    novos = []
    for fonte, arquivo in _arquivos_em_disco(raw_dir):
        if (fonte, arquivo) in ja:
            continue
        mtime = datetime.fromtimestamp((raw_dir / fonte / arquivo).stat().st_mtime, UTC)
        novos.append(_item(raw_dir, fonte, arquivo, "retroativo", mtime))
    if novos:
        corpo["arquivos"] += novos
        _gravar(raw_dir, corpo)
    return len(novos)


def _origens_por_fonte_fato() -> dict[str, str]:
    """`Fact.fonte` -> pasta da fonte que o produz (cada `Source` declara `fontes_fato`)."""
    from sources import REGISTRY  # import tardio: sources.base importa este módulo
    return {f: cls.nome for cls in REGISTRY.values() for f in cls.fontes_fato}


def sha_por_fonte_fato(raw_dir: Path) -> dict[str, str]:
    """`Fact.fonte` -> sha256 do bruto, só para a fonte com UM arquivo no manifesto.

    Fonte com vários arquivos (ex.: Câmara tem votações e proposições; CGU tem três zips; RFB, um
    JSON por CNPJ) fica de fora: o fato não diz de qual deles veio, e apontar um seria afirmar
    mais do que se sabe."""
    if not (Path(raw_dir) / NOME).exists():
        return {}
    por_origem: dict[str, list[str]] = {}
    for i in carregar(raw_dir)["arquivos"]:
        por_origem.setdefault(i["fonte"], []).append(i["sha256"])
    return {fonte_fato: hashes[0] for fonte_fato, origem in _origens_por_fonte_fato().items()
            if len(hashes := por_origem.get(origem, [])) == 1}
