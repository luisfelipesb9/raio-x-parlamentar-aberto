import { createElement, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { gerarConteudo } from "../../scripts/gen-conteudo.mjs";
import { GLOSSARIO } from "@/lib/glossario";
import { SITE_URL } from "@/lib/seo";
import { PaginaFaq, PaginaIndiceRegras, PaginaRegra, PaginaTermo, PaginaTexto, metadadosDe } from "./paginas";
import type { Conteudo } from "./tipos";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const C: Conteudo = gerarConteudo({ dirConteudo: path.join(aqui, "__fixtures__/conteudo"), dirRegras: path.join(aqui, "__fixtures__/regras") });
const html = (el: ReactElement) => renderToStaticMarkup(el);
const regra = (id: string) => C.regras.find((r) => r.id === id)!;

/** Todos os JSON-LD da saída, lidos de volta. */
function ld(h: string): Array<Record<string, unknown>> {
  return [...h.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g)].map((m) => JSON.parse(m[1]!) as Record<string, unknown>);
}

describe("metadadosDe", () => {
  it("monta título, descrição (até 160) e canonical absoluto", () => {
    const m = metadadosDe({ titulo: "Método", descricao: "x".repeat(300), caminho: "/metodo" });
    expect(m.title).toBe("Método");
    expect((m.description as string).length).toBeLessThanOrEqual(160);
    expect(m.alternates?.canonical).toBe(`${SITE_URL}/metodo`);
  });
});

describe("PaginaTexto (método, para estudantes, dados)", () => {
  const h = html(createElement(PaginaTexto, { pagina: C.paginas.metodo!, caminho: "/metodo", nome: "Método", conteudo: C }));

  it("mostra H1, resposta em destaque, data e o corpo convertido", () => {
    expect(h).toContain(">Como o sistema chega às conclusões</h1>");
    expect(h).toContain('<p class="resposta-destaque">O sistema aplica regras abertas aos fatos públicos e mostra o nível de certeza de cada conclusão.</p>');
    expect(h).toContain("20 de novembro de 2026");
    expect(h).toContain('<h2 id="passo-a-passo">Passo a passo</h2>');
    expect(h).toContain('<a href="/glossario#ceap">glossário</a>');
    expect(h).toContain('rel="noopener noreferrer"');
  });

  it("traz TechArticle e BreadcrumbList no JSON-LD, com a mesma data e o caminho certo", () => {
    const dados = ld(h);
    const artigo = dados.find((d) => d["@type"] === "TechArticle")!;
    expect(artigo.url).toBe(`${SITE_URL}/metodo`);
    expect(artigo.dateModified).toBe("2026-11-20");
    const trilha = dados.find((d) => d["@type"] === "BreadcrumbList")!;
    expect((trilha.itemListElement as Array<{ name: string }>).map((i) => i.name)).toEqual(["Início", "Método"]);
  });

  it("liga às outras páginas que existem (sem a própria página)", () => {
    expect(h).toContain('<a href="/faq">');
    expect(h).toContain('<a href="/regras">');
    expect(h).toContain('<a href="/glossario">');
    expect(h).not.toContain('<a href="/metodo">');
    expect(h).not.toContain('href="/dados"');
  });
});

describe("PaginaFaq", () => {
  const h = html(createElement(PaginaFaq, { pagina: C.paginas.faq!, conteudo: C }));

  it("mostra cada pergunta em <details>/<summary> com a resposta no HTML", () => {
    expect(h.match(/<details/g)).toHaveLength(2);
    expect(h).toContain("<summary>Isto é uma acusação?</summary>");
    expect(h).toContain("<strong>dados públicos</strong>");
    expect(h).toContain("De onde vêm os dados?");
  });

  it("### dentro de uma resposta não vira título solto: sai como negrito dentro do details", () => {
    const pagina = { ...C.paginas.faq!, corpo: "## Pergunta?\n\n### Detalhe\n\nTexto." };
    const h2 = html(createElement(PaginaFaq, { pagina, conteudo: C }));
    expect(h2).toContain("<strong>Detalhe</strong>");
    expect(h2).not.toContain("<h3");
  });

  it("o FAQPage do JSON-LD tem exatamente as perguntas visíveis, com a resposta em texto puro", () => {
    const faq = ld(h).find((d) => d["@type"] === "FAQPage")!;
    const q = faq.mainEntity as Array<{ name: string; acceptedAnswer: { text: string } }>;
    expect(q.map((x) => x.name)).toEqual(["Isto é uma acusação?", "De onde vêm os dados?"]);
    expect(q[0]!.acceptedAnswer.text).toBe("Não. É o que os dados públicos mostram.");
    expect(q[1]!.acceptedAnswer.text).toBe("De fontes oficiais, como a Câmara.");
  });

  it("sem perguntas no arquivo, não emite FAQPage", () => {
    const vazia = { ...C.paginas.faq!, corpo: "só texto, sem perguntas" };
    expect(ld(html(createElement(PaginaFaq, { pagina: vazia, conteudo: C }))).some((d) => d["@type"] === "FAQPage")).toBe(false);
  });
});

