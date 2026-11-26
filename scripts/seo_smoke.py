"""Smoke de SEO SEM JavaScript: o que um buscador ou robô de IA recebe no primeiro GET.

Sobe a API sobre o banco de DEMONSTRAÇÃO FICTÍCIO (`make seed-demo`) e o site em modo produção
(`next start`), faz pedidos HTTP simples (sem navegador, sem executar JS) e confere:

  - /deputado/9900001: 200, `<h1`, nome do deputado de demo no HTML, `rel="canonical"` apontando
    para o endereço público, JSON-LD válido;
  - /deputado/99999999: 404 de verdade (não 200 com "não encontrado");
  - /deputados: lista as fichas com `href="/deputado/`;
  - /robots.txt: cita GPTBot e tem `Sitemap:`;
  - /sitemap.xml: lista a ficha demo com o endereço público;
  - /llms.txt: 200;
  - home: JSON-LD válido.

Imprime OK/FALHA por checagem e sai com 1 se alguma falhar (2 se não conseguiu nem subir os
serviços). Mata os processos que iniciou ao terminar, inclusive em Ctrl+C. Só biblioteca padrão.
Só roda em sistemas POSIX (Linux/macOS).

Uso (na raiz do repositório, depois de `make seed-demo` e `pnpm --dir web install`):
    uv run python -m scripts.seo_smoke --build                 # sobe API e site, constrói e confere
    uv run python -m scripts.seo_smoke --api-porta 8103 --site-porta 3103 --build
    uv run python -m scripts.seo_smoke --so-checar https://preview.exemplo.test   # site já no ar
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RAIZ = Path(__file__).resolve().parents[1]
DB_DEMO = "data/sample/raio_x_demo.duckdb"
SAL_DEMO = "sal-fixo-da-demonstracao"  # sal PÚBLICO, só da demo fictícia (o de scripts/seed_demo.py)
ID_DEMO = "9900001"
NOME_DEMO = "Alice Fictícia (demo)"
ID_INEXISTENTE = "99999999"
SITE_PUBLICO = "https://exemplo.test"
AGENTE = "raio-x-seo-smoke/1.0 (sem JavaScript)"

_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.IGNORECASE | re.DOTALL)
_LD_JSON = re.compile(r"""<script\b[^>]*type=["']application/ld\+json["'][^>]*>(.*?)</script\s*>""",
                      re.IGNORECASE | re.DOTALL)
_LINK = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_ATRIBUTO = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")


@dataclass(frozen=True)
class Resposta:
    status: int  # 0 = sem resposta HTTP (conexão recusada, timeout...)
    corpo: str
    erro: str = ""


def buscar(url: str, timeout: float = 30.0) -> Resposta:
    """GET simples, como um robô: sem JS, sem cookies. 4xx/5xx viram Resposta, não exceção."""
    req = Request(url, headers={"User-Agent": AGENTE, "Accept": "text/html,application/xml,text/plain,*/*"})
    try:
        with urlopen(req, timeout=timeout) as r:
            return Resposta(r.status, r.read().decode("utf-8", "replace"))
    except HTTPError as e:
        return Resposta(e.code, e.read().decode("utf-8", "replace"))
    except (URLError, TimeoutError, ConnectionError, OSError) as e:
        return Resposta(0, "", str(getattr(e, "reason", e)))


# ---------- checagens (puras: recebem a Resposta e dizem o motivo da falha, ou "" se ok) ----------

Checagem = Callable[[Resposta], str]


def _html_sem_script(corpo: str) -> str:
    return html.unescape(_SCRIPT.sub("", corpo))


def status(esperado: int) -> Checagem:
    def f(r: Resposta) -> str:
        if r.status == esperado:
            return ""
        return f"sem resposta HTTP ({r.erro})" if r.status == 0 else f"status {r.status}, esperado {esperado}"
    return f


def contem(trecho: str, *, fora_de_script: bool = False) -> Checagem:
    def f(r: Resposta) -> str:
        alvo = _html_sem_script(r.corpo) if fora_de_script else r.corpo
        if trecho in alvo:
            return ""
        onde = " fora de <script> (o texto só existe se o JS rodar)" if fora_de_script else ""
        return f"não contém {trecho!r}{onde}"
    return f


def canonical(esperado: str) -> Checagem:
    def f(r: Resposta) -> str:
        hrefs = []
        for tag in _LINK.findall(r.corpo):
            attrs = {m[0].lower(): m[1] or m[2] for m in _ATRIBUTO.findall(tag)}
            if attrs.get("rel", "").lower() == "canonical":
                hrefs.append(html.unescape(attrs.get("href", "")))
        if not hrefs:
            return 'sem <link rel="canonical">'
        if esperado not in hrefs:
            return f"canonical aponta para {hrefs}, esperado {esperado!r}"
        return ""
    return f


