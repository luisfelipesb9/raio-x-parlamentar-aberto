"""Teste de escala SINTÉTICO da ADR-011: replica a amostra de 20 deputados até simular 513 e mede o
banco público enxuto e a partida a frio da API, contra o caminho antigo (snapshot de todos os fatos).

NADA aqui é dado real: as réplicas têm chaves e ids distintos, nome com o rótulo "SINTÉTICO k" e vivem
só no diretório de saída (fora do repositório). A densidade por deputado é a da amostra de MG (CEAP de
2024, 1 trimestre de votos); o dado nacional de verdade terá outra distribuição. Serve para medir ordem
de grandeza (arquivo, RAM, partida a frio) e acionar, ou não, o gatilho do plano B da ADR-011.

Uso:
  RAIO_X_ID_SALT=teste uv run python -m scripts.escala_sintetica --base COPIA_DA_BASE_PUBLICA.duckdb \\
      --saida /tmp/escala [--copias 25.65]

`--base` é só lido (copie o arquivo antes). Gatilho do plano B: arquivo > 80 MB, RAM > 1 GB ou partida
a frio > 10 s no caminho novo.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import resource
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from contracts import Fact
from engine import forward
from engine.factbase import FactBase
from engine.rules import load_rules
from repo.links import EntityLink
from repo.store import Store

ROTULO = "SINTÉTICO"
COPIAS_PADRAO = 513 / 20  # 25,65: a amostra tem 20 deputados
# Cada deputado tem os seus; votações, proposições e PEP são do mundo e não se repetem (513 deputados votam
# nas mesmas votações). Empresas, sócios e sanções também são replicados, com CNPJ novo por réplica: o pior
# caso para o grafo (cada deputado com fornecedores próprios, sem nó de empresa compartilhado).
POR_REPLICA = ("deputado", "candidatura", "voto", "despesa_ceap", "doacao", "emenda", "autoria",
               "votos_municipio")
POR_REPLICA_EMPRESA = ("empresa", "socio", "sancao")  # sem dono: entram por fração da réplica
COMPARTILHADOS = ("votacao", "proposicao", "pep")
LIMITE_ARQUIVO_MB, LIMITE_RAM_MB, LIMITE_PARTIDA_S = 80, 1024, 10.0  # gatilho do plano B (ADR-011)


def _dep(valor: str, k: int) -> str:
    return valor if k == 0 else str(int(valor) + k * 1_000_000)


def _sq(valor: str, k: int) -> str:
    return valor if k == 0 else f"{valor}{k:02d}"


def _suf(valor: str, k: int) -> str:
    return valor if k == 0 else f"{valor}~{k}"


def _cnpj(valor: str, k: int) -> str:
    """CNPJ da réplica `k`: troca os 4 dígitos da ordem do estabelecimento (sem validar o DV)."""
    d = re.sub(r"\D", "", str(valor))
    if k == 0 or len(d) != 14 or "*" in str(valor):
        return valor
    return d[:8] + f"{(int(d[8:12]) + k * 100) % 10000:04d}" + d[12:]


def _dono(f: Fact, sq_dep: dict[str, str]) -> str | None:
    """Deputado a quem o fato pertence (id original), ou None se não dá para saber."""
    if f.tipo == "deputado":
        return f.chave
    if f.tipo in ("doacao", "votos_municipio"):
        return sq_dep.get(str(f.atributos.get("sq_candidato")))
    dono = f.atributos.get("deputado_id")
    return str(dono) if dono else None


def _copiar(f: Fact, k: int) -> Fact:
    """Cópia da réplica `k` do fato `f` (de um tipo em POR_REPLICA) com chaves e referências novas."""
    at = dict(f.atributos)
    chave, id_oficial = f.chave, f.id_oficial
    if f.tipo == "deputado":
        chave = id_oficial = _dep(f.chave, k)
        at["nome"] = f"{at.get('nome') or 'Deputado'} [{ROTULO} {k}]"
    elif f.tipo == "candidatura":
        chave = id_oficial = _sq(f.chave, k)
        at["deputado_id"] = _dep(str(at["deputado_id"]), k)
    elif f.tipo == "voto":
        at["deputado_id"] = _dep(str(at["deputado_id"]), k)
        chave = f"{at['votacao_id']}:{at['deputado_id']}"
    elif f.tipo in ("despesa_ceap", "emenda"):
        at["deputado_id"] = _dep(str(at["deputado_id"]), k)
        if at.get("cnpj"):
            at["cnpj"] = _cnpj(at["cnpj"], k)
        chave, id_oficial = _suf(f.chave, k), _suf(f.id_oficial, k)
    elif f.tipo == "empresa":
        chave = id_oficial = _cnpj(f.chave, k)
    elif f.tipo == "socio":
        antigo = str(at["cnpj"])
        at["cnpj"] = _cnpj(antigo, k)
        chave = at["cnpj"] + f.chave[len(antigo):] if f.chave.startswith(antigo) else _suf(f.chave, k)
        id_oficial = (at["cnpj"] + f.id_oficial[len(antigo):] if f.id_oficial.startswith(antigo)
                      else _suf(f.id_oficial, k))
    elif f.tipo == "sancao":
        if at.get("cnpj"):
            at["cnpj"] = _cnpj(at["cnpj"], k)
        chave, id_oficial = _suf(f.chave, k), _suf(f.id_oficial, k)
    elif f.tipo == "doacao":
        if at.get("tipo_doador") == "PJ" and at.get("doador_cpf_cnpj"):
            at["doador_cpf_cnpj"] = _cnpj(str(at["doador_cpf_cnpj"]), k)
        at["sq_candidato"] = _sq(str(at["sq_candidato"]), k)
        chave, id_oficial = _suf(f.chave, k), _suf(f.id_oficial, k)
    elif f.tipo == "autoria":
        at["deputado_id"] = _dep(str(at["deputado_id"]), k)
        chave = f"{at['proposicao_id']}:{at['deputado_id']}:{at.get('papel')}"
    elif f.tipo == "votos_municipio":
        antigo = str(at["sq_candidato"])
        at["sq_candidato"] = _sq(antigo, k)
        chave = f"{at.get('ano')}:{at['sq_candidato']}:{at.get('municipio_ibge')}"
        id_oficial = (_sq(antigo, k) + id_oficial[len(antigo):] if id_oficial.startswith(antigo)
                      else _suf(id_oficial, k))
    return f.model_copy(update={"chave": chave, "id_oficial": id_oficial, "atributos": at})


def _plano(n_deputados: int, copias: float) -> tuple[int, int]:
    """(número de réplicas incluindo a original, deputados da última)."""
    if copias < 1:
        raise ValueError("copias deve ser >= 1 (a amostra original sempre entra)")
    total = round(n_deputados * copias)
    n_rep = math.ceil(total / n_deputados)
    return n_rep, total - (n_rep - 1) * n_deputados


def replicar(fatos: Sequence[Fact], copias: float = COPIAS_PADRAO) -> list[Fact]:
    """A amostra original (intacta) + réplicas dos fatos por deputado, até `copias` x os deputados.
    A última réplica pode ser parcial (os primeiros deputados por id), para fechar o total exato."""
    deputados = sorted(f.chave for f in fatos if f.tipo == "deputado")
    n_rep, resto = _plano(len(deputados), copias)
    sq_dep = {c.chave: str(c.atributos["deputado_id"]) for c in fatos
              if c.tipo == "candidatura" and c.atributos.get("deputado_id")}
    saida = list(fatos)
    for k in range(1, n_rep):
        escolhidos = set(deputados if k < n_rep - 1 else deputados[:resto])
        saida += [_copiar(f, k) for f in fatos
                  if f.tipo in POR_REPLICA and _dono(f, sq_dep) in escolhidos]
        for tipo in POR_REPLICA_EMPRESA:  # a última réplica leva a fração proporcional aos deputados
            lista = [f for f in fatos if f.tipo == tipo]
            if k == n_rep - 1:
                lista = lista[:round(len(lista) * resto / len(deputados))]
            saida += [_copiar(f, k) for f in lista]
    return saida


def _ref(ref: str, k: int) -> str:
    tipo, _, chave = ref.partition(":")
    novo = {"deputado": _dep, "candidatura": _sq, "despesa_ceap": _suf, "doacao": _suf,
            "emenda": _suf, "empresa": _cnpj, "sancao": _suf}.get(tipo)
    return f"{tipo}:{novo(chave, k)}" if novo else ref


def replicar_links(links: Sequence[EntityLink], copias: float, deputados: int | None = None,
                   existentes: set[str] | None = None) -> list[EntityLink]:
    """Os links originais + os das réplicas (pontas renomeadas como em `replicar`). Com `existentes`
    (conjunto de "tipo:chave" dos fatos), só ficam os links cujas duas pontas existem."""
    n_rep = math.ceil(copias)
    saida = list(links)
    for k in range(1, n_rep):
        saida += [lk._replace(origem=_ref(lk.origem, k), destino=_ref(lk.destino, k)) for lk in links]
    if existentes is not None:
        saida = [lk for lk in saida if lk.origem in existentes and lk.destino in existentes]
    return saida


def gerar_origem(fatos: Sequence[Fact], links: Sequence[EntityLink], destino: Path, *,
                 copias: float = COPIAS_PADRAO, log: Callable[[str], None] = print) -> dict:
    """Grava no `destino` o banco de trabalho SINTÉTICO (todos os fatos, links e findings do motor)."""
    destino = Path(destino)
    for sufixo in ("", ".wal"):
        Path(f"{destino}{sufixo}").unlink(missing_ok=True)
    t0 = time.perf_counter()
    todos = replicar(fatos, copias)
    existentes = {f"{f.tipo}:{f.chave}" for f in todos}
    todos_links = replicar_links(links, copias, existentes=existentes)
    n_dep = sum(1 for f in todos if f.tipo == "deputado")
    log(f"SINTÉTICO: {len(todos)} fatos, {n_dep} deputados e {len(todos_links)} links gerados por "
        f"replicação da amostra (x{copias}) em {time.perf_counter() - t0:.1f}s")
    store = Store(destino)
    try:
        store.upsert_facts(todos)
        store.upsert_links(todos_links)
        t1 = time.perf_counter()
        res = forward.run(FactBase(todos), load_rules())
        store.save_findings(res.findings, res.explanations)
        log(f"SINTÉTICO: motor sobre os fatos sintéticos: {len(res.findings)} findings em "
            f"{time.perf_counter() - t1:.1f}s; origem sintética em {destino}")
    finally:
        store.con.close()
    return {"deputados": n_dep, "fatos": len(todos), "findings": len(res.findings),
            "links": len(todos_links)}


# ---------------------------------------------------------------------------------- medições
_RSS = re.compile(r"(\d+)\s+maximum resident set size")
_REAL = re.compile(r"([\d.]+)\s+real")


def _com_time(cmd: list[str], env: dict[str, str]) -> tuple[subprocess.CompletedProcess, float, float]:
    """Roda `cmd` sob `/usr/bin/time -l`; devolve (processo, pico de RSS em MB, tempo real em s)."""
    r = subprocess.run(["/usr/bin/time", "-l", *cmd], check=False, capture_output=True, text=True,
                       env=env)
    rss = _RSS.search(r.stderr)
    real = _REAL.search(r.stderr)
    # macOS informa bytes; Linux (`time -v` seria outro formato) não é suportado aqui
    return r, (int(rss.group(1)) / 1e6 if rss else float("nan")), float(real.group(1)) if real else float("nan")


def partida(db: Path) -> dict:
    """Roda NESTE processo: tempo da primeira chamada a /deputados e /grafo (partida a frio)."""
    t0 = time.perf_counter()
    from fastapi.testclient import TestClient

    from api.main import create_app
    t_import = time.perf_counter() - t0
    with TestClient(create_app(db)) as c:
        t1 = time.perf_counter()
        deps = c.get("/deputados", params={"page_size": 100}).json()
        t2 = time.perf_counter()
        centro = f"deputado:{deps['items'][0]['id']}"
        grafo = c.get("/grafo", params={"centro": centro, "profundidade": 2})
        t3 = time.perf_counter()
        c.get("/deputados", params={"page_size": 100})
        t4 = time.perf_counter()
        c.get("/perguntar", params={"deputado": deps["items"][0]["id"], "objetivo": "risco_integridade"})
        t5 = time.perf_counter()
        c.get("/comparar", params={"a": deps["items"][0]["id"], "b": deps["items"][1]["id"]})
        t6 = time.perf_counter()
    return {"import_s": round(t_import, 2), "deputados_1a_chamada_s": round(t2 - t1, 2),
            "grafo_2a_chamada_s": round(t3 - t2, 2), "deputados_quente_s": round(t4 - t3, 3),
            "perguntar_s": round(t5 - t4, 2), "comparar_s": round(t6 - t5, 2),
            "partida_total_s": round(t3 - t1, 2),
            "n_deputados": deps["total"], "grafo_http": grafo.status_code,
            "rss_proprio_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 1)}


def _medir_partida(db: Path, env: dict[str, str], rodadas: int = 3) -> dict:
    """`rodadas` processos novos (partida a frio de verdade a cada um); vale a rodada de mediana do
    tempo de partida e o MAIOR pico de memória; todas ficam em `rodadas`."""
    todas = []
    for _ in range(rodadas):
        r, rss, _ = _com_time([sys.executable, "-m", "scripts.escala_sintetica", "partida", "--db",
                               str(db)], env)
        if r.returncode != 0:
            raise RuntimeError(f"a partida falhou:\n{r.stderr[-800:]}")
        todas.append({**json.loads(r.stdout.strip().splitlines()[-1]), "pico_rss_mb": round(rss, 1)})
    mediana = sorted(todas, key=lambda x: x["partida_total_s"])[len(todas) // 2]
    return {**mediana, "pico_rss_mb": max(x["pico_rss_mb"] for x in todas),
            "partida_total_s_rodadas": [x["partida_total_s"] for x in todas]}


def medir(base: Path, saida: Path, copias: float, log: Callable[[str], None] = print) -> dict:
    saida.mkdir(parents=True, exist_ok=True)
    env = {**os.environ}
    origem, publico = saida / "sintetico_origem.duckdb", saida / "sintetico_publico.duckdb"
    publico.unlink(missing_ok=True)
    src = Store(base, read_only=True)
    try:
        fatos, links = src.load_facts(), src.load_links()
    finally:
        src.con.close()
    log(f"SINTÉTICO: base real lida só para replicar ({len(fatos)} fatos); nada do que segue é dado real")
    gerado = gerar_origem(fatos, links, origem, copias=copias, log=log)
    del fatos, links

    log("SINTÉTICO: publicando (python -m publicar) sob /usr/bin/time -l ...")
    p, rss_pub, real_pub = _com_time([sys.executable, "-m", "publicar", "--origem", str(origem),
                                      "--destino", str(publico)], env)
    if p.returncode != 0:
        raise RuntimeError(f"publicar falhou:\n{p.stderr[-800:]}")
    log(f"SINTÉTICO: {p.stdout.strip()}")
    novo = _medir_partida(publico, {**env, "RAIO_X_DB": str(publico)})
    antigo = _medir_partida(origem, {**env, "RAIO_X_DB": str(origem)})
    mb_publico = publico.stat().st_size / 1e6
    resultado = {
        "rotulo": f"{ROTULO}: replicação da amostra de 20 deputados, não são dados reais",
        "copias": copias, **gerado,
        "arquivo_origem_mb": round(origem.stat().st_size / 1e6, 1),
        "arquivo_publico_mb": round(mb_publico, 1),
        "publicar": {"pico_rss_mb": round(rss_pub, 1), "tempo_s": real_pub},
        "partida_nova": novo, "partida_antiga": antigo}
    estouros = []
    if mb_publico > LIMITE_ARQUIVO_MB:
        estouros.append(f"arquivo público {mb_publico:.1f} MB > {LIMITE_ARQUIVO_MB} MB")
    if novo["pico_rss_mb"] > LIMITE_RAM_MB:
        estouros.append(f"RAM da API {novo['pico_rss_mb']:.0f} MB > {LIMITE_RAM_MB} MB")
    if novo["partida_total_s"] > LIMITE_PARTIDA_S:
        estouros.append(f"partida a frio {novo['partida_total_s']} s > {LIMITE_PARTIDA_S:.0f} s")
    resultado["gatilho_plano_b"] = estouros or None
    (saida / "resultado_sintetico.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")
    log("SINTÉTICO: " + ("GATILHO DO PLANO B ACIONADO: " + "; ".join(estouros) if estouros
                         else "nenhum gatilho do plano B acionado"))
    return resultado


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("partida", help="(interno) mede a partida a frio da API neste processo")
    p.add_argument("--db", type=Path, required=True)
    ap.add_argument("--base", type=Path, help="cópia da base pública real da amostra (só leitura)")
    ap.add_argument("--saida", type=Path, help="diretório de trabalho (fora do repositório)")
    ap.add_argument("--copias", type=float, default=COPIAS_PADRAO,
                    help="quantas vezes replicar a amostra (padrão 25,65 = 513 deputados)")
    a = ap.parse_args(argv)
    if a.cmd == "partida":
        print(json.dumps(partida(a.db)))
        return
    if not a.base or not a.saida:
        ap.error("informe --base e --saida")
    print(json.dumps(medir(a.base, a.saida, a.copias), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
