/** Corpo das páginas de conteúdo. Recebem os dados por props (as rotas passam `CONTEUDO`), então testam-se com fixtures. */
import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import { artigoLd, breadcrumbLd, faqLd, termoLd } from "@/lib/jsonld";
import type { Termo } from "@/lib/glossario";
import { markdownParaReact, markdownParaTexto, perguntasDoFaq } from "@/lib/markdown";
import { canonical, limitaDescricao } from "@/lib/seo";
import { PaginaConteudo, type Migalha } from "./PaginaConteudo";
import { ROTA_DA_PAGINA } from "./rotas";
import type { ArquivoPagina, Conteudo, PaginaConteudo as Pagina, RegraConteudo } from "./tipos";

const INICIO: Migalha = { nome: "Início", caminho: "/" };

export function metadadosDe(o: { titulo: string; descricao: string; caminho: string }): Metadata {
  const descricao = limitaDescricao(o.descricao);
  return {
    title: o.titulo,
    description: descricao,
    alternates: canonical(o.caminho),
    openGraph: { type: "article", title: o.titulo, description: descricao, url: o.caminho, locale: "pt_BR" },
  };
}

export const NOMES: Record<ArquivoPagina, string> = {
  metodo: "Método",
  "para-estudantes": "Para estudantes",
  "dados-e-api": "Dados e API",
  faq: "Perguntas frequentes",
};

/** Links para as outras páginas de conteúdo que existem (menos a atual). */
function vejaTambem(c: Conteudo, atual: string): Migalha[] {
  const links: Migalha[] = [];
  const pagina = (a: ArquivoPagina) => {
    if (c.paginas[a]) links.push({ nome: NOMES[a], caminho: ROTA_DA_PAGINA[a] });
  };
  pagina("metodo");
  if (c.regras.length > 0) links.push({ nome: "Regras do sistema", caminho: "/regras" });
  pagina("faq");
  links.push({ nome: "Glossário", caminho: "/glossario" });
  pagina("dados-e-api");
  pagina("para-estudantes");
  return links.filter((l) => l.caminho !== atual);
}

type PropsTexto = { pagina: Pagina; caminho: string; nome: string; conteudo: Conteudo };

/** Método, Para estudantes e Dados e API: texto do arquivo, convertido em Markdown seguro. */
export function PaginaTexto({ pagina, caminho, nome, conteudo }: PropsTexto) {
  const migalhas = [INICIO, { nome, caminho }];
  return (
    <PaginaConteudo
      titulo={pagina.titulo}
      resposta={pagina.resposta}
      atualizado={pagina.atualizado}
      migalhas={migalhas}
      jsonld={[artigoLd({ titulo: pagina.titulo, descricao: pagina.descricao, caminho, atualizado: pagina.atualizado }), breadcrumbLd(migalhas)]}
      vejaTambem={vejaTambem(conteudo, caminho)}
    >
      {markdownParaReact(pagina.corpo)}
    </PaginaConteudo>
  );
}

export function PaginaFaq({ pagina, conteudo }: { pagina: Pagina; conteudo: Conteudo }) {
  const caminho = ROTA_DA_PAGINA.faq;
  const migalhas = [INICIO, { nome: NOMES.faq, caminho }];
  const perguntas = perguntasDoFaq(pagina.corpo);
  const faq = faqLd(perguntas.map((p) => ({ pergunta: p.pergunta, resposta: markdownParaTexto(p.resposta) })));
  return (
    <PaginaConteudo
      titulo={pagina.titulo}
      resposta={pagina.resposta}
      atualizado={pagina.atualizado}
      migalhas={migalhas}
      jsonld={[artigoLd({ titulo: pagina.titulo, descricao: pagina.descricao, caminho, atualizado: pagina.atualizado }), breadcrumbLd(migalhas), ...(faq ? [faq] : [])]}
      vejaTambem={vejaTambem(conteudo, caminho)}
    >
      <div className="faq-lista">
        {perguntas.map((p) => (
          <details key={p.pergunta}>
            <summary>{p.pergunta}</summary>
            <div>{markdownParaReact(p.resposta)}</div>
          </details>
        ))}
      </div>
    </PaginaConteudo>
  );
}

// ---------- regras ----------

const TIPOS: Record<string, string> = {
  inferencia: "Regra de inferência: gera uma conclusão com nível de certeza",
  guardrail: "Salvaguarda (guardrail): não gera conclusão, só impede que o sistema erre ou invente",
};
const TIPOS_CURTOS: Record<string, string> = { inferencia: "Regra de inferência", guardrail: "Salvaguarda" };
const CATEGORIAS: Record<string, string> = {
  votacao: "Votações",
  gastos: "Gastos",
  integridade: "Integridade",
  producao: "Produção legislativa",
  emendas: "Emendas",
  geral: "Geral",
};

const numero = (n: number) => String(n).replace(".", ",");
const valor = (v: string | number | boolean) => (typeof v === "number" ? numero(v) : typeof v === "boolean" ? (v ? "sim" : "não") : v);

