import { describe, expect, it } from "vitest";
import { montaArvore } from "./trilha";
import type { PassoProva } from "@/types/contracts";

const passo = (profundidade: number, objetivo: string, regra: string | null = "R"): PassoProva => ({
  profundidade,
  objetivo,
  regra,
  cf: 0,
  nota: "n",
  diagnostico: null,
});

describe("montaArvore", () => {
  it("lista vazia gera árvore vazia", () => {
    expect(montaArvore([])).toEqual([]);
  });

  it("passos sem sub-objetivo viram raízes irmãs", () => {
    const arv = montaArvore([passo(0, "a", "R1"), passo(0, "a", "R2")]);
    expect(arv).toHaveLength(2);
    expect(arv.every((n) => n.filhos.length === 0)).toBe(true);
  });

  it("passos mais profundos viram filhos do passo anterior mais raso", () => {
    const arv = montaArvore([
      passo(0, "merece_atencao", "R09"),
      passo(1, "risco", "R03"),
      passo(1, "risco", "R04"),
      passo(2, "x", "R99"),
    ]);
    expect(arv).toHaveLength(1);
    expect(arv[0]!.filhos.map((f) => f.passo.regra)).toEqual(["R03", "R04"]);
    expect(arv[0]!.filhos[1]!.filhos[0]!.passo.regra).toBe("R99");
  });

  it("profundidade que 'pula' níveis não quebra (anexa ao último ancestral possível)", () => {
    const arv = montaArvore([passo(0, "a"), passo(3, "b")]);
    expect(arv).toHaveLength(1);
    expect(arv[0]!.filhos).toHaveLength(1);
  });

  it("não muta a entrada", () => {
    const entrada = [passo(0, "a"), passo(1, "b")];
    const copia = structuredClone(entrada);
    montaArvore(entrada);
    expect(entrada).toEqual(copia);
  });
});
