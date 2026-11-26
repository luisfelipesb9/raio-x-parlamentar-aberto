"""fetch → normalize → resolve → upsert, multi-fonte e idempotente.

Uso:
  python -m ingest.pipeline --fontes camara,ceap,cgu,tse,opensanctions,rfb --uf MG --ano 2024 \\
      --amostra 20 --limite-rfb 50 --db data/sample/raio_x_sample.duckdb

Escopo: `--uf` e/ou `--amostra N` restringem a base a um conjunto de deputados (os N primeiros
da UF, por id). Só entra o que é atribuível a eles; o resto é descartado antes de gravar.
A resolução de entidades usa TODOS os deputados da Câmara (para enxergar homônimos fora do
escopo), mas nunca grava link para deputado fora do escopo.
Cada passo apaga o que vai reafirmar (INSERT OR REPLACE não remove chave que sumiu) e regrava.

Modo nacional (sem --uf nem --amostra): o TSE é processado uma UF por vez (baixa, normaliza, grava e
solta antes da próxima; bruto por UF em data/raw/tse/) e `--reusar-raw` pula a UF já baixada. O
CEAP aceita vários anos (`--anos-ceap 2023,2024`), um zip por ano lido uma única vez.
Ver docs/ampliacao/ingest-nacional.md.
"""
from __future__ import annotations

import argparse
import inspect
import json
import re
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from contracts import Fact
from ingest.pseudonimizar import pseudonimizar_fatos, salt_do_ambiente
from ingest.resolve import (
    Resolucao,
    resolver_candidaturas,
    resolver_cnpj,
    resolver_emendas,
    resolver_peps,
)
from ingest.resolve.comum import cnpj_valido, deputados_unicos
from repo.store import Store
from sources import REGISTRY

ORDEM = ("camara", "ceap", "cgu", "tse", "opensanctions", "rfb")  # ordem de execução fixa


# ---------- utilidades puras (testadas) ----------

def montar_kwargs(fetch: Callable[..., Any], disponiveis: dict[str, Any]) -> dict[str, Any]:
    """Só os argumentos que a assinatura de `fetch` aceita. Parâmetro obrigatório que não está
    em `disponiveis` é erro explícito (e não um TypeError obscuro no meio da coleta)."""
    params = inspect.signature(fetch).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return dict(disponiveis)
    faltam = [n for n, p in params.items() if p.default is inspect.Parameter.empty
              and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY) and n not in disponiveis]
    if faltam:
        raise ValueError(f"{getattr(fetch, '__qualname__', fetch)} exige {faltam}, que o pipeline "
                         f"não tem (disponíveis: {sorted(disponiveis)})")
    return {k: v for k, v in disponiveis.items() if k in params}


def chamar_fetch(src: Any, **disponiveis: Any) -> dict:
    return src.fetch(**montar_kwargs(src.fetch, disponiveis))


def selecionar_escopo(deputados: Iterable[Fact], uf: str | None, amostra: int | None
                      ) -> set[str] | None:
    """Ids dos deputados do escopo (UF e/ou os N primeiros por id); None = sem restrição."""
    if not uf and not amostra:
        return None
    unicos = deputados_unicos(list(deputados)).values()
    ids = sorted((d.chave for d in unicos
                  if not uf or (d.atributos.get("uf") or "").upper() == uf.upper()),
                 key=lambda x: (len(x), x))
    return set(ids[:amostra] if amostra else ids)


# ---------- opções e pipeline ----------

@dataclass
class Opcoes:
    fontes: tuple[str, ...] = ("camara",)
    uf: str | None = None
    ano: int | None = None  # ano do arquivo CEAP
    anos_ceap: tuple[int, ...] = ()  # vários anos do CEAP (vale no lugar de `ano`)
    ano_eleicao: int = 2022
    amostra: int | None = None
    limite_rfb: int = 50
    max_votacoes: int | None = 30
    janela_inicio: str = "2025-01-01"
    janela_fim: str = "2025-03-31"
    max_pep: int | None = None
    reusar_raw: bool = False
    detalhar_deputados: bool = False  # GET /deputados/{id}: cpf e nome civil (só os do escopo)
    incluir_proposicoes: bool = False  # proposicao/autoria (alimenta a R05)
    max_proposicoes: int | None = 300
    siglas_proposicoes: tuple[str, ...] = ("PL", "PEC", "PLP")
    pseudonimizar: bool = False  # HMAC do CPF de terceiros (precisa de RAIO_X_ID_SALT)
    fixture: str | None = None  # JSON bruto da Câmara em vez de baixar


