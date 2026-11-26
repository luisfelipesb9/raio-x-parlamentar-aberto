"""Manifesto do bruto (data/raw/manifest.json): proveniência dos arquivos coletados (ADR-007)."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

import pytest

import sources.base
from contracts import Fact
from sources import manifest
from sources.base import Source


class FonteFalsa(Source):
    nome = "falsa"

    def fetch(self, **kwargs):
        return {}

    def normalize(self, raw) -> list[Fact]:
        return []


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.base, "RAW_DIR", tmp_path)
    return tmp_path


def lido(raw_dir):
    return json.loads((raw_dir / "manifest.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- gravação
def test_save_raw_cria_o_manifesto_com_hash_tamanho_e_data(raw_dir):
    FonteFalsa().save_raw("a.json", {"x": 1})
    corpo = (raw_dir / "falsa" / "a.json").read_bytes()
    [item] = lido(raw_dir)["arquivos"]
    assert item["fonte"] == "falsa" and item["arquivo"] == "a.json"
    assert item["sha256"] == hashlib.sha256(corpo).hexdigest()
    assert item["bytes"] == len(corpo)
    assert item["origem"] == "coleta"
    assert datetime.fromisoformat(item["coletado_em"]).utcoffset() is not None  # com fuso


def test_save_raw_do_mesmo_arquivo_atualiza_sem_duplicar(raw_dir):
    src = FonteFalsa()
    src.save_raw("a.json", {"x": 1})
    src.save_raw("b.json", {"y": 2})
    src.save_raw("a.json", {"x": 999})
    itens = {i["arquivo"]: i for i in lido(raw_dir)["arquivos"]}
    assert sorted(itens) == ["a.json", "b.json"]
    novo = (raw_dir / "falsa" / "a.json").read_bytes()
    assert itens["a.json"]["sha256"] == hashlib.sha256(novo).hexdigest()


def test_arquivo_baixado_e_registrado_com_registrar_raw(raw_dir):
    src = FonteFalsa()
    destino = src.raw_path("grande.zip")
    destino.write_bytes(b"conteudo" * 1000)
    src.registrar_raw("grande.zip")
    [item] = lido(raw_dir)["arquivos"]
    assert item["sha256"] == hashlib.sha256(b"conteudo" * 1000).hexdigest()
    assert item["bytes"] == 8000


def test_escrita_atomica_nao_deixa_manifesto_pela_metade(raw_dir, monkeypatch):
    FonteFalsa().save_raw("a.json", {"x": 1})
    antes = (raw_dir / "manifest.json").read_text(encoding="utf-8")

    def falha(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", falha)
    with pytest.raises(OSError):
        FonteFalsa().save_raw("b.json", {"y": 2})
    assert (raw_dir / "manifest.json").read_text(encoding="utf-8") == antes
    assert [p.name for p in raw_dir.iterdir() if p.name.startswith("manifest")] == ["manifest.json"]


def test_manifesto_corrompido_e_erro_claro_e_nao_e_sobrescrito(raw_dir):
    (raw_dir / "manifest.json").write_text("{ nao e json", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest.json"):
        FonteFalsa().save_raw("a.json", {"x": 1})
    assert (raw_dir / "manifest.json").read_text(encoding="utf-8") == "{ nao e json"


# --------------------------------------------------------------------------- verificação
def test_verificar_ok_quando_tudo_bate(raw_dir):
    FonteFalsa().save_raw("a.json", {"x": 1})
    assert manifest.verificar(raw_dir) == []


def test_verificar_aponta_arquivo_alterado_ausente_e_nao_registrado(raw_dir):
    src = FonteFalsa()
    src.save_raw("a.json", {"x": 1})
    src.save_raw("b.json", {"y": 2})
    (raw_dir / "falsa" / "a.json").write_text('{"x": 2}', encoding="utf-8")
    (raw_dir / "falsa" / "b.json").unlink()
    (raw_dir / "falsa" / "c.json").write_text("{}", encoding="utf-8")
    problemas = {(p.arquivo, p.tipo) for p in manifest.verificar(raw_dir)}
    assert problemas == {("falsa/a.json", "sha256_diferente"), ("falsa/b.json", "ausente"),
                         ("falsa/c.json", "nao_registrado")}


def test_verificar_sem_manifesto_gera_uma_linha_de_manifesto_ausente(raw_dir):
    (raw_dir / "falsa").mkdir()
    (raw_dir / "falsa" / "a.json").write_text("{}", encoding="utf-8")
    (raw_dir / "falsa" / "b.json").write_text("{}", encoding="utf-8")
    [p] = manifest.verificar(raw_dir)
    assert p.tipo == "manifesto_ausente"
    assert "--gerar-manifesto" in p.detalhe


def test_verificar_com_manifesto_existente_continua_acusando_arquivo_nao_registrado(raw_dir):
    FonteFalsa().save_raw("a.json", {"x": 1})
    (raw_dir / "falsa" / "solto.json").write_text("{}", encoding="utf-8")
    assert [(p.arquivo, p.tipo) for p in manifest.verificar(raw_dir)] == [
        ("falsa/solto.json", "nao_registrado")]


def test_verificar_pasta_inexistente_tambem_e_manifesto_ausente(tmp_path):
    assert [p.tipo for p in manifest.verificar(tmp_path / "nao_existe")] == ["manifesto_ausente"]


# --------------------------------------------------------------------------- pasta dos brutos
def test_save_raw_respeita_raio_x_raw(tmp_path, monkeypatch):
    destino = tmp_path / "outro_lugar"
    monkeypatch.setenv("RAIO_X_RAW", str(destino))
    FonteFalsa().save_raw("a.json", {"x": 1})
    assert (destino / "falsa" / "a.json").is_file()
    assert [i["arquivo"] for i in lido(destino)["arquivos"]] == ["a.json"]


def test_sem_raio_x_raw_o_padrao_continua_sendo_data_raw(raw_dir, monkeypatch):
    monkeypatch.delenv("RAIO_X_RAW", raising=False)
    FonteFalsa().save_raw("a.json", {"x": 1})
    assert (raw_dir / "falsa" / "a.json").is_file()  # raw_dir = RAW_DIR monkeypatchado
    assert (raw_dir / "manifest.json").is_file()


# --------------------------------------------------------------------------- retroativo
def test_manifesto_retroativo_marca_origem_e_nao_toca_nos_que_ja_existem(raw_dir):
    FonteFalsa().save_raw("novo.json", {"x": 1})
    (raw_dir / "falsa" / "velho.json").write_text('{"v": 1}', encoding="utf-8")
    (raw_dir / "outra").mkdir()
    (raw_dir / "outra" / "z.zip").write_bytes(b"zip")
    n = manifest.gerar_retroativo(raw_dir)
    assert n == 2
    itens = {(i["fonte"], i["arquivo"]): i for i in lido(raw_dir)["arquivos"]}
    assert itens[("falsa", "velho.json")]["origem"] == "retroativo"
    assert itens[("outra", "z.zip")]["origem"] == "retroativo"
    assert itens[("falsa", "novo.json")]["origem"] == "coleta"
    assert itens[("outra", "z.zip")]["sha256"] == hashlib.sha256(b"zip").hexdigest()
    assert manifest.verificar(raw_dir) == []
    assert manifest.gerar_retroativo(raw_dir) == 0  # idempotente


def test_retroativo_usa_a_data_de_modificacao_do_arquivo(raw_dir):
    (raw_dir / "falsa").mkdir()
    arq = raw_dir / "falsa" / "velho.json"
    arq.write_text("{}", encoding="utf-8")
    os.utime(arq, (1_700_000_000, 1_700_000_000))  # 2023-11-14T22:13:20Z
    manifest.gerar_retroativo(raw_dir)
    [item] = lido(raw_dir)["arquivos"]
    assert item["coletado_em"].startswith("2023-11-14T22:13:20")


# --------------------------------------------------------------------------- sha por fonte do fato
def test_sha_por_fonte_so_quando_ha_um_unico_arquivo_na_origem(raw_dir, monkeypatch):
    class UmArquivo(FonteFalsa):
        nome = "um"
        fontes_fato = ("fonte_um",)

    class DoisArquivos(FonteFalsa):
        nome = "dois"
        fontes_fato = ("fonte_dois_a", "fonte_dois_b")

    UmArquivo().save_raw("a.json", {"x": 1})
    DoisArquivos().save_raw("a.json", {"x": 1})
    DoisArquivos().save_raw("b.json", {"x": 2})
    monkeypatch.setattr(manifest, "_origens_por_fonte_fato",
                        lambda: {"fonte_um": "um", "fonte_dois_a": "dois", "fonte_dois_b": "dois"})
    sha = manifest.sha_por_fonte_fato(raw_dir)
    assert sha == {"fonte_um": hashlib.sha256((raw_dir / "um" / "a.json").read_bytes()).hexdigest()}


def test_sha_por_fonte_sem_manifesto_e_vazio(tmp_path):
    assert manifest.sha_por_fonte_fato(tmp_path) == {}
    assert manifest.sha_por_fonte_fato(tmp_path / "nao_existe") == {}


def test_toda_fonte_do_registro_declara_as_fontes_dos_fatos_que_produz():
    """`Fact.fonte` -> pasta de origem. Sem isso o hash do bruto não chega à evidência."""
    mapa = manifest._origens_por_fonte_fato()
    assert mapa["camara_api_v2"] == "camara" and mapa["camara_ceap"] == "ceap"
    assert mapa["cgu_ceis"] == mapa["cgu_cnep"] == mapa["cgu_emendas"] == "cgu"
    assert mapa["tse_consulta_cand"] == mapa["tse_prestacao_contas"] == "tse"
    assert mapa["tse_votacao_munzona"] == "tse"
    assert mapa["opensanctions_br_pep"] == "opensanctions" and mapa["brasilapi_cnpj"] == "rfb"