describe("PaginaRegra", () => {
  it("R01: mostra o bloco 'Parâmetros desta regra' com os números reais do YAML", () => {
    const h = html(createElement(PaginaRegra, { regra: regra("R01"), conteudo: C }));
    expect(h).toContain("Parâmetros desta regra");
    expect(h).toContain("<code>minimo_votacoes</code>");
    expect(h).toMatch(/minimo_votacoes<\/code>: 10/);
    expect(h).toMatch(/limiar<\/code>: 0,7/);
    expect(h).toContain("0,95");
    expect(h).toContain("<code>taxa_governismo &gt;= 0.7</code>");
    expect(h).toContain("n_votacoes &lt; 30");
    expect(h).toContain("× 0,7");
    expect(h).toContain("Poucas votações nominais, no período");
    expect(h).toContain("Abstenção e obstrução ficam fora da conta.");
    expect(h).toContain("Basômetro (Estadão)");
  });

  it("usa o texto de regras/R01.md (H1, resposta, data) e TechArticle", () => {
    const h = html(createElement(PaginaRegra, { regra: regra("R01"), conteudo: C }));
    expect(h).toContain(">R01: taxa de governismo</h1>");
    expect(h).toContain("A regra R01 mede quanto o deputado votou com a orientação do governo.");
    expect(h).toContain("22 de novembro de 2026");
    expect(ld(h).some((d) => d["@type"] === "TechArticle" && d.url === `${SITE_URL}/regras/R01`)).toBe(true);
  });

  it("sem o texto, a página existe só com os dados do YAML (sem data inventada)", () => {
    const h = html(createElement(PaginaRegra, { regra: regra("R05"), conteudo: C }));
    expect(h).toContain(">R05: Produção legislativa ponderada</h1>");
    expect(h).toMatch(/peso_coautor<\/code>: 0,25/);
    expect(h).toContain("Medida simples e comparável.");
    expect(h).not.toContain("Atualizado em");
    expect(ld(h).some((d) => d["@type"] === "TechArticle" && !("dateModified" in d))).toBe(true);
  });

  it("salvaguarda (guardrail) não mostra certeza nem parâmetros; composta mostra o que requer", () => {
    const g = html(createElement(PaginaRegra, { regra: regra("R08"), conteudo: C }));
    expect(g).toContain("Salvaguarda");
    expect(g).not.toContain("Confiança do especialista");
    expect(g).not.toContain("<dt>Parâmetros</dt>");
    const comp = html(createElement(PaginaRegra, { regra: regra("R09"), conteudo: C }));
    expect(comp).toContain("<code>risco_integridade</code>");
    expect(comp).toContain("encadeamento regressivo");
  });

  it("escapa texto vindo do YAML", () => {
    const suja = { ...regra("R05"), nome: "<script>x</script>", limitacoes: ["<img src=x onerror=1>"] };
    const h = html(createElement(PaginaRegra, { regra: suja, conteudo: C }));
    expect(h).not.toContain("<script>x");
    expect(h).not.toContain("<img");
  });
});

describe("PaginaIndiceRegras", () => {
  const h = html(createElement(PaginaIndiceRegras, { conteudo: C }));
  it("tem um link para cada regra, na ordem natural", () => {
    const hrefs = [...h.matchAll(/href="(\/regras\/[^"]+)"/g)].map((m) => m[1]);
    expect(hrefs).toEqual(["/regras/R01", "/regras/R05", "/regras/R06b", "/regras/R08", "/regras/R09"]);
  });
  it("traz o breadcrumb em JSON-LD e o aviso de não acusação", () => {
    expect(ld(h).some((d) => d["@type"] === "BreadcrumbList")).toBe(true);
    expect(h).toContain("Isto não é acusação");
  });
});

describe("PaginaTermo", () => {
  const ceap = GLOSSARIO.find((t) => t.id === "ceap")!;
  const h = html(createElement(PaginaTermo, { termo: ceap, conteudo: C }));
  it("usa o termo como H1, a definição como resposta e o 'porQueImporta' no corpo", () => {
    expect(h).toContain(">CEAP (cota parlamentar)</h1>");
    expect(h).toContain(`<p class="resposta-destaque">${ceap.definicao}</p>`);
    expect(h).toContain(ceap.porQueImporta!);
  });
  it("emite DefinedTerm e BreadcrumbList e liga de volta ao glossário", () => {
    const dados = ld(h);
    expect(dados.find((d) => d["@type"] === "DefinedTerm")!.url).toBe(`${SITE_URL}/glossario/ceap`);
    expect(dados.some((d) => d["@type"] === "BreadcrumbList")).toBe(true);
    expect(h).toContain('<a href="/glossario">');
  });
});
