"use client";

import Link from "next/link";
import { useMemo, type ReactNode } from "react";
import type { Finding, GrafoResposta, PerfilDeputado } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { resumoDoGrafo, type BlocoValor, type Parecido } from "@/lib/resumo";
import { formataPercentual, formataReais } from "@/lib/formato";
import { formataCf } from "@/lib/nivel";
import { AlertaCard } from "./AlertaCard";
import { AvisoNaoAcusacao } from "./Aviso";
import { Carregando, ErroApi, Vazio } from "./Estados";
import { Foto } from "./Foto";
import { PainelDados } from "./PainelDados";
import { Revela } from "./Revela";
import { SeloCerteza } from "./SeloCerteza";
import { Termo } from "./Termo";

type Secao = "quem" | "vota" | "gasta" | "dinheiro" | "financiou";

/** Em que seção da ficha cada regra "mora" (o cartão completo fica sempre em Alertas). */
const SECAO_DA_REGRA: Record<string, Secao> = {
  R01: "vota",
  R03: "gasta",
  R04: "gasta",
  R05: "quem",
  R06: "financiou",
  R06b: "financiou",
  R07: "dinheiro",
};

const SECOES: { id: Secao | "alertas" | "dados"; titulo: string }[] = [
  { id: "quem", titulo: "Quem é" },
  { id: "vota", titulo: "Como vota" },
  { id: "gasta", titulo: "Quanto gasta" },
  { id: "dinheiro", titulo: "Para onde mandou dinheiro" },
  { id: "financiou", titulo: "Quem financiou" },
  { id: "alertas", titulo: "Alertas" },
  { id: "dados", titulo: "Dados e verificação" },
];