def json_ld_valido(r: Resposta) -> str:
    blocos = _LD_JSON.findall(r.corpo)
    if not blocos:
        return 'sem <script type="application/ld+json">'
    for i, bloco in enumerate(blocos, 1):
        try:
            json.loads(bloco)
        except json.JSONDecodeError as e:
            return f"bloco JSON-LD {i} não é JSON válido ({e.msg})"
    return ""


def nao_vazio(r: Resposta) -> str:
    if r.status != 200:  # a página de erro também tem corpo: não conta
        return f"sem conteúdo próprio (status {r.status})"
    return "" if r.corpo.strip() else "corpo vazio"


def checagens(site_publico: str) -> list[tuple[str, str, list[tuple[str, Checagem]]]]:
    """(rótulo, caminho, [(descrição, checagem)]). A primeira de cada página é o status."""
    ficha = f"/deputado/{ID_DEMO}"
    return [
        ("ficha demo", ficha, [
            ("status 200", status(200)),
            ("tem <h1 no HTML", contem("<h1", fora_de_script=True)),
            (f"nome {NOME_DEMO!r} no HTML", contem(NOME_DEMO, fora_de_script=True)),
            ('rel="canonical" com o endereço público', canonical(f"{site_publico}{ficha}")),
            ("JSON-LD (application/ld+json) válido", json_ld_valido),
        ]),
        ("ficha inexistente", f"/deputado/{ID_INEXISTENTE}", [("status 404", status(404))]),
        ("lista de deputados", "/deputados", [
            ("status 200", status(200)),
            ('links href="/deputado/ no HTML', contem('href="/deputado/', fora_de_script=True)),
        ]),
        ("robots.txt", "/robots.txt", [
            ("status 200", status(200)),
            ("cita GPTBot", contem("GPTBot")),
            ("tem Sitemap:", contem("Sitemap:")),
        ]),
        ("sitemap.xml", "/sitemap.xml", [
            ("status 200", status(200)),
            ("lista a ficha demo com o endereço público", contem(f"{site_publico}{ficha}")),
        ]),
        ("llms.txt", "/llms.txt", [("status 200", status(200)), ("não vazio", nao_vazio)]),
        ("home", "/", [("status 200", status(200)), ("JSON-LD (application/ld+json) válido", json_ld_valido)]),
    ]


def rodar_checagens(base: str, site_publico: str) -> int:
    """Roda tudo contra `base` e devolve quantas checagens falharam."""
    falhas = total = 0
    for rotulo, caminho, itens in checagens(site_publico):
        r = buscar(base + caminho)
        for desc, chk in itens:
            total += 1
            motivo = chk(r)
            if motivo:
                falhas += 1
                print(f"FALHA  {rotulo} ({caminho}): {desc} — {motivo}")
            else:
                print(f"OK     {rotulo} ({caminho}): {desc}")
    print(f"\nseo-smoke: {total - falhas}/{total} checagens OK" + (f", {falhas} FALHA(S)" if falhas else ""))
    return falhas


# ---------- processos ----------

class ErroHarness(RuntimeError):
    """Não deu para subir API/site: não é falha de SEO, é do ambiente."""


