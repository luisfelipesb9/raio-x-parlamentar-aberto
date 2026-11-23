import { describe, expect, it } from "vitest";
import { resumoDoGrafo } from "./resumo";
import type { GraphEdge, GraphNode, GrafoResposta } from "@/types/contracts";

const no = (id: string, tipo: string, rotulo: string, atributos: Record<string, unknown> = {}): GraphNode => ({ id, tipo, rotulo, atributos });
const aresta = (origem: string, destino: string, relacao: string, peso: number, cf = 1): GraphEdge => ({ origem, destino, relacao, peso, cf, evidencia_ids: [] });

const base: GrafoResposta = {
  centro: "deputado:1",
  profundidade: 1,
  truncado: false,
  nodes: [
    no("deputado:1", "deputado", "Ana"),
    no("deputado:2", "deputado", "Beto"),
    no("deputado:3", "deputado", "Caio"),
    no("empresa:a", "empresa", "Posto A"),
    no("empresa:b", "empresa", "Posto B", { sancionada: true }),
    no("pessoa:x", "pessoa", "Fulano"),
    no("municipio:1", "municipio", "Cidade 1"),
  ],
  edges: [
    aresta("empresa:a", "deputado:1", "recebeu", 100),
    aresta("empresa:b", "deputado:1", "recebeu", 900),
    aresta("pessoa:x", "deputado:1", "doou", 50),
    aresta("deputado:1", "municipio:1", "enviou_emenda", 2000),
    aresta("deputado:1", "deputado:2", "votou_com", 0.9, 0.8),
    aresta("deputado:3", "deputado:1", "votou_com", 0.7, 0.9),
  ],
};

describe("resumoDoGrafo", () => {
  it("soma e ordena por valor, mantendo a direção correta de cada relação", () => {
    const r = resumoDoGrafo(base);
    expect(r.gastos.total).toBe(1000);
    expect(r.gastos.itens.map((i) => i.no.rotulo)).toEqual(["Posto B", "Posto A"]);
    expect(r.doacoes.itens.map((i) => i.no.rotulo)).toEqual(["Fulano"]);
    expect(r.emendas.total).toBe(2000);
    expect(r.emendas.itens[0]!.no.rotulo).toBe("Cidade 1");
  });

  it("conta e destaca fornecedores sancionados", () => {
    const r = resumoDoGrafo(base);
    expect(r.gastos.sancionados).toBe(1);
    expect(r.gastos.itens[0]!.no.atributos["sancionada"]).toBe(true);
  });

  it("limita a lista mas mantém a contagem total", () => {
    const nodes = [no("deputado:1", "deputado", "Ana")];
    const edges: GraphEdge[] = [];
    for (let i = 0; i < 12; i++) {
      nodes.push(no(`empresa:${i}`, "empresa", `E${i}`));
      edges.push(aresta(`empresa:${i}`, "deputado:1", "recebeu", i + 1));
    }
    const r = resumoDoGrafo({ ...base, nodes, edges }, 5);
    expect(r.gastos.itens).toHaveLength(5);
    expect(r.gastos.n).toBe(12);
    expect(r.gastos.itens[0]!.valor).toBe(12);
  });

  it("'vota parecido' vê os dois sentidos, ordena por afinidade e leva o cf", () => {
    const r = resumoDoGrafo(base);
    expect(r.parecidos.map((p) => p.no.rotulo)).toEqual(["Beto", "Caio"]);
    expect(r.parecidos[0]!.afinidade).toBe(0.9);
    expect(r.parecidos[0]!.cf).toBe(0.8);
  });

  it("grafo vazio devolve tudo zerado, sem quebrar", () => {
    const r = resumoDoGrafo({ ...base, nodes: [no("deputado:1", "deputado", "Ana")], edges: [] });
    expect(r.gastos).toMatchObject({ total: 0, n: 0, itens: [] });
    expect(r.parecidos).toEqual([]);
  });
});
