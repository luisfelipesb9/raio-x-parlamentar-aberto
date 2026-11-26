import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { JsonLd } from "@/components/JsonLd";
import { GLOSSARIO } from "./glossario";
import {
  LICENCAS_DADOS_URL,
  REPO_URL,
  breadcrumbLd,
  datasetLd,
  faqLd,
  organizacaoLd,
  pessoaLd,
  siteLd,
  termosLd,
} from "./jsonld";
import { SITE_URL } from "./seo";

/** O que o navegador/robô realmente lê: o objeto serializado e lido de volta. */
function ciclo(o: unknown): Record<string, unknown> {
  return JSON.parse(JSON.stringify(o)) as Record<string, unknown>;
}

/** O HTML que o servidor realmente entrega para estes dados (com o escape do componente JsonLd). */
function html(dados: unknown): string {
  return renderToStaticMarkup(createElement(JsonLd, { data: dados }));
}
/** Conteúdo do <script> no HTML, depois de lido de volta como JSON. */
function lido(h: string): Record<string, unknown> {
  const abre = '<script type="application/ld+json">';
  expect(h.startsWith(abre)).toBe(true);
  expect(h.endsWith("</script>")).toBe(true);
  const corpo = h.slice(abre.length, -"</script>".length);
  expect(corpo).not.toContain("<"); // nada que feche a tag ou abra comentário
  return JSON.parse(corpo) as Record<string, unknown>;
}

const PALAVRAS_DE_ACUSACAO = /culpa|corrup|crimin|fraud|acusa|condena|suspeit|investigad|esquema|irregular|ilegal|propina|desvio/i;

describe("organizacaoLd", () => {
  it("é uma Organization com o contexto do schema.org e o repositório em sameAs", () => {
    const o = ciclo(organizacaoLd());
    expect(o["@context"]).toBe("https://schema.org");
    expect(o["@type"]).toBe("Organization");
    expect(o.name).toBe("Raio-X Parlamentar");
    expect(o.url).toBe(SITE_URL);
    expect(o["@id"]).toBe(`${SITE_URL}/#organizacao`);
    expect(o.sameAs).toContain(REPO_URL);
  });

  it("não afirma nada além do que o projeto é (sem redes sociais ou contato inventados)", () => {
    const o = ciclo(organizacaoLd());
    expect(Object.keys(o).sort()).toEqual(["@context", "@id", "@type", "description", "logo", "name", "sameAs", "url"]);
    expect(o.sameAs).toHaveLength(1);
  });
});

describe("siteLd", () => {
  it("é um WebSite em pt-BR ligado à organização e sem ação de busca", () => {
    const s = ciclo(siteLd());
    expect(s["@type"]).toBe("WebSite");
    expect(s.inLanguage).toBe("pt-BR");
    expect(s.url).toBe(SITE_URL);
    expect(s.publisher).toEqual({ "@id": `${SITE_URL}/#organizacao` });
    expect(s).not.toHaveProperty("potentialAction");
  });
});

