/**
 * Dados estruturados (schema.org) em JSON-LD. Funções puras: recebem dados e devolvem objetos prontos
 * para o componente `JsonLd`. Regras:
 * - o que está no schema tem de estar visível na página que o usa;
 * - nada aqui afirma licença dos dados nem insinua culpa (sem alertas, achados ou acusações);
 * - o texto vindo de dados só tem os espaços normalizados (conteúdo intacto); quem impede o texto de fechar a tag
 *   <script> é o componente `JsonLd`, que escapa "<" na hora de renderizar.
 */
import type { Termo } from "./glossario";
import { DESCRICAO_PADRAO, NOME_SITE, SITE_URL, urlAbsoluta } from "./seo";

export const REPO_URL = "https://github.com/luisfelipesb9/raio-x-parlamentar-aberto";
export const LICENCAS_DADOS_URL = `${REPO_URL}/blob/main/DATA_LICENSES.md`;

const CONTEXTO = "https://schema.org";
const ID_ORGANIZACAO = `${SITE_URL}/#organizacao`;

/** Normaliza espaços (sem alterar o conteúdo). */
function texto(valor: string): string {
  return valor.replace(/\s+/g, " ").trim();
}

/** Aceita só endereço https; qualquer outra coisa (http, javascript:, data:...) vira undefined. */
function urlHttp(valor: string | null | undefined): string | undefined {
  if (!valor) return undefined;
  try {
    const u = new URL(valor);
    return u.protocol === "https:" ? u.href : undefined;
  } catch {
    return undefined;
  }
}

export function organizacaoLd() {
  return {
    "@context": CONTEXTO,
    "@type": "Organization",
    "@id": ID_ORGANIZACAO,
    name: NOME_SITE,
    url: SITE_URL,
    logo: urlAbsoluta("/icon.svg"),
    description: "Projeto acadêmico de código aberto que explica, em linguagem simples, o que é público sobre deputados federais.",
    sameAs: [REPO_URL],
  };
}

/** O site. Sem `potentialAction` de busca: a busca é feita no navegador e o Google aposentou a caixa de busca nos resultados. */
export function siteLd() {
  return {
    "@context": CONTEXTO,
    "@type": "WebSite",
    "@id": `${SITE_URL}/#site`,
    name: NOME_SITE,
    url: SITE_URL,
    description: DESCRICAO_PADRAO,
    inLanguage: "pt-BR",
    publisher: { "@id": ID_ORGANIZACAO },
  };
}

/**
 * Fontes oficiais que a ingestão usa de fato (as mesmas que /fontes mostra). A Receita Federal entra "via BrasilAPI"
 * porque hoje o CNPJ é consultado por lá, só para uma amostra de CNPJs.
 */
const FONTES_OFICIAIS = [
  { name: "Câmara dos Deputados, Dados Abertos (cadastro, votações, projetos e cota parlamentar)", url: "https://dadosabertos.camara.leg.br/" },
  { name: "Tribunal Superior Eleitoral, Portal de Dados Abertos (candidaturas, doações e votos)", url: "https://dadosabertos.tse.jus.br/" },
  { name: "Controladoria-Geral da União, Portal da Transparência (CEIS, CNEP e emendas)", url: "https://portaldatransparencia.gov.br/" },
  { name: "Receita Federal, Cadastro Nacional da Pessoa Jurídica (CNPJ), via BrasilAPI", url: "https://brasilapi.com.br/" },
  { name: "OpenSanctions, lista de pessoas politicamente expostas do Brasil (br_pep)", url: "https://www.opensanctions.org/datasets/br_pep/" },
] as const;

/**
 * A base de dados do projeto. Não declara `license`: as condições de cada fonte estão em DATA_LICENSES.md
 * (algumas ainda "a confirmar"), apontado por `usageInfo`. `atualizadoEm` é a data da última coleta (opcional).
 */
export function datasetLd(opcoes: { atualizadoEm?: string | null } = {}) {
  const quando = opcoes.atualizadoEm ? new Date(opcoes.atualizadoEm) : null;
  const dateModified = quando && !Number.isNaN(quando.getTime()) ? quando.toISOString().slice(0, 10) : undefined;
  return {
    "@context": CONTEXTO,
    "@type": "Dataset",
    name: "Base de dados do Raio-X Parlamentar",
    description:
      "Fatos públicos sobre deputados federais (votações, gastos da cota parlamentar, emendas, candidaturas e cadastros oficiais), cada um com a fonte oficial e a data de coleta, e os padrões que o sistema encontra neles, com nível de certeza.",
    url: urlAbsoluta("/fontes"),
    inLanguage: "pt-BR",
    isAccessibleForFree: true,
    creator: { "@id": ID_ORGANIZACAO },
    isBasedOn: FONTES_OFICIAIS.map((f) => ({ "@type": "CreativeWork", name: f.name, url: f.url })),
    usageInfo: LICENCAS_DADOS_URL,
    ...(dateModified ? { dateModified } : {}),
  };
}

