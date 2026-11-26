"""Leitura do manifesto do bruto (`data/raw/manifest.json`), sem rede e sem os plugins de coleta.

Módulo folha (só biblioteca padrão): a API o usa para completar o `sha256_bruto` das evidências de
findings antigos sem importar o pacote `sources` (ADR-009). Quem ESCREVE o manifesto é
`sources.manifest`, que importa daqui o que é comum (formato, leitura, pasta padrão).

`ORIGEM_POR_FONTE_FATO` repete o que cada `Source` declara em `fontes_fato`; um teste confere que
os dois mapas são iguais, então fonte nova obriga a atualizar este.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

NOME = "manifest.json"
VERSAO = 1
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# `Fact.fonte` -> pasta da fonte (em data/raw/) que produz o fato
ORIGEM_POR_FONTE_FATO: dict[str, str] = {
    "camara_api_v2": "camara",
    "camara_ceap": "ceap",
    "cgu_ceis": "cgu",
    "cgu_cnep": "cgu",
    "cgu_emendas": "cgu",
    "tse_consulta_cand": "tse",
    "tse_prestacao_contas": "tse",
    "tse_votacao_munzona": "tse",
    "opensanctions_br_pep": "opensanctions",
    "brasilapi_cnpj": "rfb",
}


def raw_dir_padrao() -> Path:
    """Pasta dos brutos: $RAIO_X_RAW ou data/raw do projeto."""
    return Path(os.environ.get("RAIO_X_RAW") or RAW_DIR)


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


def sha_por_fonte_fato(raw_dir: Path, origens: dict[str, str] | None = None) -> dict[str, str]:
    """`Fact.fonte` -> sha256 do bruto, só para a fonte com UM arquivo no manifesto.

    Fonte com vários arquivos (ex.: Câmara tem votações e proposições; CGU tem três zips; RFB, um
    JSON por CNPJ) fica de fora: o fato não diz de qual deles veio, e apontar um seria afirmar
    mais do que se sabe. Sem manifesto, devolve vazio. `origens`: mapa a usar no lugar do padrão."""
    if not (Path(raw_dir) / NOME).exists():
        return {}
    por_origem: dict[str, list[str]] = {}
    for i in carregar(raw_dir)["arquivos"]:
        por_origem.setdefault(i["fonte"], []).append(i["sha256"])
    return {fonte_fato: hashes[0]
            for fonte_fato, origem in (origens or ORIGEM_POR_FONTE_FATO).items()
            if len(hashes := por_origem.get(origem, [])) == 1}
