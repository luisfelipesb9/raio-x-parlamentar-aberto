"""Checkpoint da coleta da Câmara: um arquivo por etapa em `data/raw/camara/parcial/`.

Cada etapa (deputados, detalhe dos deputados, cada trimestre de votações, cada lote de
proposições) é gravada assim que termina. Se a coleta cai no meio, o que já veio fica aqui e a
próxima chamada retoma dali. A coleta concluída apaga tudo (`limpar`): o bruto final
(`camara_<início>_<fim>.json`) é o único que fica.

Os arquivos terminam em `.json.part`: o manifesto do bruto ignora `.part` (são incompletos por
definição) e a escrita é atômica (arquivo temporário + `os.replace`), então nunca sobra meio JSON.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


class Parcial:
    def __init__(self, pasta: Path, retomar: bool = True):
        self.pasta = Path(pasta)
        self.retomar = retomar

    def _arquivo(self, nome: str) -> Path:
        return self.pasta / f"{nome}.json.part"

    def ler(self, nome: str) -> Any | None:
        """O que a etapa `nome` guardou, ou None (não há, está ilegível, ou `retomar` é falso)."""
        if not self.retomar:
            return None
        try:
            return json.loads(self._arquivo(nome).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def gravar(self, nome: str, dados: Any) -> None:
        destino = self._arquivo(nome)
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_name(f"{nome}.json.tmp.part")
        tmp.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, destino)

    def limpar(self) -> None:
        shutil.rmtree(self.pasta, ignore_errors=True)
