import { describe, expect, it } from "vitest";
import { GLOSSARIO, buscaTermo } from "./glossario";

describe("glossário", () => {
  it("cobre os termos exigidos pelo produto", () => {
    for (const id of ["ceap", "votacao-nominal", "votacao-simbolica", "emenda-pix", "cf", "ceis-cnep", "pep", "qsa"]) {
      expect(buscaTermo(id), id).toBeDefined();
    }
  });

  it("o termo técnico CF aparece com o nome leigo na frente e continua citando o fator de certeza", () => {
    const cf = buscaTermo("cf");
    expect(cf?.termo).toMatch(/^Nível de certeza/);
    expect(cf?.termo).toMatch(/CF/);
    expect(`${cf?.termo} ${cf?.definicao}`.toLowerCase()).toContain("fator de certeza");
  });

  it("explica os termos da cobertura dos dados e do limite da certeza", () => {
    for (const id of ["cobertura-dados", "janela-votacao", "nivel-certeza-maximo", "votos-validos"]) {
      expect(buscaTermo(id), id).toBeDefined();
    }
  });

  it("explica em palavras simples o vocabulário do mapa de relações", () => {
    for (const id of ["mapa-relacoes", "saltos", "grupo-nos", "tamanho-espessura"]) {
      const t = buscaTermo(id);
      expect(t, id).toBeDefined();
      expect(t!.definicao).not.toMatch(/\b(grafo|aresta|BFS|cytoscape)\b/i);
    }
    expect(buscaTermo("saltos")!.definicao).toMatch(/ligações diretas/i);
    expect(buscaTermo("grupo-nos")!.definicao).toMatch(/\+N|mais N|\+ ?\d/);
    expect(buscaTermo("tamanho-espessura")!.definicao).toMatch(/R\$/);
  });

  it("todo termo tem nome, definição curta e ids únicos", () => {
    const ids = GLOSSARIO.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const t of GLOSSARIO) {
      expect(t.termo.length).toBeGreaterThan(1);
      expect(t.definicao.length).toBeGreaterThan(20);
    }
  });

  it("devolve undefined para termo inexistente", () => {
    expect(buscaTermo("nao-existe")).toBeUndefined();
  });
});
