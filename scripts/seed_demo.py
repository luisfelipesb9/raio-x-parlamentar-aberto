"""Gera um banco de DEMONSTRAÇÃO, 100% fictício e sem rede: `data/sample/raio_x_demo.duckdb`.

Seis deputados inventados (ids a partir de 9900001, partidos FICT-A/FICT-B, nomes com "(demo)"),
com votações nominais e simbólicas, CEAP, uma empresa sancionada fictícia, sócios e doadores
mascarados, emendas por município, votos por município, proposições e autorias. Roda o motor
sobre eles (como `make sample`). Nenhum dado é real; todo fato tem `fonte="demo_ficticio"` e
uma URL `.invalid`, que nunca resolve.

O conjunto foi desenhado para exercitar as regras:
  R01  Alice, Bruno e Fábio (alinhados); Carla e Elisa (abaixo do limiar); Davi (dados insuficientes)
  R03  Bruno e Elisa pagaram a Consultoria Inventada, sancionada; o pagamento a uma empresa com
       sanção já expirada (Alice) não conta
  R04  Carla, com combustível muito acima dos colegas
  R05  Alice, Bruno, Carla, Davi e Fábio (Elisa não tem autoria registrada)
  R07  Alice e Carla concentram emendas onde têm mais votos; Bruno recebeu emendas de forma
       proporcional (sem finding)
  R06b Davi: doador com o mesmo nome de um sócio de empresa que ele pagou (CPF não confirmável)

Uso: python -m scripts.seed_demo [--db data/sample/raio_x_demo.duckdb]   (make seed-demo)
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from contracts import Fact
from engine import forward
from engine.factbase import FactBase
from engine.rules import load_rules
from ingest.pseudonimizar import pseudonimizar_fatos
from repo.store import DB_PATH, Store

FONTE = "demo_ficticio"
AVISO = "DADOS FICTÍCIOS PARA DEMONSTRAÇÃO"
SAL_DEMO = "sal-fixo-da-demonstracao"  # sal só do demo (dado fictício): ids reprodutíveis
COLETADO = datetime(2025, 4, 1, 12, 0, tzinfo=UTC)
BASE_URL = "https://demo.invalid/dados-ficticios"
DB_DEMO = DB_PATH.parent / "sample" / "raio_x_demo.duckdb"

# (id, nome, partido, uf)
DEPUTADOS: list[tuple[str, str, str, str]] = [
    ("9900001", "Alice Fictícia (demo)", "FICT-A", "MG"),
    ("9900002", "Bruno Inventado (demo)", "FICT-A", "MG"),
    ("9900003", "Carla Simulada (demo)", "FICT-A", "SP"),
    ("9900004", "Davi Exemplo (demo)", "FICT-B", "SP"),
    ("9900005", "Elisa Modelo (demo)", "FICT-B", "BA"),
    ("9900006", "Fábio Protótipo (demo)", "FICT-B", "BA"),
]
IDS = [d[0] for d in DEPUTADOS]
A, B, C, D, E, FAB = IDS

# votações nominais em que o governo orientou: quantos votos de cada um seguem a orientação
N_NOMINAIS = 32
SEGUE: dict[str, int] = {A: 32, B: 28, C: 12, D: 32, E: 20, FAB: 24}
PARTICIPA: dict[str, int] = {A: 32, B: 32, C: 32, D: 6, E: 32, FAB: 32}  # Davi quase não votou
PASSO: dict[str, int] = {A: 3, B: 5, C: 7, D: 9, E: 11, FAB: 13}  # ímpar: permuta 0..31


def _fato(tipo: str, chave: str, /, **atributos) -> Fact:
    return Fact(tipo=tipo, chave=chave, atributos=atributos, fonte=FONTE, id_oficial=chave,
                url=f"{BASE_URL}/{tipo}/{chave}", coletado_em=COLETADO)


def _cnpj(numero: int) -> str:
    """CNPJ fictício com dígitos verificadores válidos, numa raiz (99999xxx) fora da faixa real."""
    base = [int(c) for c in f"99999{numero:03d}0001"]
    for pesos in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        soma = sum(d * p for d, p in zip(base, pesos, strict=True))
        base.append(0 if soma % 11 < 2 else 11 - soma % 11)
    return "".join(map(str, base))


def _norm(nome: str) -> str:
    return re.sub(r"\s+", " ", nome).strip().upper()


# fornecedores fictícios: (numero, razão social)
FORNECEDORES = {
    "posto": (1, "Posto Exemplo Ltda (demo)"),
    "grafica": (2, "Gráfica Modelo Ltda (demo)"),
    "viagens": (3, "Agência Simulada de Viagens (demo)"),
    "consultoria": (4, "Consultoria Inventada S/A (demo)"),  # sancionada e vigente
    "escritorio": (5, "Escritório Fictício Ltda (demo)"),  # sócio com o mesmo nome de um doador
    "expirada": (6, "Serviços Expirados Ltda (demo)"),  # sanção terminada em 2024
}
CNPJ = {k: _cnpj(n) for k, (n, _) in FORNECEDORES.items()}


def _deputados() -> list[Fact]:
    return [_fato("deputado", i, nome=nome, partido=p, uf=uf, ficticio=True)
            for i, nome, p, uf in DEPUTADOS]


def _votacoes() -> list[Fact]:
    fatos: list[Fact] = []
    inicio = date(2025, 2, 3)
    for n in range(1, N_NOMINAIS + 1):
        orient = "Sim" if n % 3 else "Não"
        fatos.append(_fato(
            "votacao", f"DEMO-V{n:03d}", data=(inicio + timedelta(days=n)).isoformat(),
            descricao=f"{AVISO}: votação nominal nº {n}", nominal=True, orientacao_governo=orient))
        for dep in IDS:
            if n > PARTICIPA[dep]:
                continue  # não votou (ausente)
            segue = (n * PASSO[dep]) % N_NOMINAIS < SEGUE[dep]  # espalha os votos contrários
            contra = "Não" if orient == "Sim" else "Sim"
            fatos.append(_fato("voto", f"DEMO-V{n:03d}:{dep}", votacao_id=f"DEMO-V{n:03d}",
                               deputado_id=dep, voto=orient if segue else contra))
    # sem orientação do governo: entra no banco, mas não na taxa de governismo
    for n in (33, 34):
        fatos.append(_fato(
            "votacao", f"DEMO-V{n:03d}", data=(inicio + timedelta(days=n)).isoformat(),
            descricao=f"{AVISO}: votação nominal nº {n} (governo não orientou)", nominal=True,
            orientacao_governo=None))
        for dep in IDS:
            fatos.append(_fato("voto", f"DEMO-V{n:03d}:{dep}", votacao_id=f"DEMO-V{n:03d}",
                               deputado_id=dep, voto="Sim"))
    # votações simbólicas: têm orientação, mas não existe voto individual
    for n, orient in ((35, "Sim"), (36, "Não"), (37, "Sim")):
        fatos.append(_fato(
            "votacao", f"DEMO-V{n:03d}", data=(inicio + timedelta(days=n)).isoformat(),
            descricao=f"{AVISO}: votação simbólica nº {n}", nominal=False,
            orientacao_governo=orient))
    return fatos


def _despesas() -> list[Fact]:
    fatos: list[Fact] = []
    n = 0

    def gasto(dep: str, forn: str, cat: str, valor: float, dia: str) -> None:
        nonlocal n
        n += 1
        fatos.append(_fato("despesa_ceap", f"DEMO-D{n:04d}", deputado_id=dep, cnpj=CNPJ[forn],
                           fornecedor=FORNECEDORES[forn][1], valor=valor, categoria=cat, data=dia))

    base = {  # (combustível, divulgação, passagens) por mês, por deputado
        A: (1050, 2100, 1700), B: (1200, 2300, 2000), C: (1100, 2500, 1800),
        D: (950, 2000, 1500), E: (1300, 2600, 2100), FAB: (1125, 2250, 1900)}
    for dep, (comb, div, pas) in base.items():
        for mes, dia in ((2, "2025-02-10"), (3, "2025-03-10")):
            f = 1 + 0.03 * mes  # pequena variação mensal
            gasto(dep, "posto", "combustivel", round(comb * f, 2), dia)
            gasto(dep, "grafica", "divulgacao", round(div * f, 2), dia)
            gasto(dep, "viagens", "passagens", round(pas * f, 2), dia)
    gasto(C, "posto", "combustivel", 31500.00, "2025-03-12")  # R04: fora do padrão
    gasto(B, "consultoria", "consultoria", 12000.00, "2025-02-20")  # R03: sanção vigente
    gasto(E, "consultoria", "consultoria", 4500.00, "2025-03-05")  # R03: sanção vigente
    gasto(A, "expirada", "consultoria", 3000.00, "2025-03-01")  # sanção já terminada: não conta
    gasto(D, "escritorio", "consultoria", 8000.00, "2025-03-15")  # R06b: sócio = doador
    return fatos


def _sancoes_empresas_socios() -> list[Fact]:
    fatos = [
        _fato("sancao", "CEIS:DEMO-S1", cnpj=CNPJ["consultoria"], cadastro="CEIS",
              inicio="2024-06-01", fim=None, orgao="Órgão Sancionador Fictício"),
        _fato("sancao", "CEIS:DEMO-S2", cnpj=CNPJ["expirada"], cadastro="CEIS",
              inicio="2023-01-01", fim="2024-12-31", orgao="Órgão Sancionador Fictício"),
    ]
    for chave, (numero, razao) in FORNECEDORES.items():
        fatos.append(_fato("empresa", CNPJ[chave], razao_social=razao, situacao="ATIVA",
                           cnae="7490104", municipio_ibge="9900101", ficticio=True))
    # sócios: CPF sempre mascarado (como na Receita); um deles tem o nome de um doador de Davi
    socios = [("escritorio", "Teodoro Exemplar Silva", "***700101**", "Sócio-Administrador"),
              ("escritorio", "Ursula Modelo Costa", "***810202**", "Sócio"),
              ("consultoria", "Valério Simulado Reis", "***920303**", "Sócio-Administrador"),
              ("posto", "Wanda Fictícia Prado", "***630404**", "Sócio-Administrador")]
    for forn, nome, cpf, qual in socios:
        fatos.append(_fato("socio", f"{CNPJ[forn]}:{_norm(nome)}", cnpj=CNPJ[forn], nome=nome,
                           cpf_cnpj=cpf, qualificacao=qual))
    return fatos


# municípios fictícios de cada UF: ibge "99UUnnn"
UF_COD = {"MG": "31", "SP": "35", "BA": "29"}


def _ibge(uf: str, k: int) -> str:
    return f"99{UF_COD[uf]}{k:03d}"


def _eleicoes_e_emendas() -> list[Fact]:
    fatos: list[Fact] = []
    sq = {dep: f"9901{i + 1:04d}" for i, dep in enumerate(IDS)}
    ufs = {d[0]: d[3] for d in DEPUTADOS}
    # (municípios que receberam emendas, votos nesses municípios, votos nos demais, tipo da emenda)
    emendas = {
        A: ((1, 2, 3), 3000, 500, "individual"),   # razão 6: finding
        B: ((1, 2, 3), 600, 500, "individual"),    # razão 1,2: sem finding
        C: ((1, 2, 3), 2500, 600, "pix"),          # razão ~4,2: finding, com a ressalva do Pix
    }
    for dep in IDS:
        uf = ufs[dep]
        fatos.append(_fato("candidatura", sq[dep], ano=2022,
                           nome=next(n for i, n, _, _ in DEPUTADOS if i == dep).replace(" (demo)", ""),
                           nome_urna=next(n for i, n, _, _ in DEPUTADOS if i == dep),
                           cargo="DEPUTADO FEDERAL", uf=uf,
                           partido=next(p for i, _, p, _ in DEPUTADOS if i == dep),
                           deputado_id=dep))
        destino, v_dest, v_resto, _ = emendas.get(dep, ((1, 2, 3), 700, 600, "individual"))
        for k in range(1, 9):
            votos = v_dest if k in destino else v_resto
            fatos.append(_fato(
                "votos_municipio", f"2022:{sq[dep]}:{_ibge(uf, k)}", ano=2022,
                sq_candidato=sq[dep], municipio_ibge=_ibge(uf, k), municipio_nome=f"Vila Demo {uf}-{k}",
                uf=uf, votos=votos, votos_validos_municipio=10000))
    n = 0
    for dep, (destino, _, _, tipo) in emendas.items():
        for k in destino:
            n += 1
            fatos.append(_fato(
                "emenda", f"DEMO-E{n:03d}", deputado_id=dep, autor_nome=f"Autor demo {dep}",
                ano=2024, valor_empenhado=250000.0 * k, valor_pago=100000.0 * k,
                municipio_ibge=_ibge(ufs[dep], k), municipio_nome=f"Vila Demo {ufs[dep]}-{k}",
                tipo=tipo))
    # doações: PF com CPF de dígitos verificadores INVÁLIDOS (nunca é CPF de alguém), pseudonimizado
    # depois; o doador de Davi tem o mesmo nome de um sócio da empresa que ele pagou (R06b)
    doacoes = [
        (D, "Teodoro Exemplar Silva", "99970010100", "PF", 1500.0),
        (A, "Xavier Anônimo Lima", "99981020200", "PF", 800.0),
        (B, "Yara Inventada Souza", "99992030300", "PF", 1200.0),
        (A, "Comércio Demo Ltda (demo)", _cnpj(9), "PJ", 5000.0),
        (C, "Direção Nacional FICT-A", _cnpj(10), "partido", 20000.0),
    ]
    for i, (dep, nome, doc, tipo, valor) in enumerate(doacoes, start=1):
        fatos.append(_fato("doacao", f"DEMO-R{i:03d}", sq_candidato=sq[dep], doador_nome=nome,
                           doador_cpf_cnpj=doc, valor=valor, data="2022-09-15", tipo_doador=tipo))
    return fatos


def _proposicoes() -> list[Fact]:
    fatos: list[Fact] = []
    # (deputado, autorias, coautorias, relatorias): 'Elisa' não tem nenhuma autoria registrada
    plano = {A: (8, 5, 2), B: (3, 6, 0), C: (12, 0, 4), D: (1, 0, 0), FAB: (5, 2, 1)}
    n = 0
    for dep, (aut, coaut, rel) in plano.items():
        for papel, qtd in (("autor", aut), ("coautor", coaut), ("relator", rel)):
            for _ in range(qtd):
                n += 1
                pid = f"99{n:05d}"
                fatos.append(_fato("proposicao", pid, sigla_tipo="PL", numero=9000 + n, ano=2025,
                                   ementa=f"{AVISO}: projeto de exemplo nº {n}",
                                   data=f"2025-0{1 + n % 3}-1{n % 9}"))
                fatos.append(_fato("autoria", f"{pid}:{dep}:{papel}", proposicao_id=pid,
                                   deputado_id=dep, papel=papel))
    return fatos


def montar_fatos() -> list[Fact]:
    """Todos os fatos do demo, ainda com o CPF fictício das doações em claro (nunca persistido)."""
    return (_deputados() + _votacoes() + _despesas() + _sancoes_empresas_socios()
            + _eleicoes_e_emendas() + _proposicoes())


def gerar(db: Path | str) -> dict:
    """Recria o banco `db` do zero (sem rede), grava os fatos pseudonimizados e roda o motor."""
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    for sufixo in ("", ".wal"):
        Path(f"{db}{sufixo}").unlink(missing_ok=True)
    store = Store(db)
    try:
        store.upsert_facts(pseudonimizar_fatos(montar_fatos(), SAL_DEMO))
        res = forward.run(FactBase(store.load_facts()), load_rules())
        store.save_findings(res.findings, res.explanations)
        contagem = Counter(f.tipo for f in store.load_facts())
        return {"db": str(db), "deputados": contagem["deputado"], "fatos": sum(contagem.values()),
                "por_tipo": dict(sorted(contagem.items())), "findings": len(res.findings),
                "regras": sorted({f.regra for f in res.findings}),
                "guardrails": dict(res.guardrail_log)}
    finally:
        store.con.close()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", type=Path, default=DB_DEMO, help=f"banco a gerar (padrão: {DB_DEMO})")
    r = gerar(ap.parse_args(argv).db)
    print(f"{AVISO}\n{r['db']}: {r['deputados']} deputados fictícios, {r['fatos']} fatos, "
          f"{r['findings']} findings (regras: {', '.join(r['regras'])})")


if __name__ == "__main__":
    main()
