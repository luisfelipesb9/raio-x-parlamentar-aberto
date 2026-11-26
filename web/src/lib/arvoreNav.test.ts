import { describe, expect, it } from "vitest";
import type { PassoProva } from "@/types/contracts";
import { achata, navega, visiveis } from "./arvoreNav";
import { montaArvore } from "./trilha";

const passo = (profundidade: number, regra: string): PassoProva => ({ profundidade, objetivo: "o", regra, cf: 0, nota: "n", diagnostico: null });

// 0 R09
//   0.0 R03
//   0.1 R04
//     0.1.0 R99
// 1 R05
const itens = achata(montaArvore([passo(0, "R09"), passo(1, "R03"), passo(1, "R04"), passo(2, "R99"), passo(0, "R05")]));
const livre = new Set<string>();

describe("achata", () => {
  it("dá a cada nó um id de caminho, em pré-ordem, com pai e filhos", () => {
    expect(itens.map((i) => i.id)).toEqual(["0", "0.0", "0.1", "0.1.0", "1"]);
    expect(itens.find((i) => i.id === "0.1")).toMatchObject({ pai: "0", filhos: ["0.1.0"] });
    expect(itens.find((i) => i.id === "0")?.pai).toBeNull();
  });
});

describe("visiveis", () => {
  it("tudo aberto: todos os nós; recolher esconde os descendentes", () => {
    expect(visiveis(itens, livre)).toEqual(["0", "0.0", "0.1", "0.1.0", "1"]);
    expect(visiveis(itens, new Set(["0"]))).toEqual(["0", "1"]);
    expect(visiveis(itens, new Set(["0.1"]))).toEqual(["0", "0.0", "0.1", "1"]);
  });
});

describe("navega", () => {
  it("seta para baixo e para cima andam entre os nós visíveis e param nas pontas", () => {
    expect(navega("ArrowDown", "0", itens, livre)?.foco).toBe("0.0");
    expect(navega("ArrowDown", "1", itens, livre)?.foco).toBe("1");
    expect(navega("ArrowUp", "0.0", itens, livre)?.foco).toBe("0");
    expect(navega("ArrowUp", "0", itens, livre)?.foco).toBe("0");
    expect(navega("ArrowDown", "0", itens, new Set(["0"]))?.foco).toBe("1");
  });

  it("Home e End vão ao primeiro e ao último nó visível", () => {
    expect(navega("Home", "0.1", itens, livre)?.foco).toBe("0");
    expect(navega("End", "0", itens, livre)?.foco).toBe("1");
    expect(navega("End", "0", itens, new Set(["1"]))?.foco).toBe("1");
  });

  it("seta para a direita: abre o nó fechado; no aberto vai ao primeiro filho; folha não faz nada", () => {
    const fechado = navega("ArrowRight", "0", itens, new Set(["0"]));
    expect(fechado?.foco).toBe("0");
    expect(fechado?.recolhidos.has("0")).toBe(false);
    expect(navega("ArrowRight", "0", itens, livre)?.foco).toBe("0.0");
    expect(navega("ArrowRight", "0.0", itens, livre)?.foco).toBe("0.0");
  });

  it("seta para a esquerda: fecha o nó aberto; no fechado ou folha sobe para o pai", () => {
    const fecha = navega("ArrowLeft", "0", itens, livre);
    expect(fecha?.foco).toBe("0");
    expect(fecha?.recolhidos.has("0")).toBe(true);
    expect(navega("ArrowLeft", "0.0", itens, livre)?.foco).toBe("0");
    expect(navega("ArrowLeft", "0", itens, new Set(["0"]))?.foco).toBe("0");
  });

  it("Enter e espaço alternam abrir/fechar nos nós com filhos", () => {
    expect(navega("Enter", "0", itens, livre)?.recolhidos.has("0")).toBe(true);
    expect(navega(" ", "0", itens, new Set(["0"]))?.recolhidos.has("0")).toBe(false);
    expect(navega("Enter", "0.0", itens, livre)?.recolhidos.size).toBe(0);
  });

  it("não muta o conjunto recebido e ignora outras teclas", () => {
    const entrada = new Set<string>();
    navega("ArrowLeft", "0", itens, entrada);
    expect(entrada.size).toBe(0);
    expect(navega("a", "0", itens, livre)).toBeNull();
  });
});
