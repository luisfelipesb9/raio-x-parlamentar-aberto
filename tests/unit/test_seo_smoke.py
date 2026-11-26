"""scripts/seo_smoke.py: as checagens não aceitam falso positivo e os processos morrem no fim."""
import os
import subprocess
import sys
import time

import pytest

from scripts import seo_smoke as smk
from scripts.seo_smoke import Resposta, canonical, h1_com, json_ld_valido

SITE = "https://exemplo.test"
NOME = smk.NOME_DEMO
LD_OK = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"Person",'
         f'"name":"{NOME}"}}</script>')

# Controle POSITIVO: o que um site com SSR de verdade entrega.
FICHA_BOA = (f'<html><head><title>{NOME} | Raio-X</title>'
             f'<link rel="canonical" href="{SITE}/deputado/9900001"/>{LD_OK}</head>'
             '<body><main><h1 class="t"><span>Alice Fict&iacute;cia</span> (demo)</h1></main></body></html>')
# Controle NEGATIVO: nome só no <title>, h1 de carregamento e JSON-LD vazio.
FICHA_FALSA = (f'<html><head><title>{NOME} | Raio-X</title><meta name="description" content="{NOME}">'
               '<script type="application/ld+json">{}</script></head>'
               f'<body><h1>Carregando…</h1><script>self.__next_f.push(["<h1>{NOME}</h1>"])</script></body></html>')


def _r(corpo, status=200):
    return Resposta(status, corpo)


def test_ficha_com_ssr_de_verdade_passa():
    r = _r(FICHA_BOA)
    assert h1_com(NOME)(r) == ""
    assert json_ld_valido(r) == ""
    assert canonical(f"{SITE}/deputado/9900001")(r) == ""


def test_ficha_falso_positivo_reprova_h1_e_json_ld():
    r = _r(FICHA_FALSA)
    assert "nenhum <h1> contém" in h1_com(NOME)(r)
    assert "schema.org" in json_ld_valido(r)


@pytest.mark.parametrize("corpo", [
    f"<html><head><title>{NOME}</title></head><body><p>{NOME}</p></body></html>",  # sem h1
    f"<html><body><script>document.write('<h1>{NOME}</h1>')</script></body></html>",  # h1 só em JS
    f"<html><head><h1>{NOME}</h1></head><body><h1>Outro</h1></body></html>",  # h1 fora do body
])
def test_nome_fora_de_h1_do_body_nao_conta(corpo):
    assert h1_com(NOME)(_r(corpo))


@pytest.mark.parametrize("bloco", ["{}", "[]", '"texto"', "{nao json", '{"@type":"Person"}',
                                   '{"@context":"https://schema.org"}',
                                   '{"@context":"https://exemplo.test/vocab","@type":"Person"}'])
def test_json_ld_sem_schema_org_tipado_reprova(bloco):
    assert json_ld_valido(_r(f'<script type="application/ld+json">{bloco}</script>'))


@pytest.mark.parametrize("bloco", [
    '{"@context":"https://schema.org","@type":"WebSite"}',
    '{"@context":"http://schema.org/","@type":"Person"}',
    '[{"@context":"https://schema.org","@type":"Person"}]',
    '{"@context":"https://schema.org","@graph":[{"@type":"WebSite"},{"@type":"Organization"}]}',
])
def test_json_ld_schema_org_tipado_passa(bloco):
    assert json_ld_valido(_r(f'<script type="application/ld+json">{bloco}</script>')) == ""


def test_json_ld_reprova_se_um_dos_blocos_for_invalido():
    assert "não é JSON" in json_ld_valido(_r(LD_OK + '<script type="application/ld+json">{x</script>'))


def test_canonical_para_localhost_reprova():
    r = _r('<link rel="canonical" href="http://localhost:3000/deputado/9900001">')
    assert "localhost" in canonical(f"{SITE}/deputado/9900001")(r)


def _site(paginas):
    return lambda url, timeout=30.0: paginas.get(url.removeprefix("http://site"), Resposta(404, "nao"))


PAGINAS_BOAS = {
    "/": _r(f"<html><head>{LD_OK}</head><body><h1>Raio-X</h1></body></html>"),
    "/deputado/9900001": _r(FICHA_BOA),
    "/deputados": _r('<html><body><a href="/deputado/9900001">Alice</a></body></html>'),
    "/robots.txt": _r(f"User-agent: GPTBot\nAllow: /\nSitemap: {SITE}/sitemap.xml\n"),
    "/sitemap.xml": _r(f"<urlset><url><loc>{SITE}/deputado/9900001</loc></url></urlset>"),
    "/llms.txt": _r("# Raio-X Parlamentar\n"),
}


def test_controle_positivo_passa_tudo(monkeypatch, capsys):
    monkeypatch.setattr(smk, "buscar", _site(PAGINAS_BOAS))
    assert smk.rodar_checagens("http://site", SITE) == 0
    assert "FALHA" not in capsys.readouterr().out


def test_controle_negativo_reprova_exatamente_o_falso_positivo(monkeypatch, capsys):
    paginas = {**PAGINAS_BOAS, "/deputado/9900001": _r(FICHA_FALSA),
               "/deputados": _r('<a href="/deputado/">lista vazia</a>')}
    monkeypatch.setattr(smk, "buscar", _site(paginas))
    assert smk.rodar_checagens("http://site", SITE) == 4  # h1, canonical, JSON-LD e link da ficha demo
    falhas = [x for x in capsys.readouterr().out.splitlines() if x.startswith("FALHA")]
    assert len(falhas) == 4 and all("ficha demo" in x or "lista" in x for x in falhas)


posix = pytest.mark.skipif(sys.platform == "win32", reason="grupos de processo POSIX")


@posix
def test_matar_grupo_mata_o_filho_mesmo_se_o_lider_ja_saiu():
    p = subprocess.Popen(["sh", "-c", "sleep 30 & exit 0"], start_new_session=True)
    p.wait(timeout=5)  # o líder saiu; o sleep segue vivo no grupo
    assert smk._grupo_vivo(p.pid)
    smk.matar_grupo(p, espera=2)
    assert not smk._grupo_vivo(p.pid)


@posix
def test_build_com_timeout_e_interrompido_e_nao_deixa_processo(tmp_path):
    pid_neto = tmp_path / "neto.pid"
    inicio = time.monotonic()
    with pytest.raises(smk.ErroHarness, match="passou de"):
        smk.rodar_com_timeout(["sh", "-c", f"sleep 30 & echo $! > {pid_neto}; sleep 30"], tmp_path,
                              dict(os.environ), timeout=1)
    assert time.monotonic() - inicio < 10
    with pytest.raises(ProcessLookupError):  # o filho em segundo plano também morreu
        os.kill(int(pid_neto.read_text()), 0)