export function Ficha({ id }: { id: string }) {
  const perfil = useApi<PerfilDeputado>(`/deputados/${encodeURIComponent(id)}`);
  const findings = useApi<Finding[]>(`/deputados/${encodeURIComponent(id)}/findings`);
  const grafo = useApi<GrafoResposta>(perfil.estado.status === "ok" ? "/grafo" : null, { centro: `deputado:${id}`, profundidade: 1 });

  if (perfil.estado.status === "carregando" || perfil.estado.status === "ocioso") return <Carregando texto="Carregando a ficha…" />;
  if (perfil.estado.status === "erro")
    return <ErroApi erro={perfil.estado.erro} onTentarDeNovo={perfil.recarregar} voltar={{ href: "/", texto: "Voltar à busca" }} />;

  const p = perfil.estado.data;
  const lista = findings.estado.status === "ok" ? [...findings.estado.data].sort((a, b) => b.cf - a.cf) : null;

  return (
    <article className="ficha">
      <header className="ficha-topo">
        <span className="foto-anel">
          <Foto src={p.foto} nome={p.nome} tamanho={112} descrever />
        </span>
        <div>
          <p className="eyebrow">Ficha do deputado federal</p>
          <h1>{p.nome}</h1>
          <p className="ficha-meta">
            {[p.partido, p.uf].filter(Boolean).join(" · ")}
            {p.n_findings > 0 ? ` · ${p.n_findings} ${p.n_findings === 1 ? "alerta" : "alertas"}` : " · sem alertas"}
          </p>
          <ul className="acoes acoes-lista">
            <li>
              <Link className="btn btn-sec" href={`/grafo?centro=${encodeURIComponent(`deputado:${p.id}`)}`}>
                Ver mapa de relações
              </Link>
            </li>
            <li>
              <Link className="btn btn-sec" href={`/perguntar?deputado=${encodeURIComponent(p.id)}`}>
                Perguntar ao sistema
              </Link>
            </li>
            <li>
              <Link className="btn btn-sec" href={`/comparar?a=${encodeURIComponent(p.id)}`}>
                Comparar com outro
              </Link>
            </li>
          </ul>
        </div>
      </header>

      <AvisoNaoAcusacao />

      <div className="ficha-corpo">
        <nav className="ficha-indice" aria-label="Nesta ficha">
          <ul>
            {SECOES.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`}>{s.titulo}</a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="ficha-secoes">
          <SecaoFicha id="quem" titulo="Quem é">
            <p>
              Deputado(a) federal pelo <strong>{p.partido ?? "partido não informado"}</strong>
              {p.uf ? <>, eleito(a) por <strong>{p.uf}</strong></> : null}. Cadastro e foto oficiais da Câmara dos Deputados.
            </p>
            <p>
              <a href={`https://www.camara.leg.br/deputados/${encodeURIComponent(p.id)}`} target="_blank" rel="noopener noreferrer">
                Abrir a página oficial na Câmara<span className="visually-hidden"> (abre em nova aba)</span>
              </a>
            </p>
            <AlertasDaSecao secao="quem" lista={lista} vazio="Ainda não há análise de produção legislativa (projetos de que foi autor ou relator) nesta base." />
          </SecaoFicha>

          <SecaoFicha id="vota" titulo="Como vota">
            <p>
              Só contamos <Termo id="votacao-nominal">votação nominal</Termo>, a única em que o voto de cada deputado fica registrado. Em{" "}
              <Termo id="votacao-simbolica">votação simbólica</Termo> ninguém vota individualmente, então ela nunca entra na conta. A{" "}
              <Termo id="orientacao-governo">orientação do governo</Termo> é usada como referência.
            </p>
            <AlertasDaSecao secao="vota" lista={lista} vazio="Não há análise de votações para este deputado nesta base." />
            <Parecidos estado={grafo.estado} />
          </SecaoFicha>

          <SecaoFicha id="gasta" titulo="Quanto gasta">
            <p>
              Gastos pagos com a <Termo id="ceap">cota parlamentar (CEAP)</Termo>: dinheiro público com nota fiscal.
            </p>
            <AlertasDaSecao secao="gasta" lista={lista} />
            <BlocoGrafo estado={grafo.estado} bloco={(r) => r.gastos} titulo="Quem mais recebeu da cota" vazio="Não há despesas da cota registradas para este deputado nesta base. Isso não permite concluir nada: a fonte pode ainda não ter sido carregada." rotuloTotal="pago a" unidade="fornecedores" />
          </SecaoFicha>

          <SecaoFicha id="dinheiro" titulo="Para onde mandou dinheiro">
            <p>
              Dinheiro do orçamento que o deputado indicou por <Termo id="emenda">emendas</Termo> (inclui a <Termo id="emenda-pix">emenda Pix</Termo>), por município.
            </p>
            <AlertasDaSecao secao="dinheiro" lista={lista} />
            <BlocoGrafo estado={grafo.estado} bloco={(r) => r.emendas} titulo="Municípios que mais receberam" vazio="Não há emendas registradas para este deputado nesta base." rotuloTotal="indicados para" unidade="municípios" />
          </SecaoFicha>

          <SecaoFicha id="financiou" titulo="Quem financiou">
            <p>Pessoas e empresas que doaram para a campanha, segundo a Justiça Eleitoral (TSE).</p>
            <AlertasDaSecao secao="financiou" lista={lista} />
            <BlocoGrafo estado={grafo.estado} bloco={(r) => r.doacoes} titulo="Maiores doadores" vazio="Não há doações registradas para este deputado nesta base." rotuloTotal="doados por" unidade="doadores" />
          </SecaoFicha>

          <SecaoFicha id="alertas" titulo="Alertas">
            {findings.estado.status === "carregando" && <Carregando texto="Carregando alertas…" />}
            {findings.estado.status === "erro" && <ErroApi erro={findings.estado.erro} onTentarDeNovo={findings.recarregar} />}
            {lista && lista.length === 0 && (
              <Vazio titulo="Nenhum alerta para este deputado">
                <p>
                  A ausência de alerta não quer dizer que esteja tudo certo: significa só que o sistema não encontrou, nos dados que já
                  carregou, nada que ative uma de suas regras.
                </p>
                <p>
                  Próximos passos: <a href="#dados">veja os dados e a cobertura</a>, <Link href={`/perguntar?deputado=${encodeURIComponent(p.id)}`}>pergunte ao sistema</Link> ou{" "}
                  <Link href="/fontes">entenda o método</Link>.
                </p>
              </Vazio>
            )}
            {lista && lista.length > 0 && (
              <>
                <p>
                  Cada cartão traz o nível de certeza, o botão <em>Como sabemos disso?</em> (passo a passo) e o botão <em>Verificar na fonte</em> (documentos oficiais, com identificador e data de coleta).
                </p>
                <div className="alertas">
                  {lista.map((f) => (
                    <AlertaCard key={f.id} finding={f} />
                  ))}
                </div>
              </>
            )}
          </SecaoFicha>

          <SecaoFicha id="dados" titulo="Dados e verificação">
            <PainelDados deputadoId={p.id} />
          </SecaoFicha>
        </div>
      </div>
    </article>
  );
}

function SecaoFicha({ id, titulo, children }: { id: string; titulo: string; children: ReactNode }) {
  return (
    <Revela id={id} className="secao" rotulo={`h-${id}`}>
      <h2 id={`h-${id}`}>{titulo}</h2>
      {children}
    </Revela>
  );
}

function AlertasDaSecao({ secao, lista, vazio }: { secao: Secao; lista: Finding[] | null; vazio?: string }) {
  const daSecao = useMemo(() => (lista ?? []).filter((f) => SECAO_DA_REGRA[f.regra] === secao), [lista, secao]);
  if (lista === null) return null;
  if (daSecao.length === 0) return vazio ? <p className="nota">{vazio}</p> : null;
  return (
    <ul className="resumo-alertas" aria-label="Alertas desta seção">
      {daSecao.map((f) => (
        <li key={f.id}>
          <SeloCerteza nivel={f.nivel} />
          <span>
            {f.conclusao}{" "}
            <a href={`#alerta-${f.id}`}>
              Ver detalhes<span className="visually-hidden"> do alerta {f.regra}</span>
            </a>
          </span>
        </li>
      ))}
    </ul>
  );
}

type EstadoGrafo = ReturnType<typeof useApi<GrafoResposta>>["estado"];

function BlocoGrafo({ estado, bloco, titulo, vazio, rotuloTotal, unidade }: { estado: EstadoGrafo; bloco: (r: ReturnType<typeof resumoDoGrafo>) => BlocoValor; titulo: string; vazio: string; rotuloTotal: string; unidade: string }) {
  const resumo = useMemo(() => (estado.status === "ok" ? resumoDoGrafo(estado.data) : null), [estado]);
  if (estado.status === "carregando" || estado.status === "ocioso") return <Carregando texto="Carregando relações…" />;
  if (estado.status === "erro") return <p className="nota">Não foi possível carregar os valores desta seção ({estado.erro.mensagemParaLeigo})</p>;
  const b = resumo ? bloco(resumo) : null;
  if (!b || b.n === 0) return <p className="nota">{vazio}</p>;
  return (
    <div className="bloco-valor">
      <p className="bloco-total">
        <strong>{formataReais(b.total)}</strong> {rotuloTotal} {b.n} {unidade}
        {b.sancionados > 0 && (
          <>
            , dos quais <strong>{b.sancionados}</strong> com sanção registrada (<Termo id="ceis-cnep">CEIS/CNEP</Termo>)
          </>
        )}
        .
      </p>
      <h3 className="bloco-titulo">{titulo}</h3>
      <ol className="ranking">
        {b.itens.map((i) => (
          <li key={i.no.id}>
            <Link href={`/grafo?centro=${encodeURIComponent(i.no.id)}`} className="ranking-nome">
              {i.no.rotulo}
            </Link>
            {i.no.atributos["sancionada"] === true && <span className="tag-sancao">Sanção registrada</span>}
            <span className="ranking-valor">{formataReais(i.valor)}</span>
          </li>
        ))}
      </ol>
      {estado.status === "ok" && estado.data.truncado && (
        <p className="nota">Lista parcial: o mapa tem mais nós do que o limite de exibição.</p>
      )}
    </div>
  );
}

function Parecidos({ estado }: { estado: EstadoGrafo }) {
  const lista: Parecido[] = useMemo(() => (estado.status === "ok" ? resumoDoGrafo(estado.data).parecidos : []), [estado]);
  if (estado.status !== "ok" || lista.length === 0) return null;
  return (
    <div className="bloco-valor">
      <h3 className="bloco-titulo">Vota parecido com</h3>
      <ol className="ranking">
        {lista.map((p) => (
          <li key={p.no.id}>
            <Link href={`/deputado/${encodeURIComponent(p.no.id.replace(/^deputado:/, ""))}`} className="ranking-nome">
              {p.no.rotulo}
            </Link>
            <span className="ranking-valor">
              {formataPercentual(p.afinidade)} dos votos iguais <small>(<Termo id="cf">CF</Termo> {formataCf(p.cf)})</small>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
