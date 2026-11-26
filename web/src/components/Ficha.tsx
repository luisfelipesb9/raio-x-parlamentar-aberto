import Link from "next/link";
import type { ReactNode } from "react";
import type { Finding, GrafoResposta, PerfilDeputado } from "@/types/contracts";
import { resumoDoGrafo, type BlocoValor, type ResumoGrafo } from "@/lib/resumo";
import { resumoFicha } from "@/lib/ficha-seo";
import { decimaisPtBr, formataPercentual, formataReais, origemDoCadastro } from "@/lib/formato";
import { formataCf } from "@/lib/nivel";
import { AlertaCard } from "./AlertaCard";
import { AvisoNaoAcusacao } from "./Aviso";
import { Vazio } from "./Estados";
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

/**
 * Ficha do deputado. Componente de SERVIDOR: recebe os dados já buscados (a página usa ISR) e o HTML inicial
 * já traz nome, resumo, alertas e aviso de não acusação. Só os pedaços interativos (Termo, AlertaCard, Revela,
 * Foto, PainelDados) são componentes de cliente próprios.
 */
export function Ficha({ perfil: p, findings, grafo }: { perfil: PerfilDeputado; findings: Finding[]; grafo: GrafoResposta | null }) {
  const lista = [...findings].sort((a, b) => b.cf - a.cf);
  const resumo = grafo ? resumoDoGrafo(grafo) : null;
  const truncado = grafo?.truncado === true;
  const intro = resumoFicha(p, lista);

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
          <p className="lead">
            {intro.frase} {intro.alertas}
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
              {p.uf ? <>, eleito(a) por <strong>{p.uf}</strong></> : null}. {origemDoCadastro(p.foto)}
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
            <Parecidos resumo={resumo} />
          </SecaoFicha>

          <SecaoFicha id="gasta" titulo="Quanto gasta">
            <p>
              Gastos pagos com a <Termo id="ceap">cota parlamentar (CEAP)</Termo>: dinheiro público com nota fiscal.
            </p>
            <AlertasDaSecao secao="gasta" lista={lista} />
            <BlocoGrafo resumo={resumo} bloco={(r) => r.gastos} titulo="Quem mais recebeu da cota" vazio="Não há despesas da cota registradas para este deputado nesta base. Isso não permite concluir nada: a fonte pode ainda não ter sido carregada." rotuloTotal="pago a" unidade="fornecedores" truncado={truncado} />
          </SecaoFicha>

          <SecaoFicha id="dinheiro" titulo="Para onde mandou dinheiro">
            <p>
              Dinheiro do orçamento que o deputado indicou por <Termo id="emenda">emendas</Termo> (inclui a <Termo id="emenda-pix">emenda Pix</Termo>), por município.
            </p>
            <AlertasDaSecao secao="dinheiro" lista={lista} />
            <BlocoGrafo resumo={resumo} bloco={(r) => r.emendas} titulo="Municípios que mais receberam" vazio="Não há emendas registradas para este deputado nesta base." rotuloTotal="indicados para" unidade="municípios" truncado={truncado} />
          </SecaoFicha>

          <SecaoFicha id="financiou" titulo="Quem financiou">
            <p>Pessoas e empresas que doaram para a campanha, segundo a Justiça Eleitoral (TSE).</p>
            <AlertasDaSecao secao="financiou" lista={lista} />
            <BlocoGrafo resumo={resumo} bloco={(r) => r.doacoes} titulo="Maiores doadores" vazio="Não há doações registradas para este deputado nesta base." rotuloTotal="doados por" unidade="doadores" truncado={truncado} />
          </SecaoFicha>

          <SecaoFicha id="alertas" titulo="Alertas">
            {lista.length === 0 && (
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
            {lista.length > 0 && (
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

function AlertasDaSecao({ secao, lista, vazio }: { secao: Secao; lista: Finding[]; vazio?: string }) {
  const daSecao = lista.filter((f) => SECAO_DA_REGRA[f.regra] === secao);
  if (daSecao.length === 0) return vazio ? <p className="nota">{vazio}</p> : null;
  return (
    <ul className="resumo-alertas" aria-label="Alertas desta seção">
      {daSecao.map((f) => (
        <li key={f.id}>
          <SeloCerteza nivel={f.nivel} />
          <span>
            {decimaisPtBr(f.conclusao)}{" "}
            <a href={`#alerta-${f.id}`}>
              Ver detalhes<span className="visually-hidden"> do alerta {f.regra}</span>
            </a>
          </span>
        </li>
      ))}
    </ul>
  );
}

type PropsBloco = { resumo: ResumoGrafo | null; bloco: (r: ResumoGrafo) => BlocoValor; titulo: string; vazio: string; rotuloTotal: string; unidade: string; truncado: boolean };

function BlocoGrafo({ resumo, bloco, titulo, vazio, rotuloTotal, unidade, truncado }: PropsBloco) {
  if (resumo === null) return <p className="nota">Os valores desta seção não puderam ser carregados agora. Tente de novo em instantes ou veja o mapa de relações.</p>;
  const b = bloco(resumo);
  if (b.n === 0) return <p className="nota">{vazio}</p>;
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
      {truncado && <p className="nota">Lista parcial: o mapa tem mais nós do que o limite de exibição.</p>}
    </div>
  );
}

function Parecidos({ resumo }: { resumo: ResumoGrafo | null }) {
  const lista = resumo?.parecidos ?? [];
  if (lista.length === 0) return null;
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
