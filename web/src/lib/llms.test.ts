import { describe, expect, it } from "vitest";
import { LICENCAS_DADOS_URL, REPO_URL } from "./jsonld";
import { gerarLlmsTxt } from "./llms";
import { SITE_URL } from "./seo";

describe("gerarLlmsTxt", () => {
  const txt = gerarLlmsTxt();
  const linhas = txt.split("\n");

  it("começa com o nome do projeto e um resumo cuja primeira frase diz o que é", () => {
    expect(linhas[0]).toBe("# Raio-X Parlamentar");
    const resumo = linhas.find((l) => l.startsWith("> "))!;
    expect(resumo).toMatch(/^> Sistema de código aberto que /);
  });

  it("tem as seções de páginas, metodologia, dados e código", () => {
    for (const h of ["## Páginas principais", "## Metodologia e limites", "## Dados e licenças", "## Código"]) {
      expect(linhas).toContain(h);
    }
  });

  it("lista as páginas principais com link absoluto do site", () => {
    for (const r of ["/", "/deputados", "/grafo", "/perguntar", "/comparar", "/glossario", "/fontes"]) {
      expect(txt).toContain(`](${SITE_URL}${r})`);
    }
  });

  it("deixa claro que não é acusação e que cada conclusão tem certeza e fonte", () => {
    expect(txt).toMatch(/não é acusação/i);
    expect(txt).toMatch(/nível de certeza/i);
    expect(txt).toMatch(/fonte oficial/i);
  });

  it("aponta para as licenças dos dados e para o repositório", () => {
    expect(txt).toContain(`](${LICENCAS_DADOS_URL})`);
    expect(txt).toContain(`](${REPO_URL})`);
  });

  it("não cita ferramentas de IA nem usa marketês", () => {
    expect(txt).not.toMatch(/Co-Authored|Generated with|ChatGPT|Claude|líder de mercado|inovador/i);
  });

  it("termina com quebra de linha", () => {
    expect(txt.endsWith("\n")).toBe(true);
  });
});
