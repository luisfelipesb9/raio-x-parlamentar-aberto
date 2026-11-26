import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SITE_URL } from "@/lib/seo";
import { PaginaConteudo, dataPorExtenso } from "./PaginaConteudo";

function render(props: Partial<Parameters<typeof PaginaConteudo>[0]> = {}): string {
  return renderToStaticMarkup(
    createElement(
      PaginaConteudo,
      {
        titulo: "Como o sistema chega às conclusões",
        resposta: "O sistema aplica regras abertas aos fatos públicos.",
        atualizado: "2026-11-20",
        migalhas: [
          { nome: "Início", caminho: "/" },
          { nome: "Método", caminho: "/metodo" },
        ],
        jsonld: [{ "@type": "TechArticle" }],
        vejaTambem: [{ caminho: "/faq", nome: "Perguntas frequentes" }],
        ...props,
      },
      createElement("p", null, "corpo da página"),
    ),
  );
}

describe("dataPorExtenso", () => {
  it("escreve a data em português, sem depender do fuso", () => {
    expect(dataPorExtenso("2026-11-20")).toBe("20 de novembro de 2026");
    expect(dataPorExtenso("2026-01-01")).toBe("1 de janeiro de 2026");
  });
  it("devolve null para data inválida", () => {
    expect(dataPorExtenso("ontem")).toBeNull();
    expect(dataPorExtenso("2026-13-40")).toBeNull();
  });
});

describe("PaginaConteudo", () => {
  const h = render();

  it("tem um único H1 (o título) e a resposta como parágrafo de abertura destacado", () => {
    expect(h.match(/<h1[ >]/g)).toHaveLength(1);
    expect(h).toContain(">Como o sistema chega às conclusões</h1>");
    expect(h).toMatch(/<p class="resposta-destaque">O sistema aplica regras abertas aos fatos públicos\.<\/p>/);
    expect(h.indexOf("</h1>")).toBeLessThan(h.indexOf("resposta-destaque"));
  });

  it("mostra a data 'Atualizado em' em <time> e some quando não há data", () => {
    expect(h).toContain('Atualizado em <time dateTime="2026-11-20">20 de novembro de 2026</time>');
    expect(render({ atualizado: undefined })).not.toContain("Atualizado em");
  });

  it("traz o breadcrumb visual (com a página atual marcada) e o aviso de não acusação", () => {
    expect(h).toMatch(/<nav aria-label="Você está em"[^>]*><ol/);
    expect(h).toContain('<a href="/">Início</a>');
    expect(h).toContain('<span aria-current="page">Método</span>');
    expect(h).toContain("Isto não é acusação");
  });

  it("inclui cada JSON-LD em <script type=application/ld+json> e o corpo", () => {
    expect(h).toContain('<script type="application/ld+json">{"@type":"TechArticle"}</script>');
    expect(h).toContain("corpo da página");
  });

  it("lista os links internos de 'Veja também'", () => {
    expect(h).toContain('<a href="/faq">Perguntas frequentes</a>');
    expect(render({ vejaTambem: [] })).not.toContain("Veja também");
  });

  it("não usa o endereço do site em links internos (sem host fixo no HTML)", () => {
    expect(h).not.toContain(SITE_URL + "/faq");
  });
});
