"""Verificação independente: recalcula, direto dos brutos, o que o banco e o motor afirmam.

Uso: python -m scripts.verifica [--db BANCO] [--raw PASTA] [--saida ARQUIVO.md]
                                [--gerar-manifesto] [--online] [--amostra-online N] [--semente S]

O que confere (tolerância zero para contagens; até 1 centavo para valores em reais):
  1. votações: total, nominais e com orientação Sim/Não do JSON bruto da Câmara x banco;
  2. governismo: por deputado do banco, nº de votos válidos e taxa recalculados do JSON bruto x
     banco (SQL) x finding da R01 (o motor), inclusive a decisão de disparar ou não;
  3. CEAP: por deputado do banco, nº de despesas e total do bruto (zip oficial) x banco;
  4. manifesto: o sha256 de cada arquivo de data/raw bate com data/raw/manifest.json;
  5. (opcional, --online) contagem de votos de votações sorteadas direto na API da Câmara.

Independência: este módulo não importa o motor (engine), o grafo nem a API. Os limiares da R01 vêm
do YAML da regra, para conferir que o motor aplica o que a regra declara. Lê o leitor de JSON em
streaming da fonte CEAP (`iterar_dados`), que só percorre o arquivo; filtro e soma são daqui.

Código de saída: 0 sem divergência; 1 com divergência. "Não verificado" não é aprovação: aparece
na tabela e no relatório, e não vira "ok".
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import IO, Any

import httpx
import yaml

from repo.store import Store
from sources import manifest
from sources.ceap.source import iterar_dados

RAIZ = Path(__file__).resolve().parent.parent
RELATORIO = RAIZ / "docs" / "relatorio" / "verificacao.md"
REGRA_R01 = RAIZ / "knowledge" / "rules" / "R01_governismo.yaml"
BASE_CAMARA = "https://dadosabertos.camara.leg.br/api/v2"
TOLERANCIA_CENTAVOS = 1

OK, DIVERGE, NAO_VERIFICADO = "ok", "diverge", "nao_verificado"
ROTULO_STATUS = {OK: "ok", DIVERGE: "DIVERGE", NAO_VERIFICADO: "não verificado"}
TITULOS = {"votacoes": "Votações", "governismo": "Governismo (R01)", "ceap": "Despesas CEAP",
           "manifesto": "Manifesto do bruto", "online": "Conferência na API da Câmara"}


@dataclass
class Linha:
    verificacao: str  # votacoes | governismo | ceap | manifesto | online
    item: str
    esperado: str  # o que o bruto diz
    obtido: str  # o que o banco/motor diz
    status: str
    detalhe: str = ""


@dataclass
class Resultado:
    linhas: list[Linha] = field(default_factory=list)
    manifesto_gerado: int = 0
    n_deputados: int = 0
    banco: str = ""
    pasta_raw: str = ""
    avisos: list[str] = field(default_factory=list)  # não reprovam, mas o leitor precisa saber

    @property
    def divergencias(self) -> int:
        return sum(1 for lin in self.linhas if lin.status == DIVERGE)

    @property
    def nao_verificados(self) -> int:
        return sum(1 for lin in self.linhas if lin.status == NAO_VERIFICADO)


@dataclass
class Governismo:
    n: int = 0
    convergentes: int = 0

    @property
    def taxa(self) -> float | None:
        return round(self.convergentes / self.n, 3) if self.n else None


# --------------------------------------------------------------------------- cálculo sobre o bruto
def votacoes_do_bruto(raw: dict[str, Any]) -> dict[str, int]:
    """Totais das votações no JSON da Câmara: nominal = tem voto individual no bruto."""
    vs = raw.get("votacoes", [])
    return {
        "votações": len(vs),
        "votações nominais": sum(1 for v in vs if v.get("_votos")),
        "votações com orientação Sim/Não": sum(1 for v in vs if _orientacao_governo(v) in ("Sim", "Não")),
    }


def _orientacao_governo(votacao: dict[str, Any]) -> str | None:
    return next((o.get("orientacaoVoto") for o in votacao.get("_orientacoes", [])
                 if (o.get("siglaPartidoBloco") or "").lower() == "governo"), None)


def governismo_do_bruto(raw: dict[str, Any]) -> dict[str, Governismo]:
    """Por deputado: votos válidos (Sim/Não numa votação com voto individual em que o governo
    orientou Sim/Não) e quantos iguais à orientação. Só entra quem tem ao menos um voto válido."""
    out: dict[str, Governismo] = {}
    for v in raw.get("votacoes", []):
        gov = _orientacao_governo(v)
        if gov not in ("Sim", "Não"):
            continue
        for voto in v.get("_votos", []):
            escolha = voto.get("tipoVoto")
            dep = (voto.get("deputado_") or {}).get("id")
            if escolha not in ("Sim", "Não") or dep is None:
                continue
            g = out.setdefault(str(dep), Governismo())
            g.n += 1
            g.convergentes += int(escolha == gov)
    return out


def _centavos(valor: Any) -> int | None:
    try:
        d = Decimal(str(valor).strip())
    except InvalidOperation:
        return None
    return int(d.quantize(Decimal("0.01")) * 100) if d.is_finite() else None


def ceap_do_bruto(zip_fonte: str | Path | IO[bytes], deputados: set[str]) -> dict[str, tuple[int, int]]:
    """{deputado_id: (n_despesas, total em centavos)} do zip oficial da CEAP, só para `deputados`.
    Linha sem `idDeputado` ou sem `valorLiquido` numérico fica de fora (como no ingest)."""
    out: dict[str, tuple[int, int]] = {}
    with zipfile.ZipFile(zip_fonte) as z:
        membro = next((i for i in z.infolist() if i.filename.lower().endswith(".json")), None)
        if membro is None:
            raise ValueError("zip sem arquivo json")
        with z.open(membro) as f:
            for linha in iterar_dados(f):
                dep = str(linha.get("idDeputado") or "")
                cents = _centavos(linha.get("valorLiquido"))
                if dep not in deputados or cents is None:
                    continue
                n, total = out.get(dep, (0, 0))
                out[dep] = (n + 1, total + cents)
    return out


# --------------------------------------------------------------------------- formatação
def _brl(centavos: int) -> str:
    sinal, c = ("-" if centavos < 0 else ""), abs(centavos)
    return f"{sinal}R$ {c // 100:,}".replace(",", ".") + f",{c % 100:02d}"


def _taxa(t: float | None) -> str:
    return "—" if t is None else str(t)


def _desc_gov(n: int, taxa: float | None, dispara: bool) -> str:
    return f"{n} votos, taxa {_taxa(taxa)}, {'dispara' if dispara else 'não dispara'}"


def _desc_ceap(n: int, centavos: int) -> str:
    return f"{n} despesas, {_brl(centavos)}"


# --------------------------------------------------------------------------- conferências
def _parametros_r01() -> tuple[int, float]:
    p = yaml.safe_load(REGRA_R01.read_text(encoding="utf-8"))["parametros"]
    return int(p["minimo_votacoes"]), float(p["limiar"])


def _conferir_votacoes(raw: dict[str, Any], store: Store) -> list[Linha]:
    bruto = votacoes_do_bruto(raw)
    j = store.janela_votos()
    banco = {"votações": j.n_votacoes, "votações nominais": j.n_votacoes_nominais,
             "votações com orientação Sim/Não": j.n_votacoes_com_orientacao}
    return [Linha("votacoes", k, str(bruto[k]), str(banco[k]),
                  OK if bruto[k] == banco[k] else DIVERGE,
                  "" if bruto[k] == banco[k] else "contagem diferente entre bruto e banco")
            for k in bruto]


def _conferir_governismo(raw: dict[str, Any], store: Store, deputados: dict[str, str]) -> list[Linha]:
    minimo, limiar = _parametros_r01()
    bruto = governismo_do_bruto(raw)
    linhas = []
    for dep, nome in sorted(deputados.items(), key=lambda kv: (len(kv[0]), kv[0])):
        b = bruto.get(dep, Governismo())
        dispara_esp = b.n >= minimo and b.taxa is not None and b.taxa >= limiar
        n_banco = store.contagem_votos(dep)[1]
        taxa_banco = round(store.votos_convergentes(dep) / n_banco, 3) if n_banco else None
        finding = next((f for f in store.findings_of(dep) if f.regra == "R01"), None)
        n_obt, taxa_obt = n_banco, taxa_banco
        problemas = []
        if (n_banco, taxa_banco) != (b.n, b.taxa):
            problemas.append(f"banco: {n_banco} votos válidos, taxa {_taxa(taxa_banco)}")
        if finding is not None:
            taxa_obt = finding.valores.get("taxa_governismo")
            if finding.valores.get("n_votacoes") != b.n:
                problemas.append(f"motor: {finding.valores.get('n_votacoes')} votos no finding")
            if taxa_obt != b.taxa:
                problemas.append(f"motor: taxa {_taxa(taxa_obt)} no finding")
        if (finding is not None) != dispara_esp:
            problemas.append("motor " + ("gerou" if finding else "não gerou") + " o finding R01, "
                             f"mas o bruto indica que {'deveria' if dispara_esp else 'não deveria'}"
                             f" (mínimo {minimo} votos, limiar {limiar})")
        linhas.append(Linha("governismo", f"{dep} {nome}", _desc_gov(b.n, b.taxa, dispara_esp),
                            _desc_gov(n_obt, taxa_obt, finding is not None),
                            DIVERGE if problemas else OK, "; ".join(problemas)))
    return linhas


def _achar_zip_ceap(raw_dir: Path) -> Path | None:
    zips = sorted((raw_dir / "ceap").glob("Ano-*.json.zip")) if (raw_dir / "ceap").is_dir() else []
    return zips[-1] if zips else None


def _conferir_ceap(raw_dir: Path, store: Store, deputados: dict[str, str]) -> list[Linha]:
    arquivo = _achar_zip_ceap(raw_dir)
    if arquivo is None:
        return [Linha("ceap", "CEAP", "—", "—", NAO_VERIFICADO,
                      "sem zip em ceap/Ano-*.json.zip; despesas não conferidas")]
    try:
        bruto = ceap_do_bruto(arquivo, set(deputados))
    except (zipfile.BadZipFile, ValueError, OSError) as e:
        return [Linha("ceap", arquivo.name, "—", "—", NAO_VERIFICADO,
                      f"não foi possível ler o zip: {e}")]
    banco = store.despesas_por_deputado()
    linhas = []
    for dep, nome in sorted(deputados.items(), key=lambda kv: (len(kv[0]), kv[0])):
        (n_b, c_b), (n_d, c_d) = bruto.get(dep, (0, 0)), banco.get(dep, (0, 0))
        problemas = []
        if n_b != n_d:
            problemas.append(f"contagem: bruto {n_b}, banco {n_d}")
        if abs(c_b - c_d) > TOLERANCIA_CENTAVOS:
            problemas.append(f"valor: bruto {_brl(c_b)}, banco {_brl(c_d)} (diferença {_brl(c_d - c_b)})")
        elif c_b != c_d:
            problemas.append("diferença de 1 centavo (dentro da tolerância)")
        diverge = n_b != n_d or abs(c_b - c_d) > TOLERANCIA_CENTAVOS
        linhas.append(Linha("ceap", f"{dep} {nome}", _desc_ceap(n_b, c_b), _desc_ceap(n_d, c_d),
                            DIVERGE if diverge else OK, "; ".join(problemas)))
    return linhas


def _conferir_manifesto(raw_dir: Path) -> list[Linha]:
    try:
        problemas = manifest.verificar(raw_dir)
        n_itens = len(manifest.carregar(raw_dir)["arquivos"])
    except (ValueError, OSError) as e:
        return [Linha("manifesto", "manifest.json", "—", "—", NAO_VERIFICADO, str(e))]
    if [p.tipo for p in problemas] == ["manifesto_ausente"]:
        # sem manifesto não há o que conferir: é "não verificado", não divergência de cada arquivo
        return [Linha("manifesto", "manifest.json", "—", "—", NAO_VERIFICADO, problemas[0].detalhe)]
    if not problemas:
        return [Linha("manifesto", "manifest.json", f"{n_itens} arquivos", f"{n_itens} arquivos",
                      OK, "sha256 de todos os arquivos confere")]
    return [Linha("manifesto", p.arquivo, "no manifesto" if p.tipo != "nao_registrado" else "—",
                  "no disco" if p.tipo != "ausente" else "—", DIVERGE, f"{p.tipo}: {p.detalhe}")
            for p in problemas]


def _conferir_online(raw: dict[str, Any], cliente: httpx.Client, n: int, semente: int) -> list[Linha]:
    por_id = {str(v["id"]): v for v in raw.get("votacoes", []) if v.get("id") is not None}
    sorteadas = random.Random(semente).sample(sorted(por_id), min(n, len(por_id)))
    linhas = []
    for vid in sorteadas:
        esperado = len(por_id[vid].get("_votos", []))
        try:
            r = cliente.get(f"{BASE_CAMARA}/votacoes/{vid}/votos")
            r.raise_for_status()
            ao_vivo = len(r.json().get("dados", []))
        except (httpx.HTTPError, ValueError) as e:
            linhas.append(Linha("online", f"votação {vid}", f"{esperado} votos", "—", NAO_VERIFICADO,
                                f"sem resposta da API: {type(e).__name__}"))
            continue
        ok = ao_vivo == esperado
        linhas.append(Linha("online", f"votação {vid}", f"{esperado} votos (bruto)",
                            f"{ao_vivo} votos (API)", OK if ok else DIVERGE,
                            "" if ok else "a API devolve outra contagem de votos"))
    return linhas


_JANELA_CAMARA = re.compile(r"camara_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.json")


def _achar_raw_camara(raw_dir: Path, inicio: date | None = None,
                      fim: date | None = None) -> tuple[Path | None, list[str]]:
    """Bruto da Câmara `camara_<início>_<fim>.json` cuja janela cobre as votações do banco
    (`inicio`..`fim`). Com mais de um candidato que não se resolve pela janela, usa o último em
    ordem alfabética e AVISA, em vez de escolher em silêncio."""
    pasta = raw_dir / "camara"
    candidatos = []
    for arq in sorted(pasta.glob("camara_*.json")) if pasta.is_dir() else []:
        if m := _JANELA_CAMARA.fullmatch(arq.name):
            candidatos.append((arq, date.fromisoformat(m[1]), date.fromisoformat(m[2])))
    if not candidatos:
        return None, []
    if len(candidatos) == 1:
        return candidatos[0][0], []
    cobrem = ([c for c in candidatos if c[1] <= inicio and c[2] >= fim]
              if inicio and fim else [])
    if len(cobrem) == 1:
        return cobrem[0][0], []
    pool = cobrem or candidatos
    escolhido = pool[-1][0]
    motivo = ("mais de um cobre a janela das votações do banco" if cobrem
              else "nenhum cobre a janela das votações do banco" if inicio and fim
              else "o banco não tem janela de votações para decidir")
    nomes = ", ".join(c[0].name for c in pool)
    aviso = f"{len(pool)} brutos da Câmara candidatos ({nomes}): {motivo}; conferido {escolhido.name}"
    return escolhido, [aviso]


def verificar(db: Path | str, raw_dir: Path | str, *, gerar_manifesto: bool = False,
              online: bool = False, cliente_http: httpx.Client | None = None,
              amostra_online: int = 5, semente: int = 0) -> Resultado:
    raw_dir = Path(raw_dir)
    store = Store(db, read_only=True)
    try:
        deputados = {f.chave: f.atributos.get("nome") or f"Deputado {f.chave}"
                     for f in store.facts_by_tipo("deputado")}
        res = Resultado(n_deputados=len(deputados), banco=Path(db).name, pasta_raw=raw_dir.name)
        janela = store.janela_votos()
        arq_camara, res.avisos = _achar_raw_camara(raw_dir, janela.inicio, janela.fim)
        if arq_camara is None:
            res.linhas.append(Linha("governismo", "Câmara", "—", "—", NAO_VERIFICADO,
                                    "sem camara/camara_<início>_<fim>.json; votações e governismo "
                                    "não conferidos"))
            raw: dict[str, Any] = {}
        else:
            raw = json.loads(arq_camara.read_text(encoding="utf-8"))
            res.linhas += _conferir_votacoes(raw, store)
            res.linhas += _conferir_governismo(raw, store, deputados)
        res.linhas += _conferir_ceap(raw_dir, store, deputados)
        if gerar_manifesto:
            res.manifesto_gerado = manifest.gerar_retroativo(raw_dir)
        res.linhas += _conferir_manifesto(raw_dir)
        if online and raw:
            if cliente_http is not None:
                res.linhas += _conferir_online(raw, cliente_http, amostra_online, semente)
            else:
                with httpx.Client(timeout=30, headers={"Accept": "application/json"}) as cliente:
                    res.linhas += _conferir_online(raw, cliente, amostra_online, semente)
        return res
    finally:
        store.con.close()


# --------------------------------------------------------------------------- saída
def renderizar_tabela(res: Resultado) -> str:
    cab = ("verificação", "item", "bruto (esperado)", "banco/motor (obtido)", "status")
    linhas = [cab] + [(lin.verificacao, lin.item, lin.esperado, lin.obtido, ROTULO_STATUS[lin.status])
                      for lin in res.linhas]
    larg = [max(len(str(r[i])) for r in linhas) for i in range(len(cab))]
    fmt = "  ".join(f"{{:<{w}}}" for w in larg)
    out = [fmt.format(*cab), "  ".join("-" * w for w in larg)]
    out += [fmt.format(*r) for r in linhas[1:]]
    for lin in res.linhas:
        if lin.status != OK and lin.detalhe:
            out.append(f"  ! {lin.verificacao} · {lin.item}: {lin.detalhe}")
    out += [f"  ? aviso: {a}" for a in res.avisos]
    out.append(_resumo(res))
    return "\n".join(out)


def _resumo(res: Resultado) -> str:
    n_ok = sum(1 for lin in res.linhas if lin.status == OK)
    return (f"{len(res.linhas)} conferências: {n_ok} ok, {res.divergencias} com divergência, "
            f"{res.nao_verificados} não verificadas")


def renderizar_md(res: Resultado, quando: str | None = None) -> str:
    quando = quando or date.today().isoformat()
    aprovado = res.divergencias == 0
    veredito = ("**APROVADO**: nenhuma divergência" if aprovado
                else f"**REPROVADO**: {res.divergencias} divergência(s)")
    if res.nao_verificados:
        veredito += f"; {res.nao_verificados} conferência(s) não verificada(s)"
    md = ["# Verificação dos dados contra o bruto", "",
          (f"Gerado em {quando} por `python -m scripts.verifica` (`make verifica`). "
           f"Banco: `{res.banco}` ({res.n_deputados} deputados). Brutos: pasta `{res.pasta_raw}`."),
          "",
          f"**Resultado:** {veredito}.", "", _resumo(res) + ".", "",
          "| verificação | ok | diverge | não verificado |", "|---|---|---|---|"]
    for chave, titulo in TITULOS.items():
        ls = [lin for lin in res.linhas if lin.verificacao == chave]
        if ls:
            md.append(f"| {titulo} | {sum(lin.status == OK for lin in ls)} | "
                      f"{sum(lin.status == DIVERGE for lin in ls)} | "
                      f"{sum(lin.status == NAO_VERIFICADO for lin in ls)} |")
    md += ["", "## Divergências", ""]
    div = [lin for lin in res.linhas if lin.status == DIVERGE]
    md += ([f"- **{TITULOS[lin.verificacao]} · {lin.item}**: bruto `{lin.esperado}`, banco/motor "
            f"`{lin.obtido}`. {lin.detalhe}" for lin in div] if div else ["Nenhuma divergência."])
    nv = [lin for lin in res.linhas if lin.status == NAO_VERIFICADO]
    md += ["", "## Não verificado", ""]
    md += ([f"- **{TITULOS[lin.verificacao]} · {lin.item}**: {lin.detalhe}" for lin in nv]
           if nv else ["Nada ficou sem verificar nas conferências executadas."])
    if res.avisos:
        md += ["", "## Avisos", ""] + [f"- {a}" for a in res.avisos]
    md += ["", "## Todas as conferências"]
    for chave, titulo in TITULOS.items():
        ls = [lin for lin in res.linhas if lin.verificacao == chave]
        if not ls:
            continue
        md += ["", f"### {titulo}", "", "| item | bruto (esperado) | banco/motor (obtido) | status |",
               "|---|---|---|---|"]
        md += [f"| {lin.item} | {lin.esperado} | {lin.obtido} | {ROTULO_STATUS[lin.status]} |"
               for lin in ls]
    md += ["", "## Como ler e limites", "",
           "- Contagens: tolerância zero. Valores em reais: até 1 centavo (somados em centavos, sem float).",
           ("- \"Bruto\" é recalculado do JSON da Câmara e do zip da CEAP sem usar o motor; \"banco\" é a "
            "consulta SQL aos fatos; \"motor\" é o finding da R01 gravado por `make infer`."),
           "- Governismo e CEAP conferem os deputados que estão no banco (a amostra), não os 513.",
           ("- Isto confere o caminho bruto → banco → motor. Não prova que o dado oficial está certo, "
            "só que o sistema o reproduz sem perder nem inventar nada.")]
    if res.manifesto_gerado:
        md.append(f"- O manifesto foi gerado agora para {res.manifesto_gerado} arquivo(s) que já existiam "
                  "(origem `retroativo`): o hash prova que o arquivo não mudou daqui em diante, não que é "
                  "idêntico ao que foi baixado na época.")
    if not any(lin.verificacao == "online" for lin in res.linhas):
        md.append("- A conferência `--online` (contagem de votos direto na API da Câmara) não foi executada.")
    return "\n".join(md) + "\n"


# --------------------------------------------------------------------------- CLI
def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.verifica",
                                 description="Confere banco e motor contra os brutos.")
    ap.add_argument("--db", type=Path, default=None, help="banco (padrão: $RAIO_X_DB)")
    ap.add_argument("--raw", type=Path, default=None, help="pasta data/raw (padrão: $RAIO_X_RAW)")
    ap.add_argument("--saida", type=Path, default=RELATORIO, help=f"relatório .md (padrão: {RELATORIO.relative_to(RAIZ)})")
    ap.add_argument("--gerar-manifesto", action="store_true",
                    help="registra no manifesto os arquivos de data/raw que ainda não constam (origem retroativo)")
    ap.add_argument("--online", action="store_true", help="confere por amostragem na API da Câmara (usa rede)")
    ap.add_argument("--amostra-online", type=int, default=5, help="votações sorteadas no --online")
    ap.add_argument("--semente", type=int, default=0, help="semente do sorteio do --online")
    args = ap.parse_args(argv)
    db = args.db or os.environ.get("RAIO_X_DB")
    if not db or not Path(db).exists():
        ap.error(f"banco não encontrado: {db or '(use --db ou RAIO_X_DB)'}")
    res = verificar(db, args.raw or manifest.raw_dir_padrao(), gerar_manifesto=args.gerar_manifesto,
                    online=args.online, amostra_online=args.amostra_online, semente=args.semente)
    print(renderizar_tabela(res))
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(renderizar_md(res), encoding="utf-8")
    print(f"relatório: {args.saida}", file=sys.stderr)
    return 1 if res.divergencias else 0


if __name__ == "__main__":
    sys.exit(main())