def porta_ocupada(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def esperar(url: str, timeout: float, pronto: Callable[[Resposta], bool], proc: subprocess.Popen,
            nome: str, log: Path) -> None:
    fim = time.monotonic() + timeout
    while time.monotonic() < fim:
        if proc.poll() is not None:
            raise ErroHarness(f"{nome} saiu com código {proc.returncode} antes de ficar pronto.\n{_cauda(log)}")
        if pronto(buscar(url, timeout=5)):
            print(f"[seo-smoke] {nome} pronto em {url}")
            return
        time.sleep(1)
    raise ErroHarness(f"{nome} não ficou pronto em {timeout:.0f}s ({url}).\n{_cauda(log)}")


def _cauda(log: Path, linhas: int = 30) -> str:
    try:
        texto = log.read_text(encoding="utf-8", errors="replace").splitlines()[-linhas:]
    except OSError:
        return ""
    return f"--- últimas linhas de {log} ---\n" + "\n".join(texto)


class Processos:
    """Inicia processos em grupo próprio e mata o grupo inteiro no fim (pnpm → next → workers)."""

    def __init__(self, pasta_logs: Path):
        self.pasta = pasta_logs
        self.procs: list[tuple[str, subprocess.Popen]] = []

    def iniciar(self, nome: str, cmd: list[str], cwd: Path, env: dict[str, str]) -> tuple[subprocess.Popen, Path]:
        log = self.pasta / f"{nome}.log"
        arq = log.open("wb")
        print(f"[seo-smoke] iniciando {nome}: {' '.join(cmd)} (log: {log})")
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=arq, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        arq.close()
        self.procs.append((nome, p))
        return p, log

    def encerrar(self) -> None:
        for nome, p in reversed(self.procs):
            if p.poll() is not None:
                continue
            try:
                os.killpg(p.pid, signal.SIGTERM)
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait(timeout=5)
            except ProcessLookupError:
                pass
            print(f"[seo-smoke] {nome} encerrado")
        self.procs.clear()


def _sinal_para_saida(signum, _frame):  # SIGTERM do CI vira SystemExit: o finally mata os filhos
    raise SystemExit(128 + signum)


def subir_e_checar(a: argparse.Namespace) -> int:
    raiz = Path(a.raiz).resolve()
    db = raiz / a.db
    if not db.exists():
        raise ErroHarness(f"banco da demo não encontrado em {db}: rode `make seed-demo` antes.")
    pnpm = shutil.which("pnpm")
    if not pnpm:
        raise ErroHarness("pnpm não encontrado no PATH.")
    for porta in (a.api_porta, a.site_porta):
        if porta_ocupada(porta):
            raise ErroHarness(f"a porta {porta} já está em uso: pare o que está nela ou escolha outra "
                              "(--api-porta/--site-porta); o smoke não testa servidor alheio.")
    api = f"http://127.0.0.1:{a.api_porta}"
    site = f"http://127.0.0.1:{a.site_porta}"
    env_api = {**os.environ, "RAIO_X_ID_SALT": SAL_DEMO, "RAIO_X_DB": str(db)}
    env_web = {**os.environ, "API_URL": api, "NEXT_PUBLIC_API_URL": api,
               "NEXT_PUBLIC_SITE_URL": a.site_publico, "NEXT_TELEMETRY_DISABLED": "1"}

    procs = Processos(Path(tempfile.mkdtemp(prefix="seo-smoke-")))
    try:
        p_api, log_api = procs.iniciar(
            "api", [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1",
                    "--port", str(a.api_porta)], raiz, env_api)
        esperar(f"{api}/deputados?page_size=1", a.timeout, lambda r: r.status == 200, p_api, "API", log_api)
        if a.build:  # com a API no ar: páginas pré-renderizadas no build podem consultá-la
            print("[seo-smoke] pnpm build")
            if subprocess.run([pnpm, "build"], check=False, cwd=raiz / "web", env=env_web).returncode != 0:
                raise ErroHarness("pnpm build falhou.")
        p_web, log_web = procs.iniciar(
            "site", [pnpm, "exec", "next", "start", "-H", "127.0.0.1", "-p", str(a.site_porta)],
            raiz / "web", env_web)
        esperar(f"{site}/", a.timeout, lambda r: r.status != 0, p_web, "site", log_web)
        print()
        return 1 if rodar_checagens(site, a.site_publico) else 0
    finally:
        procs.encerrar()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raiz", default=str(RAIZ), help="raiz do repositório")
    ap.add_argument("--db", default=DB_DEMO, help="banco (relativo à raiz); padrão: o da demo fictícia")
    ap.add_argument("--api-porta", type=int, default=8000)
    ap.add_argument("--site-porta", type=int, default=3000)
    ap.add_argument("--site-publico", default=SITE_PUBLICO,
                    help="NEXT_PUBLIC_SITE_URL esperado no canonical e no sitemap")
    ap.add_argument("--build", action="store_true", help="roda `pnpm build` (com a API no ar) antes de subir o site")
    ap.add_argument("--timeout", type=float, default=120.0, help="segundos para API e site ficarem prontos")
    ap.add_argument("--so-checar", metavar="URL",
                    help="não sobe nada: confere um site já no ar (o banco precisa ter a ficha demo)")
    a = ap.parse_args(argv)
    a.site_publico = a.site_publico.rstrip("/")
    if hasattr(sys.stdout, "reconfigure"):  # mensagens em ordem com a saída do pnpm build no log do CI
        sys.stdout.reconfigure(line_buffering=True)
    if a.so_checar:
        return 1 if rodar_checagens(a.so_checar.rstrip("/"), a.site_publico) else 0
    signal.signal(signal.SIGTERM, _sinal_para_saida)
    try:
        return subir_e_checar(a)
    except ErroHarness as e:
        print(f"ERRO (ambiente, não SEO): {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