export function breadcrumbLd(itens: ReadonlyArray<{ nome: string; caminho: string }>) {
  return {
    "@context": CONTEXTO,
    "@type": "BreadcrumbList",
    itemListElement: itens.map((i, idx) => ({
      "@type": "ListItem",
      position: idx + 1,
      name: texto(i.nome),
      item: urlAbsoluta(i.caminho),
    })),
  };
}

export type PerfilParaLd = {
  id: string;
  nome: string;
  partido?: string | null;
  uf?: string | null;
  foto?: string | null;
};

/** Deputado como pessoa pública: cargo, partido e ficha. Só identificação; nenhum alerta ou achado entra aqui. */
export function pessoaLd(perfil: PerfilParaLd) {
  const nome = texto(perfil.nome);
  const partido = perfil.partido ? texto(perfil.partido) : "";
  const uf = perfil.uf ? texto(perfil.uf) : "";
  const imagem = urlHttp(perfil.foto);
  const ficha = urlAbsoluta(`/deputado/${encodeURIComponent(perfil.id)}`);
  return {
    "@context": CONTEXTO,
    "@type": "Person",
    "@id": `${ficha}#pessoa`,
    name: nome,
    jobTitle: "Deputado(a) Federal",
    url: ficha,
    ...(partido ? { affiliation: { "@type": "Organization", name: partido } } : {}),
    ...(partido || uf ? { description: `Deputado(a) federal (${[partido, uf].filter(Boolean).join("-")}).` } : {}),
    ...(imagem ? { image: imagem } : {}),
    ...(/^\d+$/.test(perfil.id) ? { sameAs: [`https://www.camara.leg.br/deputados/${perfil.id}`] } : {}),
  };
}

/** O glossário como conjunto de termos definidos (mesmo texto que a página mostra). */
export function termosLd(termos: ReadonlyArray<Termo>) {
  const urlGlossario = urlAbsoluta("/glossario");
  return {
    "@context": CONTEXTO,
    "@type": "DefinedTermSet",
    name: "Glossário do Raio-X Parlamentar",
    url: urlGlossario,
    inLanguage: "pt-BR",
    hasDefinedTerm: termos.map((t) => ({
      "@type": "DefinedTerm",
      name: texto(t.termo),
      termCode: t.id,
      description: texto(t.porQueImporta ? `${t.definicao} ${t.porQueImporta}` : t.definicao),
      url: `${urlGlossario}#${encodeURIComponent(t.id)}`,
      inDefinedTermSet: urlGlossario,
    })),
  };
}

/** FAQPage. Só use quando a página mostrar essas mesmas perguntas e respostas. Sem perguntas, devolve null. */
export function faqLd(pares: ReadonlyArray<{ pergunta: string; resposta: string }>) {
  if (pares.length === 0) return null;
  return {
    "@context": CONTEXTO,
    "@type": "FAQPage",
    mainEntity: pares.map((p) => ({
      "@type": "Question",
      name: texto(p.pergunta),
      acceptedAnswer: { "@type": "Answer", text: texto(p.resposta) },
    })),
  };
}

/** Artigo técnico (método, regras, dados, guia). Só diz o que a página mostra; a data só entra se for AAAA-MM-DD válida. */
export function artigoLd(opcoes: { titulo: string; descricao: string; caminho: string; atualizado?: string | null }) {
  const url = urlAbsoluta(opcoes.caminho);
  const atualizado = opcoes.atualizado && /^\d{4}-\d{2}-\d{2}$/.test(opcoes.atualizado) && !Number.isNaN(new Date(opcoes.atualizado).getTime()) ? opcoes.atualizado : undefined;
  return {
    "@context": CONTEXTO,
    "@type": "TechArticle",
    headline: texto(opcoes.titulo),
    description: texto(opcoes.descricao),
    url,
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    inLanguage: "pt-BR",
    isAccessibleForFree: true,
    author: { "@id": ID_ORGANIZACAO },
    publisher: { "@id": ID_ORGANIZACAO },
    ...(atualizado ? { dateModified: atualizado } : {}),
  };
}

/** Um termo do glossário na própria página. Mesmo texto que a página mostra. */
export function termoLd(t: Termo) {
  const urlGlossario = urlAbsoluta("/glossario");
  return {
    "@context": CONTEXTO,
    "@type": "DefinedTerm",
    name: texto(t.termo),
    termCode: t.id,
    description: texto(t.porQueImporta ? `${t.definicao} ${t.porQueImporta}` : t.definicao),
    url: `${urlGlossario}/${encodeURIComponent(t.id)}`,
    inLanguage: "pt-BR",
    inDefinedTermSet: urlGlossario,
  };
}
