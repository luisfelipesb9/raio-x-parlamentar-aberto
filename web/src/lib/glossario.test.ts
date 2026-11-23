import { describe, expect, it } from "vitest";
import { GLOSSARIO, buscaTermo } from "./glossario";

describe("glossário", () => {
  it("cobre os termos exigidos pelo produto", () => {
    for (const id of ["ceap", "votacao-nominal", "votacao-simbolica", "emenda-pix", "cf", "ceis-cnep", "pep", "qsa"]) {
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
