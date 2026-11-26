import { describe, expect, it } from "vitest";
import { nomeDaUf, NOMES_UF } from "./ufs";

describe("nomeDaUf", () => {
  it("devolve o nome por extenso das 27 UFs", () => {
    expect(Object.keys(NOMES_UF)).toHaveLength(27);
    expect(nomeDaUf("MG")).toBe("Minas Gerais");
    expect(nomeDaUf("DF")).toBe("Distrito Federal");
  });

  it("aceita minúsculas e espaços", () => {
    expect(nomeDaUf(" sp ")).toBe("São Paulo");
  });

  it("devolve null para sigla desconhecida", () => {
    expect(nomeDaUf("XX")).toBeNull();
    expect(nomeDaUf("UF não informada")).toBeNull();
  });
});
