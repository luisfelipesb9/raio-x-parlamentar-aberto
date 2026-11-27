"""Parcial: checkpoint em arquivos `.json.part` com escrita atômica."""
from __future__ import annotations

from sources.camara.parcial import Parcial


def test_grava_e_le_de_volta(tmp_path):
    p = Parcial(tmp_path / "parcial")
    p.gravar("etapa", {"a": [1, 2], "b": "ç"})
    assert p.ler("etapa") == {"a": [1, 2], "b": "ç"}
    assert [f.name for f in (tmp_path / "parcial").iterdir()] == ["etapa.json.part"]  # sem tmp


def test_etapa_inexistente_e_none(tmp_path):
    assert Parcial(tmp_path / "nada").ler("etapa") is None


def test_arquivo_corrompido_e_ignorado_em_vez_de_derrubar_a_retomada(tmp_path):
    p = Parcial(tmp_path)
    (tmp_path / "etapa.json.part").write_text('{"cortado": [1, 2', encoding="utf-8")
    assert p.ler("etapa") is None


def test_lista_vazia_guardada_nao_se_confunde_com_ausente(tmp_path):
    p = Parcial(tmp_path)
    p.gravar("etapa", [])
    assert p.ler("etapa") == []


def test_retomar_falso_ignora_o_que_existe_mas_ainda_grava(tmp_path):
    Parcial(tmp_path).gravar("etapa", [1])
    p = Parcial(tmp_path, retomar=False)
    assert p.ler("etapa") is None
    p.gravar("etapa", [2])
    assert Parcial(tmp_path).ler("etapa") == [2]


def test_limpar_apaga_so_as_etapas_pedidas_e_remove_a_pasta_quando_esvazia(tmp_path):
    pasta = tmp_path / "parcial"
    p = Parcial(pasta)
    p.gravar("a", 1)
    p.gravar("b", 2)
    p.limpar(["a"])
    assert p.ler("a") is None and p.ler("b") == 2
    p.limpar(["b"])
    assert not pasta.exists()


def test_limpar_tudo(tmp_path):
    pasta = tmp_path / "parcial"
    p = Parcial(pasta)
    p.gravar("a", 1)
    p.limpar()
    assert not pasta.exists()
    p.limpar()  # de novo, sem pasta: não é erro
