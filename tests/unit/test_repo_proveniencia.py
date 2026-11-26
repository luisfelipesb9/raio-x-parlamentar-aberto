"""Leitura do manifesto do bruto sem passar por `sources` (ADR-009): a API só lê o banco e,
opcionalmente, o hash do manifesto, e não deve carregar os plugins de coleta."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from repo import proveniencia
from sources import manifest

RAIZ = Path(__file__).resolve().parents[2]


def test_importar_api_state_nao_carrega_o_pacote_sources():
    codigo = ("import sys, api.state; "
              "print(sorted(m for m in sys.modules if m == 'sources' or m.startswith('sources.')))")
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True,
                       timeout=120, check=False)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "[]"


def test_mapa_estatico_de_origem_e_igual_ao_derivado_do_registro_de_fontes():
    """Se uma fonte nova declarar `fontes_fato`, o mapa estático da API tem de acompanhar."""
    assert proveniencia.ORIGEM_POR_FONTE_FATO == manifest._origens_por_fonte_fato()


def _grava(raw_dir, itens):
    (raw_dir / "manifest.json").write_text(json.dumps({"versao": 1, "arquivos": itens}), "utf-8")


def test_sha_por_fonte_fato_so_para_origem_com_um_arquivo(tmp_path):
    _grava(tmp_path, [
        {"fonte": "ceap", "arquivo": "Ano-2024.json.zip", "sha256": "a" * 64},
        {"fonte": "camara", "arquivo": "x.json", "sha256": "b" * 64},
        {"fonte": "camara", "arquivo": "y.json", "sha256": "c" * 64},
    ])
    assert proveniencia.sha_por_fonte_fato(tmp_path) == {"camara_ceap": "a" * 64}


def test_sha_por_fonte_fato_igual_ao_do_modulo_de_coleta(tmp_path):
    _grava(tmp_path, [{"fonte": "rfb", "arquivo": "1.json", "sha256": "d" * 64},
                      {"fonte": "ceap", "arquivo": "a.zip", "sha256": "e" * 64}])
    assert proveniencia.sha_por_fonte_fato(tmp_path) == manifest.sha_por_fonte_fato(tmp_path)


def test_sem_manifesto_ou_pasta_inexistente_e_vazio(tmp_path):
    assert proveniencia.sha_por_fonte_fato(tmp_path) == {}
    assert proveniencia.sha_por_fonte_fato(tmp_path / "nao_existe") == {}


def test_manifesto_ilegivel_e_erro_claro(tmp_path):
    (tmp_path / "manifest.json").write_text("{ nao e json", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest.json"):
        proveniencia.sha_por_fonte_fato(tmp_path)


def test_raw_dir_padrao_respeita_a_variavel_de_ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("RAIO_X_RAW", str(tmp_path))
    assert proveniencia.raw_dir_padrao() == tmp_path
    monkeypatch.delenv("RAIO_X_RAW")
    assert proveniencia.raw_dir_padrao() == RAIZ / "data" / "raw"


def test_modulo_de_coleta_e_o_de_leitura_usam_o_mesmo_padrao(monkeypatch):
    monkeypatch.delenv("RAIO_X_RAW", raising=False)
    assert manifest.raw_dir_padrao() == proveniencia.raw_dir_padrao()