/** Bloco gerado a partir do YAML da regra: nunca digitado à mão. */
function ParametrosDaRegra({ regra }: { regra: RegraConteudo }) {
  const linhas: [string, ReactNode][] = [];
  linhas.push(["Tipo", TIPOS[regra.tipo] ?? regra.tipo]);
  linhas.push(["Categoria", CATEGORIAS[regra.categoria] ?? regra.categoria]);
  if (regra.composta) linhas.push(["Funcionamento", "Regra composta: só é avaliada no encadeamento regressivo, a pedido de um objetivo"]);
  if (regra.requer.length > 0)
    linhas.push([
      "Depende de",
      regra.requer.map((r, i) => (
        <span key={r}>
          {i > 0 && ", "}
          <code>{r}</code>
        </span>
      )),
    ]);
  if (regra.se) linhas.push(["Condição", <code key="se">{regra.se}</code>]);
  const params = Object.entries(regra.parametros);
  if (params.length > 0)
    linhas.push([
      "Parâmetros",
      <ul key="p">
        {params.map(([k, v]) => (
          <li key={k}>
            <code>{k}</code>: {valor(v)}
          </li>
        ))}
      </ul>,
    ]);
  if (typeof regra.cf === "number") linhas.push(["Confiança do especialista (cf, de 0 a 1)", numero(regra.cf)]);
  if (regra.penalidades.length > 0)
    linhas.push([
      "Quando a certeza diminui",
      <ul key="pen">
        {regra.penalidades.map((p) => (
          <li key={p.se}>
            Se <code>{p.se}</code>: × {numero(p.fator)}. {p.motivo}.
          </li>
        ))}
      </ul>,
    ]);
  if (regra.limitacoes.length > 0)
    linhas.push([
      "Limitações",
      <ul key="lim">
        {regra.limitacoes.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>,
    ]);
  if (regra.fonteMetodologica) linhas.push(["Fonte metodológica", regra.fonteMetodologica]);
  return (
    <section className="regra-parametros" aria-labelledby="parametros-regra">
      <h2 id="parametros-regra">Parâmetros desta regra</h2>
      <dl>
        {linhas.map(([rotulo, v]) => (
          <div key={rotulo} style={{ display: "contents" }}>
            <dt>{rotulo}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function PaginaRegra({ regra, conteudo }: { regra: RegraConteudo; conteudo: Conteudo }) {
  const caminho = `/regras/${regra.id}`;
  const texto = regra.texto;
  const titulo = texto?.titulo ?? `${regra.id}: ${regra.nome}`;
  const resposta = texto?.resposta ?? regra.porQue ?? `Regra ${regra.id}: ${regra.nome}.`;
  const descricao = texto?.descricao ?? resposta;
  const migalhas = [INICIO, { nome: "Regras do sistema", caminho: "/regras" }, { nome: regra.id, caminho }];
  return (
    <PaginaConteudo
      titulo={titulo}
      resposta={resposta}
      atualizado={texto?.atualizado}
      migalhas={migalhas}
      jsonld={[artigoLd({ titulo, descricao, caminho, atualizado: texto?.atualizado }), breadcrumbLd(migalhas)]}
      vejaTambem={vejaTambem(conteudo, caminho)}
    >
      {texto && markdownParaReact(texto.corpo)}
      <ParametrosDaRegra regra={regra} />
    </PaginaConteudo>
  );
}

export const RESPOSTA_INDICE_REGRAS =
  "O sistema decide com regras escritas em arquivos abertos: cada uma diz o que olha nos dados, a partir de que limite e com que nível de certeza.";

export function PaginaIndiceRegras({ conteudo }: { conteudo: Conteudo }) {
  const migalhas = [INICIO, { nome: "Regras do sistema", caminho: "/regras" }];
  return (
    <PaginaConteudo
      titulo="Regras do sistema"
      resposta={RESPOSTA_INDICE_REGRAS}
      migalhas={migalhas}
      jsonld={[breadcrumbLd(migalhas)]}
      vejaTambem={vejaTambem(conteudo, "/regras")}
    >
      <ul className="regras-lista">
        {conteudo.regras.map((r) => {
          const resumo = r.texto?.resposta ?? r.porQue;
          return (
            <li key={r.id}>
              <Link href={`/regras/${r.id}`}>
                <strong>{r.id}</strong>: {r.nome}
              </Link>
              <span className="regra-meta">
                {TIPOS_CURTOS[r.tipo] ?? r.tipo} · {CATEGORIAS[r.categoria] ?? r.categoria}
              </span>
              {resumo && <p>{resumo}</p>}
            </li>
          );
        })}
      </ul>
    </PaginaConteudo>
  );
}

// ---------- glossário ----------

export function PaginaTermo({ termo, conteudo }: { termo: Termo; conteudo: Conteudo }) {
  const caminho = `/glossario/${termo.id}`;
  const migalhas = [INICIO, { nome: "Glossário", caminho: "/glossario" }, { nome: termo.termo, caminho }];
  return (
    <PaginaConteudo
      titulo={termo.termo}
      resposta={termo.definicao}
      migalhas={migalhas}
      jsonld={[termoLd(termo), breadcrumbLd(migalhas)]}
      vejaTambem={vejaTambem(conteudo, caminho)}
    >
      {termo.porQueImporta && <p>{termo.porQueImporta}</p>}
    </PaginaConteudo>
  );
}
