import { describe, expect, it } from "vitest";
import { agrupaPorUf, SEM_UF } from "./deputados-lista";

const d = (id: string, nome: string, uf: string | null, partido: string | null = "PXX") => ({ id, nome, uf, partido });

describe("agrupaPorUf", () => {
  it("agrupa por UF, com as UFs e os nomes em ordem alfabética (sem ranking)", () => {
    const grupos = agrupaPorUf([d("3", "Zeca", "SP"), d("1", "Ana", "MG"), d("2", "Bia", "SP"), d("4", "Caio", "AC")]);
    expect(grupos.map((g) => g.uf)).toEqual(["AC", "MG", "SP"]);
    expect(grupos[2]?.deputados.map((x) => x.nome)).toEqual(["Bia", "Zeca"]);
  });

  it("ordena nomes com acento como o leitor espera (Álvaro antes de Bruno)", () => {
    const [g] = agrupaPorUf([d("1", "Bruno", "MG"), d("2", "Álvaro", "MG")]);
    expect(g?.deputados.map((x) => x.nome)).toEqual(["Álvaro", "Bruno"]);
  });

  it("manda quem não tem UF para um grupo no fim, sem perder ninguém", () => {
    const grupos = agrupaPorUf([d("1", "Ana", null), d("2", "Bia", "AC")]);
    expect(grupos.map((g) => g.uf)).toEqual(["AC", SEM_UF]);
    expect(grupos[1]?.deputados).toHaveLength(1);
  });

  it("devolve lista vazia para entrada vazia", () => {
    expect(agrupaPorUf([])).toEqual([]);
  });
});
