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
