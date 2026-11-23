import { describe, expect, it } from "vitest";
import { RELACOES, TIPOS_NO, distanciasDoCentro, paraElementos, rotuloRelacao, type ElementoNo } from "./grafo";
import type { GrafoResposta } from "@/types/contracts";

const grafo: GrafoResposta = {
  centro: "deputado:1",
  profundidade: 2,
  truncado: false,
  nodes: [
    { id: "deputado:1", tipo: "deputado", rotulo: "Ana", atributos: { partido: "PT" } },
    { id: "partido:PT", tipo: "partido", rotulo: "PT", atributos: {} },
    { id: "deputado:2", tipo: "deputado", rotulo: "Beto", atributos: {} },
    { id: "deputado:3", tipo: "deputado", rotulo: "Isolado", atributos: {} },
  ],
  edges: [
    { origem: "deputado:1", destino: "partido:PT", relacao: "filiado_a", peso: 1, cf: 1, evidencia_ids: [] },
    { origem: "deputado:2", destino: "partido:PT", relacao: "filiado_a", peso: 1, cf: 1, evidencia_ids: [] },
  ],
};

describe("distanciasDoCentro", () => {
  it("BFS não direcionado a partir do centro; inalcançável fica fora", () => {
    const d = distanciasDoCentro(grafo);
    expect(d.get("deputado:1")).toBe(0);
    expect(d.get("partido:PT")).toBe(1);
    expect(d.get("deputado:2")).toBe(2);
    expect(d.has("deputado:3")).toBe(false);
  });
});

describe("paraElementos", () => {
  it("gera elementos Cytoscape com distância e descarta arestas órfãs", () => {
    const el = paraElementos({ ...grafo, edges: [...grafo.edges, { origem: "deputado:1", destino: "empresa:x", relacao: "doou", peso: 1, cf: 1, evidencia_ids: [] }] });
    const nos = el.filter((e): e is ElementoNo => !("source" in e.data));
    const arestas = el.filter((e) => "source" in e.data);
    expect(nos).toHaveLength(4);
    expect(arestas).toHaveLength(2);
    expect(nos.find((n) => n.data.id === "deputado:1")!.data.dist).toBe(0);
    expect(nos.find((n) => n.data.id === "deputado:3")!.data.dist).toBe(3);
  });
});

describe("vocabulário", () => {
  it("toda relação do backend tem rótulo em português simples", () => {
    for (const r of RELACOES) {
      expect(rotuloRelacao(r).length).toBeGreaterThan(3);
      expect(rotuloRelacao(r)).not.toContain("_");
    }
    expect(RELACOES).toContain("votou_com");
  });

  it("relação desconhecida cai num rótulo legível (sem underscore)", () => {
    expect(rotuloRelacao("nova_relacao")).toBe("nova relacao");
  });

  it("todo tipo de nó tem forma distinta (não depender só de cor)", () => {
    const formas = Object.values(TIPOS_NO).map((t) => t.forma);
    expect(new Set(formas).size).toBe(formas.length);
    expect(Object.keys(TIPOS_NO).sort()).toEqual(["deputado", "empresa", "municipio", "partido", "pessoa", "proposicao"]);
  });
});