@dataclass
class Pipeline:
    store: Store
    opcoes: Opcoes
    registry: dict = field(default_factory=lambda: dict(REGISTRY))
    log: Callable[[str], None] = print
    todos_deputados: list[Fact] = field(default_factory=list)
    escopo: set[str] | None = None
    relatorio: dict[str, Any] = field(default_factory=dict)
    salt: str | None = None

    # ----- orquestração -----

    def executar(self) -> dict[str, Any]:
        desconhecidas = [f for f in self.opcoes.fontes if f not in self.registry]
        if desconhecidas:
            raise ValueError(f"fonte desconhecida: {desconhecidas} (use {sorted(self.registry)})")
        if "ceap" in self.opcoes.fontes and not self._anos_ceap():
            raise ValueError("a fonte ceap precisa de --ano (ou --anos-ceap)")
        if self.opcoes.incluir_proposicoes and "camara" in self.opcoes.fontes and not callable(
                getattr(self.registry["camara"], "fetch_proposicoes", None)):
            raise ValueError("--incluir-proposicoes: a fonte camara não tem fetch_proposicoes")
        if self.opcoes.pseudonimizar:
            self.salt = salt_do_ambiente()  # falha antes de coletar qualquer coisa
        if "camara" not in self.opcoes.fontes:
            self._deputados_do_banco()
        for nome in ORDEM:
            if nome in self.opcoes.fontes:
                self.log(f"[{nome}] ...")
                getattr(self, f"_passo_{nome}")()
        if {"ceap", "cgu", "rfb"} & set(self.opcoes.fontes):
            self._ligar_cnpj()
        self.relatorio["escopo_deputados"] = None if self.escopo is None else len(self.escopo)
        return self.relatorio

    # ----- contexto -----

    def _deputados_do_banco(self) -> None:
        self.todos_deputados = list(deputados_unicos(self.store.facts_by_tipo("deputado")).values())
        self.escopo = selecionar_escopo(self.todos_deputados, self.opcoes.uf, self.opcoes.amostra)

    def _no_escopo(self, dep_id: Any) -> bool:
        return self.escopo is None or str(dep_id) in self.escopo

    def _ufs_do_escopo(self) -> list[str | None]:
        if self.opcoes.uf:
            return [self.opcoes.uf.upper()]
        if self.escopo is None:
            return [None]
        d = deputados_unicos(self.todos_deputados)
        return sorted({d[i].atributos["uf"] for i in self.escopo if i in d and d[i].atributos.get("uf")})

    def _cnpjs_do_escopo(self) -> set[str]:
        return {f.atributos["cnpj"] for f in self.store.facts_by_tipo("despesa_ceap")
                if f.atributos.get("cnpj") and self._no_escopo(f.atributos.get("deputado_id"))}

    def _p(self, fatos: list[Fact]) -> list[Fact]:
        """Pseudonimiza o CPF de terceiros quando pedido (--pseudonimizar)."""
        return pseudonimizar_fatos(fatos, self.salt) if self.salt else fatos

    def _gravar(self, fatos: list[Fact], res: Resolucao | None = None,
                origens: Iterable[str] = ()) -> None:
        n = self.store.upsert_facts(self._p(fatos))  # ponto único: nada é gravado sem passar aqui
        if res is not None:
            self.store.upsert_links(res.links, substituir_origens=origens)
            self.store.save_ambiguities(res.ambiguos, substituir_origens=origens)
        self.log(f"    {n} fatos gravados, {len(res.links) if res else 0} links")

    def _restringir(self, res: Resolucao, tipo: str) -> tuple[list[Fact], Resolucao]:
        """No modo escopo, só ficam fatos ligados a deputado do escopo (e seus links)."""
        if self.escopo is None:
            return res.fatos, res
        fatos = [f for f in res.fatos if self._no_escopo(f.atributos.get("deputado_id"))
                 and f.atributos.get("deputado_id")]
        ficam = {f"{tipo}:{f.chave}" for f in fatos}
        links = [lk for lk in res.links if lk.origem in ficam
                 and lk.destino.removeprefix("deputado:") in self.escopo]
        amb = [a for a in res.ambiguos if any(c.removeprefix("deputado:") in self.escopo
                                              for c in a.candidatos)]
        return fatos, Resolucao(fatos=fatos, links=links, ambiguos=amb)

    # ----- passos -----

    def _passo_camara(self) -> None:
        o = self.opcoes
        src = self.registry["camara"]()
        raw = self._raw_camara(src)
        fatos = src.normalize(raw)
        self.todos_deputados = list(deputados_unicos(
            [f for f in fatos if f.tipo == "deputado"]).values())
        self.escopo = selecionar_escopo(self.todos_deputados, o.uf, o.amostra)
        ficam = [f for f in fatos if f.tipo == "votacao"] + \
                [f for f in self.todos_deputados if self._no_escopo(f.chave)] + \
                [f for f in fatos if f.tipo in ("voto", "autoria")
                 and self._no_escopo(f.atributos.get("deputado_id"))]
        votacoes = [f.chave for f in ficam if f.tipo == "votacao"]
        onde: dict[str, Collection] = {"votacao_id": votacoes}
        if self.escopo is not None:
            onde["deputado_id"] = self.escopo
        if ficam:
            self.store.delete_facts("voto", fonte=ficam[0].fonte, onde=onde)
        self._gravar(ficam)
        self.relatorio["camara"] = {"deputados_total": len(self.todos_deputados),
                                    "deputados_escopo": len(self.todos_deputados)
                                    if self.escopo is None else len(self.escopo)}
        if o.incluir_proposicoes:
            self._proposicoes(src)

    def _proposicoes(self, src: Any) -> None:
        """proposicao + autoria (PL/PEC/PLP da janela) dos deputados do escopo. Só fica autoria
        de deputado do escopo, e a proposição que tem ao menos uma delas."""
        o = self.opcoes
        ids = None if self.escopo is None else sorted(self.escopo, key=lambda x: (len(x), x))
        raw = src.fetch_proposicoes(o.janela_inicio, o.janela_fim, deputado_ids=ids,
                                    siglas_tipo=o.siglas_proposicoes,
                                    max_proposicoes=o.max_proposicoes)
        fatos = src.normalize({"proposicoes": raw.get("proposicoes", [])})
        autorias = [f for f in fatos if f.tipo == "autoria"
                    and self._no_escopo(f.atributos.get("deputado_id"))]
        com_autor = {f.atributos.get("proposicao_id") for f in autorias}
        props = [f for f in fatos if f.tipo == "proposicao" and f.chave in com_autor]
        if autorias:
            self.store.delete_facts("autoria", fonte=autorias[0].fonte,
                                    onde={"deputado_id": self.escopo}
                                    if self.escopo is not None else None)
        self._gravar(props + autorias)
        self.relatorio["camara"].update({"proposicoes": len(props), "autorias": len(autorias),
                                         "proposicoes_erros": len(raw.get("erros", []))})

    def _raw_camara(self, src: Any) -> dict:
        o = self.opcoes
        if o.fixture:
            return json.loads(Path(o.fixture).read_text(encoding="utf-8"))
        alvo = src.raw_path(f"camara_{o.janela_inicio}_{o.janela_fim}.json")
        cache = (json.loads(alvo.read_text(encoding="utf-8"))
                 if alvo.exists() and (o.reusar_raw or o.detalhar_deputados) else None)
        extra: dict[str, Any] = {}
        if o.detalhar_deputados:
            self._exigir_detalhamento(src)
            extra["detalhar_deputados"] = self._ids_para_detalhar(src, cache)
        if o.reusar_raw and cache is not None and self._cache_serve(cache, extra):
            self.log(f"    reaproveitando {alvo.name}")
            if o.max_votacoes is not None:
                cache["votacoes"] = cache.get("votacoes", [])[:o.max_votacoes]
            return cache
        return chamar_fetch(src, data_inicio=o.janela_inicio, data_fim=o.janela_fim,
                            max_votacoes=o.max_votacoes, **extra)

    @staticmethod
    def _exigir_detalhamento(src: Any) -> None:
        params = inspect.signature(src.fetch).parameters
        if "detalhar_deputados" not in params and not any(
                p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
            raise ValueError("--detalhar-deputados: o fetch desta fonte não aceita "
                             "`detalhar_deputados` (cpf/nome_civil não serão coletados)")

    def _ids_para_detalhar(self, src: Any, cache: dict | None) -> bool | list[str]:
        """True (todos) sem escopo; com escopo, só os ids dele. A lista de deputados vem do cache
        ou de uma coleta prévia sem votações (o escopo só existe depois de conhecê-la)."""
        o = self.opcoes
        if not o.uf and not o.amostra:
            return True
        if cache is None:
            cache = chamar_fetch(src, data_inicio=o.janela_inicio, data_fim=o.janela_fim,
                                 max_votacoes=0)
        deputados = [f for f in src.normalize({"deputados": cache.get("deputados", [])})
                     if f.tipo == "deputado"]
        escopo = selecionar_escopo(deputados, o.uf, o.amostra) or set()
        return sorted(escopo, key=lambda x: (len(x), x))

    @staticmethod
    def _cache_serve(cache: dict, extra: dict[str, Any]) -> bool:
        """O cache vale se, quando se pediu detalhe, todo deputado pedido já o tem."""
        pedido = extra.get("detalhar_deputados")
        if pedido is None:
            return True
        return all("_detalhe" in d for d in cache.get("deputados", [])
                   if pedido is True or str(d.get("id")) in pedido)

    def _anos_ceap(self) -> tuple[int, ...]:
        """Anos do CEAP a processar: `anos_ceap` se vier, senão `ano`; sem repetição, em ordem."""
        o = self.opcoes
        return tuple(dict.fromkeys(o.anos_ceap or (() if o.ano is None else (o.ano,))))

    def _passo_ceap(self) -> None:
        """Um zip por ano, lido uma única vez (a leitura não depende de quantos deputados há no
        escopo: o filtro é um conjunto em memória). Os anos são processados em sequência, e só um
        ano fica em memória por vez."""
        src = self.registry["ceap"]()
        por_ano: dict[int, int] = {}
        com_cnpj = 0
        sem_data_anteriores: list[Fact] = []
        for ano in self._anos_ceap():
            raw = chamar_fetch(src, ano=ano)
            fatos = [f for f in src.normalize(raw) if f.tipo == "despesa_ceap"
                     and self._no_escopo(f.atributos.get("deputado_id"))]
            del raw
            if fatos:
                self.store.delete_facts(
                    "despesa_ceap", fonte=fatos[0].fonte, ano_data=ano,
                    onde={"deputado_id": self.escopo} if self.escopo is not None else None)
            self._gravar(fatos)
            if sem_data_anteriores:
                # o delete por ano também apaga fatos sem data (não dá para saber de que carga
                # são): regrava os dos anos anteriores desta rodada, que acabaram de ser apagados
                self.store.upsert_facts(self._p(sem_data_anteriores))
            sem_data_anteriores += [f for f in fatos if f.atributos.get("data") is None]
            por_ano[ano] = len(fatos)
            com_cnpj += sum(1 for f in fatos if f.atributos.get("cnpj"))
            del fatos  # o ano seguinte não pode começar com este ainda em memória
        self.relatorio["ceap"] = {"despesas": sum(por_ano.values()), "com_cnpj": com_cnpj,
                                  "por_ano": por_ano}

    def _passo_cgu(self) -> None:
        src = self.registry["cgu"]()
        fatos = src.normalize(chamar_fetch(src))
        sancoes = [f for f in fatos if f.tipo == "sancao"]
        relevantes = self._cnpjs_do_escopo() if self.escopo is not None else None
        if relevantes is not None:
            sancoes = [s for s in sancoes if s.atributos.get("cnpj") in relevantes]
        for fonte in {s.fonte for s in sancoes}:
            self.store.delete_facts("sancao", fonte=fonte,
                                    onde={"cnpj": relevantes} if relevantes is not None else None)
        self._gravar(sancoes)

        res = resolver_emendas([f for f in fatos if f.tipo == "emenda"], self.todos_deputados)
        ficam, res_e = self._restringir(res, "emenda")
        for fonte in {e.fonte for e in res.fatos}:
            self.store.delete_facts("emenda", fonte=fonte, onde={"deputado_id": self.escopo}
                                    if self.escopo is not None else None)
        self._gravar(ficam, res_e, origens=[f"emenda:{f.chave}" for f in ficam])
        self.relatorio["cgu"] = {"sancoes": len(sancoes), "emendas": res.resumo(),
                                 "emendas_gravadas": len(ficam)}

    def _partes_tse(self, src: Any, uf: str | None) -> Iterator[tuple[str | None, dict]]:
        """(uf, bruto) de cada parte a processar, uma por vez. Sem UF (modo nacional) usa
        `fetch_por_uf`, que baixa e entrega uma UF de cada vez; com UF (ou numa fonte sem
        `fetch_por_uf`) é o `fetch` de sempre."""
        o = self.opcoes
        pedido = {"ano": o.ano_eleicao, "conjuntos": ("candidatos", "receitas", "votacao"),
                  "reusar_raw": o.reusar_raw}
        if uf is None and callable(getattr(src, "fetch_por_uf", None)):
            for parte in src.fetch_por_uf(None, **pedido):
                yield parte["uf"], parte
                del parte  # senão esta função segura a UF anterior enquanto a próxima é lida
            return
        yield uf, chamar_fetch(src, uf=uf, **pedido)

    def _passo_tse(self) -> None:
        """Uma UF por vez: baixa, normaliza, grava e solta antes de ir para a próxima. No modo
        nacional o pico de memória é o de uma UF, não o das 27 somadas."""
        src = self.registry["tse"]()
        total = {"total": 0, "ligados": 0, "ambiguos": 0, "sem_match": 0}
        contagem = {"gravadas": 0, "doacoes": 0, "votos": 0}
        for uf_escopo in self._ufs_do_escopo():
            partes = self._partes_tse(src, uf_escopo)
            for uf, raw in partes:
                self._gravar_uf_tse(src, raw, uf, total, contagem)
                del raw  # o gerador só solta a UF anterior se ninguém mais a segura
        self.relatorio["tse"] = {"candidaturas": total,
                                 "candidaturas_gravadas": contagem["gravadas"],
                                 "doacoes": contagem["doacoes"],
                                 "votos_municipio": contagem["votos"]}

    def _gravar_uf_tse(self, src: Any, raw: dict, uf: str | None, total: dict[str, int],
                       contagem: dict[str, int]) -> None:
        o = self.opcoes
        cand_raw = src.normalize({"ano": o.ano_eleicao, "candidatos": raw.get("candidatos", [])})
        res = resolver_candidaturas(cand_raw, self.todos_deputados)
        for k, v in res.resumo().items():
            total[k] += v
        ficam, res_c = self._restringir(res, "candidatura")
        sqs = {f.chave for f in ficam if f.atributos.get("deputado_id")}
        self.store.delete_facts("candidatura", fonte=cand_raw[0].fonte if cand_raw else None,
                                onde={"ano": [o.ano_eleicao], **({"uf": [uf]} if uf else {})})
        self._gravar(ficam, res_c, origens=[f"candidatura:{f.chave}" for f in ficam])
        contagem["gravadas"] += len(ficam)

        todos_sq = [f.chave for f in cand_raw]
        doa = src.normalize({"ano": o.ano_eleicao, "receitas": [
            r for r in raw.get("receitas", []) if str(r.get("SQ_CANDIDATO")) in sqs]})
        vot = self._votos_por_municipio(src, raw, sqs, uf)
        for tipo, novos in (("doacao", doa), ("votos_municipio", vot)):
            if novos:
                self.store.delete_facts(tipo, fonte=novos[0].fonte,
                                        onde={"sq_candidato": todos_sq})
        self._gravar(doa + vot)
        contagem["doacoes"] += len(doa)
        contagem["votos"] += len(vot)

    @staticmethod
    def _votos_por_municipio(src: Any, raw: dict, sqs: set[str], uf: str | None) -> list[Fact]:
        """Normaliza a votação município a município (os totais por município continuam certos)
        e já descarta quem não é do escopo: o estado inteiro de uma vez são centenas de milhares
        de fatos que ninguém usa."""
        grupos: dict[str, list[dict]] = defaultdict(list)
        for r in raw.get("votacao", []):
            grupos[str(r.get("CD_MUNICIPIO"))].append(r)
        ibge = [m for m in raw.get("municipios_ibge") or [] if not uf or m.get("uf") == uf]
        out: list[Fact] = []
        for linhas in grupos.values():
            out += [f for f in src.normalize({"ano": raw.get("ano"), "votacao": linhas,
                                              "municipios_ibge": ibge})
                    if f.tipo == "votos_municipio" and f.atributos.get("sq_candidato") in sqs]
        return out

    def _passo_opensanctions(self) -> None:
        src = self.registry["opensanctions"]()
        peps = [f for f in src.normalize(chamar_fetch(src, max_entidades=self.opcoes.max_pep))
                if f.tipo == "pep"]
        cands = self.store.facts_by_tipo("candidatura")
        res = resolver_peps(peps, self.todos_deputados, cands, self.store.load_links("candidatura"))
        ligados = {lk.origem for lk in res.links
                   if self._no_escopo(lk.destino.removeprefix("deputado:"))}
        ficam = [f for f in peps if f"pep:{f.chave}" in ligados]
        links = [lk for lk in res.links if lk.origem in ligados
                 and self._no_escopo(lk.destino.removeprefix("deputado:"))]
        amb = [a for a in res.ambiguos if self.escopo is None or any(
            c.removeprefix("deputado:") in self.escopo for c in a.candidatos)]
        self._gravar(ficam, Resolucao(links=links, ambiguos=amb), origens=sorted(ligados))
        self.relatorio["opensanctions"] = {"peps_lidos": len(peps), **res.resumo(),
                                           "gravados": len(ficam)}

    def _passo_rfb(self) -> None:
        o = self.opcoes
        if o.limite_rfb <= 0:
            self.relatorio["rfb"] = {"consultados": 0}
            return
        src = self.registry["rfb"]()
        cnpjs = self._cnpjs_para_rfb(o.limite_rfb)
        if not cnpjs:
            self.relatorio["rfb"] = {"consultados": 0}
            return
        raw = chamar_fetch(src, cnpjs=cnpjs, reusar_raw=o.reusar_raw)
        fatos = src.normalize(raw)
        self.store.delete_facts("socio", onde={"cnpj": cnpjs})
        self._gravar(fatos)
        indisponiveis = raw.get("indisponiveis", [])
        if indisponiveis:
            self.log(f"    ATENÇÃO: {len(indisponiveis)} CNPJ(s) sem dados da Receita (BrasilAPI "
                     f"indisponível): {', '.join(indisponiveis)}")
        self.relatorio["rfb"] = {"consultados": len(cnpjs),
                                 "empresas": sum(1 for f in fatos if f.tipo == "empresa"),
                                 "socios": sum(1 for f in fatos if f.tipo == "socio"),
                                 "indisponiveis": indisponiveis}

    def _cnpjs_para_rfb(self, limite: int) -> list[str]:
        """Os `limite` CNPJs válidos de maior valor vistos em despesa_ceap/doacao (PJ), menos os
        que já têm `empresa` gravada: re-executar com o mesmo limite não consulta nada de novo."""
        valor: dict[str, float] = defaultdict(float)
        for f in self.store.facts_by_tipo("despesa_ceap"):
            if f.atributos.get("cnpj") and self._no_escopo(f.atributos.get("deputado_id")):
                valor[f.atributos["cnpj"]] += abs(float(f.atributos.get("valor") or 0))
        for f in self.store.facts_by_tipo("doacao"):
            doc = re.sub(r"\D", "", str(f.atributos.get("doador_cpf_cnpj") or ""))
            if len(doc) == 14:
                valor[doc] += abs(float(f.atributos.get("valor") or 0))
        conhecidos = {e.chave for e in self.store.facts_by_tipo("empresa")}
        ranking = [c for c, _ in sorted(valor.items(), key=lambda kv: (-kv[1], kv[0]))
                   if cnpj_valido(c)][:limite]
        return [c for c in ranking if c not in conhecidos]

    def _ligar_cnpj(self) -> None:
        despesas = [f for f in self.store.facts_by_tipo("despesa_ceap")
                    if self._no_escopo(f.atributos.get("deputado_id"))]
        res = resolver_cnpj(despesas, self.store.facts_by_tipo("empresa"),
                            self.store.facts_by_tipo("sancao"))
        self.store.upsert_links(
            res.links, substituir_origens=[f"despesa_ceap:{d.chave}" for d in despesas
                                           if d.atributos.get("cnpj")])
        self.relatorio["links_cnpj"] = {
            "empresa": sum(1 for lk in res.links if lk.destino.startswith("empresa:")),
            "sancao": sum(1 for lk in res.links if lk.destino.startswith("sancao:"))}


# ---------- CLI ----------

def _lista_de_anos(texto: str) -> tuple[int, ...]:
    """'2023,2024' -> (2023, 2024), sem repetição e na ordem dada."""
    partes = [p.strip() for p in texto.split(",")]
    if not all(p.isascii() and p.isdigit() and len(p) == 4 and 2000 <= int(p) <= 2100
               for p in partes):
        raise argparse.ArgumentTypeError(
            f"anos inválidos: {texto!r} (esperado ANO[,ANO...] com 4 dígitos, ex.: 2023,2024)")
    return tuple(dict.fromkeys(int(p) for p in partes))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--fontes", "--fonte", default="camara",
                    help=f"lista separada por vírgula de: {','.join(ORDEM)}")
    ap.add_argument("--uf", help="restringe a uma UF (ex.: MG)")
    ap.add_argument("--ano", type=int, help="ano do arquivo CEAP (com ceap: --ano ou --anos-ceap)")
    ap.add_argument("--anos-ceap", type=_lista_de_anos, default=(), metavar="ANO[,ANO...]",
                    help="vários anos do CEAP, ex.: 2023,2024 (um zip por ano, um ano de cada vez; "
                         "vale no lugar de --ano)")
    ap.add_argument("--ano-eleicao", type=int, default=2022)
    ap.add_argument("--amostra", type=int, help="só os N primeiros deputados (da UF, se dada)")
    ap.add_argument("--limite-rfb", type=int, default=50, help="máx. de CNPJs consultados (0=nenhum)")
    ap.add_argument("--max-votacoes", type=int, default=30)
    ap.add_argument("--janela-inicio", default="2025-01-01")
    ap.add_argument("--janela-fim", default="2025-03-31")
    ap.add_argument("--max-pep", type=int, help="limita entidades lidas do OpenSanctions (teste)")
    ap.add_argument("--reusar-raw", action="store_true",
                    help="usa o bruto já baixado em vez de baixar de novo: Câmara (data/raw/camara/), "
                         "TSE por UF (data/raw/tse/) e Receita por CNPJ (data/raw/rfb/)")
    ap.add_argument("--detalhar-deputados", action="store_true",
                    help="GET /deputados/{id} (cpf, nome civil) só dos deputados do escopo")
    ap.add_argument("--incluir-proposicoes", action="store_true",
                    help="coleta proposicao/autoria (PL, PEC, PLP) dos deputados do escopo")
    ap.add_argument("--max-proposicoes", type=int, default=300,
                    help="teto de proposições (2 chamadas cada); padrão 300")
    ap.add_argument("--pseudonimizar", action="store_true",
                    help="troca o CPF íntegro de terceiros por HMAC-SHA256 (sal em $RAIO_X_ID_SALT)")
    ap.add_argument("--fixture", help="JSON bruto local da Câmara em vez de baixar")
    ap.add_argument("--db", help="arquivo DuckDB (padrão: $RAIO_X_DB ou data/raio_x.duckdb)")
    a = ap.parse_args(argv)
    fontes = tuple(f.strip() for f in a.fontes.split(",") if f.strip())
    op = Opcoes(fontes=fontes, uf=a.uf, ano=a.ano, anos_ceap=a.anos_ceap,
                ano_eleicao=a.ano_eleicao, amostra=a.amostra,
                limite_rfb=a.limite_rfb, max_votacoes=a.max_votacoes,
                janela_inicio=a.janela_inicio, janela_fim=a.janela_fim, max_pep=a.max_pep,
                reusar_raw=a.reusar_raw, detalhar_deputados=a.detalhar_deputados,
                incluir_proposicoes=a.incluir_proposicoes, max_proposicoes=a.max_proposicoes,
                pseudonimizar=a.pseudonimizar,
                fixture=a.fixture)
    rel = Pipeline(Store(a.db), op).executar()
    print(json.dumps(rel, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