describe("datasetLd", () => {
  it("lista em isBasedOn, como CreativeWork com nome e endereço, as fontes que a ingestão usa de fato", () => {
    const d = ciclo(datasetLd());
    expect(d["@type"]).toBe("Dataset");
    const fontes = d.isBasedOn as Array<{ "@type": string; name: string; url: string }>;
    expect(fontes).toHaveLength(5);
    for (const f of fontes) {
      expect(f["@type"]).toBe("CreativeWork");
      expect(f.name.length).toBeGreaterThan(2);
      expect(f.url).toMatch(/^https:\/\//);
    }
    const urls = fontes.map((f) => f.url).join(" ");
    expect(urls).toContain("dadosabertos.camara.leg.br");
    expect(urls).toContain("dadosabertos.tse.jus.br");
    expect(urls).toContain("portaldatransparencia.gov.br");
    expect(urls).toContain("opensanctions.org/datasets/br_pep");
    // Receita Federal hoje vem pela BrasilAPI (/fontes mostra "Receita Federal (via BrasilAPI)")
    expect(fontes.find((f) => f.url.includes("brasilapi.com.br"))?.name).toMatch(/Receita Federal.*BrasilAPI/);
  });

  it("não cita fonte que a ingestão não usa (IBGE)", () => {
    expect(JSON.stringify(datasetLd())).not.toMatch(/ibge/i);
  });

  it("não declara licença dos dados e aponta para a página de licenças", () => {
    const d = ciclo(datasetLd());
    expect(d).not.toHaveProperty("license");
    expect(d.usageInfo).toBe(LICENCAS_DADOS_URL);
    expect(LICENCAS_DADOS_URL).toBe("https://github.com/luisfelipesb9/raio-x-parlamentar-aberto/blob/main/DATA_LICENSES.md");
  });

  it("usa a data de atualização só quando ela é informada e válida", () => {
    expect(ciclo(datasetLd())).not.toHaveProperty("dateModified");
    expect(ciclo(datasetLd({ atualizadoEm: "não é data" }))).not.toHaveProperty("dateModified");
    expect(ciclo(datasetLd({ atualizadoEm: "2026-11-20T10:30:00Z" })).dateModified).toBe("2026-11-20");
  });

  it("aponta o criador para a organização e a página para /fontes", () => {
    const d = ciclo(datasetLd());
    expect(d.creator).toEqual({ "@id": `${SITE_URL}/#organizacao` });
    expect(d.url).toBe(`${SITE_URL}/fontes`);
  });
});

describe("breadcrumbLd", () => {
  it("numera os itens a partir de 1 e usa URLs absolutas", () => {
    const b = ciclo(breadcrumbLd([{ nome: "Início", caminho: "/" }, { nome: "Deputados", caminho: "/deputados" }, { nome: "Ana Souza", caminho: "/deputado/9900001" }]));
    expect(b["@type"]).toBe("BreadcrumbList");
    const itens = b.itemListElement as Array<{ position: number; name: string; item: string }>;
    expect(itens.map((i) => i.position)).toEqual([1, 2, 3]);
    expect(itens[2]).toMatchObject({ name: "Ana Souza", item: `${SITE_URL}/deputado/9900001` });
  });
});

describe("pessoaLd", () => {
  const perfil = { id: "9900001", nome: "Ana Souza", partido: "PXY", uf: "MG", foto: "https://www.camara.leg.br/internet/deputado/bandep/9900001.jpg" };

  it("descreve o deputado com cargo, partido, ficha e página oficial", () => {
    const p = ciclo(pessoaLd(perfil));
    expect(p["@type"]).toBe("Person");
    expect(p.name).toBe("Ana Souza");
    expect(p.jobTitle).toBe("Deputado(a) Federal");
    expect(p.affiliation).toEqual({ "@type": "Organization", name: "PXY" });
    expect(p.url).toBe(`${SITE_URL}/deputado/9900001`);
    expect(p.image).toBe(perfil.foto);
    expect(p.sameAs).toEqual(["https://www.camara.leg.br/deputados/9900001"]);
  });

  it.each(["javascript:alert(1)", "http://www.camara.leg.br/foto.jpg", "data:image/png;base64,AAAA", "não é url"])(
    "só aceita foto https: recusa %s",
    (foto) => {
      expect(ciclo(pessoaLd({ id: "1", nome: "Fulano", foto })).image).toBeUndefined();
    },
  );

  it("omite foto, partido e sameAs quando faltam ou não são confiáveis", () => {
    const p = ciclo(pessoaLd({ id: "abc", nome: "Fulano", partido: null, uf: null, foto: "javascript:alert(1)" }));
    expect(p).not.toHaveProperty("image");
    expect(p).not.toHaveProperty("affiliation");
    expect(p).not.toHaveProperty("sameAs");
  });

  it("não insinua culpa: nada de alerta, achado ou palavra de acusação", () => {
    const texto = JSON.stringify(pessoaLd({ ...perfil, n_findings: 7, categorias: [{ categoria: "gastos" }] } as typeof perfil));
    expect(texto).not.toMatch(PALAVRAS_DE_ACUSACAO);
    expect(texto).not.toMatch(/alerta|finding|certeza/i);
  });

  it("não altera o conteúdo do texto (só normaliza espaços) e o HTML entregue não deixa fechar a tag script", () => {
    const nome = 'Ana </script><script>alert(1)</script> "Dos" Santos';
    const p = pessoaLd({ id: "1", nome: `  ${nome}  `, partido: "<b>PXY</b>", uf: "MG", foto: null });
    expect(ciclo(p).name).toBe(nome);
    const h = html(p);
    expect(h.match(/<\/script>/g)).toHaveLength(1);
    const voltou = lido(h);
    expect(voltou.name).toBe(nome);
    expect(voltou.affiliation).toEqual({ "@type": "Organization", name: "<b>PXY</b>" });
  });
});

describe("termosLd", () => {
  it("vira um DefinedTermSet com todos os termos do glossário e âncora de cada um", () => {
    const t = ciclo(termosLd(GLOSSARIO));
    expect(t["@type"]).toBe("DefinedTermSet");
    expect(t.url).toBe(`${SITE_URL}/glossario`);
    const termos = t.hasDefinedTerm as Array<{ "@type": string; name: string; description: string; url: string }>;
    expect(termos).toHaveLength(GLOSSARIO.length);
    const primeiro = GLOSSARIO[0]!;
    expect(termos[0]).toMatchObject({ "@type": "DefinedTerm", name: primeiro.termo, url: `${SITE_URL}/glossario#${primeiro.id}` });
    expect(termos[0]!.description).toContain(primeiro.definicao);
    expect(termos[0]!.description).toContain(primeiro.porQueImporta!);
  });

  it("mantém 'a < b' como está e o HTML entregue não contém '<' dentro do script", () => {
    const t = termosLd([{ id: "x", termo: "<img onerror=1>", definicao: "a < b" }]);
    const termo = (lido(html(t)).hasDefinedTerm as Array<{ name: string; description: string }>)[0]!;
    expect(termo.name).toBe("<img onerror=1>");
    expect(termo.description).toBe("a < b");
  });
});

describe("faqLd", () => {
  it("monta FAQPage com pares pergunta e resposta", () => {
    const f = ciclo(faqLd([{ pergunta: "O que é CEAP?", resposta: "A cota parlamentar." }])!);
    expect(f["@type"]).toBe("FAQPage");
    expect(f.mainEntity).toEqual([{ "@type": "Question", name: "O que é CEAP?", acceptedAnswer: { "@type": "Answer", text: "A cota parlamentar." } }]);
  });

  it("devolve null sem perguntas (a página só usa FAQ que está visível)", () => {
    expect(faqLd([])).toBeNull();
  });

  it("mantém o texto das respostas e o HTML entregue não contém '<' dentro do script", () => {
    const f = faqLd([{ pergunta: "p<", resposta: "<script>x</script>" }]);
    const q = (lido(html(f)).mainEntity as Array<{ name: string; acceptedAnswer: { text: string } }>)[0]!;
    expect(q.name).toBe("p<");
    expect(q.acceptedAnswer.text).toBe("<script>x</script>");
  });
});

describe("saídas globais", () => {
  it("organização, site e dataset não trazem palavras de acusação", () => {
    const texto = JSON.stringify([organizacaoLd(), siteLd(), datasetLd()]);
    expect(texto).not.toMatch(PALAVRAS_DE_ACUSACAO);
  });
});
