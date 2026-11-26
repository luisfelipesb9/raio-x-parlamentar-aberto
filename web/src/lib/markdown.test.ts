import { Fragment, createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { markdownParaReact, markdownParaTexto, perguntasDoFaq } from "./markdown";

function html(md: string): string {
  return renderToStaticMarkup(createElement(Fragment, null, markdownParaReact(md)));
}

describe("markdownParaReact: estrutura", () => {
  it("converte títulos ## e ### em h2 e h3 com âncora", () => {
    expect(html("## Como funciona\n\n### Passo a passo")).toBe(
      '<h2 id="como-funciona">Como funciona</h2><h3 id="passo-a-passo">Passo a passo</h3>',
    );
  });

  it("junta linhas seguidas num único parágrafo e separa por linha em branco", () => {
    expect(html("primeira linha\nsegunda linha\n\nOutro parágrafo")).toBe("<p>primeira linha segunda linha</p><p>Outro parágrafo</p>");
  });

  it("converte listas com - e numeradas com 1.", () => {
    expect(html("- um\n- dois\n\n1. alfa\n2. beta")).toBe("<ul><li>um</li><li>dois</li></ul><ol><li>alfa</li><li>beta</li></ol>");
  });

  it("junta a continuação indentada ao item da lista", () => {
    expect(html("- um item\n  que continua\n- outro")).toBe("<ul><li>um item que continua</li><li>outro</li></ul>");
  });

  it("converte bloco de código sem interpretar o que há dentro", () => {
    expect(html("```\nGET /deputados?uf=MG\n**não é negrito**\n```")).toBe(
      "<pre><code>GET /deputados?uf=MG\n**não é negrito**</code></pre>",
    );
  });

  it("devolve vazio para texto vazio", () => {
    expect(html("")).toBe("");
    expect(html("\n\n  \n")).toBe("");
  });
});

describe("markdownParaReact: texto em linha", () => {
  it("converte **negrito**, *itálico* e `código`", () => {
    expect(html("um **forte**, um *leve* e `x`")).toBe("<p>um <strong>forte</strong>, um <em>leve</em> e <code>x</code></p>");
  });

  it("converte link interno sem rel e sem abrir nova aba", () => {
    expect(html("veja o [glossário](/glossario#ceap)")).toBe('<p>veja o <a href="/glossario#ceap">glossário</a></p>');
  });

  it("converte link https externo com rel noopener noreferrer", () => {
    expect(html("fonte: [Câmara](https://dadosabertos.camara.leg.br/)")).toBe(
      '<p>fonte: <a href="https://dadosabertos.camara.leg.br/" rel="noopener noreferrer" target="_blank">Câmara<span class="visually-hidden"> (abre em nova aba)</span></a></p>',
    );
  });

  it("aceita negrito dentro do texto do link", () => {
    expect(html("[**R01**](/regras/R01)")).toBe('<p><a href="/regras/R01"><strong>R01</strong></a></p>');
  });
});

describe("markdownParaReact: segurança", () => {
  it("não gera link para javascript:, data:, http: ou //host: fica só o texto", () => {
    for (const href of ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html;base64,AAAA", "http://exemplo.test/", "//exemplo.test/x", "vbscript:x"]) {
      const saida = html(`[clique aqui](${href})`);
      expect(saida, href).toBe("<p>clique aqui</p>");
    }
  });

  it("escapa HTML cru e <script>: nunca aparece como tag", () => {
    const saida = html('<script>alert("x")</script>\n\n<img src=x onerror=alert(1)> e <b>negrito</b>');
    expect(saida).not.toContain("<script");
    expect(saida).not.toContain("<img");
    expect(saida).not.toContain("<b>");
    expect(saida).toContain("&lt;script&gt;");
    expect(saida).toContain("&lt;img src=x onerror=alert(1)&gt;");
  });

  it("não deixa o texto do link escapar do atributo href", () => {
    const saida = html('[a](https://exemplo.test/" onmouseover="alert(1))');
    expect(saida).not.toMatch(/<a [^>]*onmouseover/);
  });

  it("não produz atributos fora de href, rel, target e id", () => {
    const saida = html("## T\n\n[a](/x) [b](https://exemplo.test/y) **c**");
    const atributos = [...saida.matchAll(/<[a-z0-9]+ ([^>]*)>/g)].flatMap((m) => [...(m[1] ?? "").matchAll(/([a-z-]+)=/g)].map((x) => x[1]));
    for (const a of atributos) expect(["href", "rel", "target", "id", "class"]).toContain(a);
  });
});

describe("markdownParaReact: casos extras", () => {
  it("recusa https com usuário e senha (https://camara.leg.br@evil.com)", () => {
    expect(html("[a](https://camara.leg.br@evil.com/x) [b](https://u:p@evil.com/)")).toBe("<p>a b</p>");
  });

  it("gera ids de âncora únicos (sufixo -2) e sem colidir com ids da moldura", () => {
    expect(html("## Dados\n\n## Dados\n\n## Veja também\n\n## Parametros regra")).toBe(
      '<h2 id="dados">Dados</h2><h2 id="dados-2">Dados</h2><h2 id="veja-tambem-2">Veja também</h2><h2 id="parametros-regra-2">Parametros regra</h2>',
    );
  });

  it("título sem letras fica sem id", () => {
    expect(html("## ???")).toBe("<h2>???</h2>");
  });

  it("com rebaixaTitulos, ## e ### viram negrito em parágrafo (sem h2/h3 soltos)", () => {
    const saida = renderToStaticMarkup(createElement(Fragment, null, markdownParaReact("## A\n\n### B\n\ntexto", { rebaixaTitulos: true })));
    expect(saida).toBe("<p><strong>A</strong></p><p><strong>B</strong></p><p>texto</p>");
  });
});

describe("markdownParaTexto", () => {
  it("tira a marcação e mantém o texto, inclusive das listas e dos links", () => {
    const md = "Veja o [glossário](/glossario#ceap) e **entenda**.\n\n- item *um*\n- item `dois`\n\n1. passo";
    expect(markdownParaTexto(md)).toBe("Veja o glossário e entenda. item um item dois passo");
  });
});

describe("perguntasDoFaq", () => {
  it("cada ## é uma pergunta e o texto até o próximo ## é a resposta", () => {
    const corpo = "## O que é isto?\n\nUm **sistema**.\n\nMais um parágrafo.\n\n## Posso confiar?\n\nConfira a [fonte](https://exemplo.test/).";
    expect(perguntasDoFaq(corpo)).toEqual([
      { pergunta: "O que é isto?", resposta: "Um **sistema**.\n\nMais um parágrafo." },
      { pergunta: "Posso confiar?", resposta: "Confira a [fonte](https://exemplo.test/)." },
    ]);
  });

  it("ignora o texto antes da primeira pergunta e perguntas sem resposta", () => {
    expect(perguntasDoFaq("introdução solta\n\n## Sem resposta?\n\n## Com resposta?\n\nSim.")).toEqual([
      { pergunta: "Com resposta?", resposta: "Sim." },
    ]);
  });
});
