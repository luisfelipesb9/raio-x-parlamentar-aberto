import type { GraphEdge, GraphNode, GrafoResposta } from "@/types/contracts";

export interface ItemValor {
  no: GraphNode;
  valor: number;
  aresta: GraphEdge;
}

export interface BlocoValor {
  /** soma em R$ de TODAS as arestas do tipo (não só das exibidas) */
  total: number;
  /** quantidade total de parceiros */
  n: number;
  /** quantos deles têm sanção marcada no nó */
  sancionados: number;
  /** os maiores, já ordenados */
  itens: ItemValor[];
}

export interface Parecido {
  no: GraphNode;
  afinidade: number;
  cf: number;
}

export interface ResumoGrafo {
  gastos: BlocoValor;
  emendas: BlocoValor;
  doacoes: BlocoValor;
  parecidos: Parecido[];
}

function bloco(grafo: GrafoResposta, porId: Map<string, GraphNode>, relacao: string, lado: "origem" | "destino", limite: number): BlocoValor {
  const outro = lado === "origem" ? "destino" : "origem";
  const itens: ItemValor[] = [];
  let total = 0;
  for (const e of grafo.edges) {
    if (e.relacao !== relacao || e[lado] !== grafo.centro) continue;
    const no = porId.get(e[outro]);
    if (!no) continue;
    total += e.peso;
    itens.push({ no, valor: e.peso, aresta: e });
  }
  itens.sort((a, b) => b.valor - a.valor);
  return {
    total,
    n: itens.length,
    sancionados: itens.filter((i) => i.no.atributos["sancionada"] === true).length,
    itens: itens.slice(0, limite),
  };
}

/**
 * Resume o subgrafo de profundidade 1 do deputado em blocos para a ficha:
 * - gastos: `recebeu` (empresa → deputado, R$ da cota)
 * - doações: `doou` (doador → deputado, R$)
 * - emendas: `enviou_emenda` (deputado → município, R$ empenhado)
 */
export function resumoDoGrafo(grafo: GrafoResposta, limite = 5): ResumoGrafo {
  const porId = new Map(grafo.nodes.map((n) => [n.id, n]));
  const parecidos: Parecido[] = [];
  for (const e of grafo.edges) {
    if (e.relacao !== "votou_com") continue;
    const outroId = e.origem === grafo.centro ? e.destino : e.destino === grafo.centro ? e.origem : null;
    const no = outroId ? porId.get(outroId) : undefined;
    if (no) parecidos.push({ no, afinidade: e.peso, cf: e.cf });
  }
  parecidos.sort((a, b) => b.afinidade - a.afinidade);
  return {
    gastos: bloco(grafo, porId, "recebeu", "destino", limite),
    doacoes: bloco(grafo, porId, "doou", "destino", limite),
    emendas: bloco(grafo, porId, "enviou_emenda", "origem", limite),
    parecidos: parecidos.slice(0, limite),
  };
}
