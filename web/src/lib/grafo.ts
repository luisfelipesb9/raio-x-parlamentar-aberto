import type { GrafoResposta } from "@/types/contracts";
import { formataPercentual, formataReais } from "./formato";
import { formataCf } from "./nivel";

export const RELACOES = [
  "filiado_a",
  "votou_com",
  "doou",
  "recebeu",
  "enviou_emenda",
  "socio_de",
  "relator_de",
  "autor_de",
] as const;

const ROTULOS_RELACAO: Record<(typeof RELACOES)[number], string> = {
  filiado_a: "é filiado ao partido",
  votou_com: "vota parecido com",
  doou: "doou dinheiro a",
  recebeu: "recebeu dinheiro de",
  enviou_emenda: "enviou emenda a",
  socio_de: "é sócio de",
  relator_de: "foi relator de",
  autor_de: "é autor de",
};

/** Texto curto para filtros e legendas. */
export const ROTULOS_FILTRO: Record<(typeof RELACOES)[number], string> = {
  filiado_a: "Partido",
  votou_com: "Votos parecidos",
  doou: "Doações",
  recebeu: "Pagamentos recebidos",
  enviou_emenda: "Emendas",
  socio_de: "Sociedades",
  relator_de: "Relatorias",
  autor_de: "Autorias",
};

export function rotuloRelacao(relacao: string): string {
  return (ROTULOS_RELACAO as Record<string, string>)[relacao] ?? relacao.replaceAll("_", " ");
}

/** A ligação sai do nó selecionado? Então a frase começa por ele. Voto parecido é simétrico. */
export function saiDoNo(noId: string, aresta: { origem: string; relacao: string }): boolean {
  return aresta.origem === noId && aresta.relacao !== "votou_com";
}

/** Separa o que chega ao nó (inclui voto parecido) do que sai dele, mantendo a ordem da API. */
export function separaLigacoes<T extends { aresta: { origem: string; relacao: string } }>(
  noId: string,
  ligacoes: readonly T[],
): { chegam: T[]; saem: T[] } {
  return {
    chegam: ligacoes.filter((l) => !saiDoNo(noId, l.aresta)),
    saem: ligacoes.filter((l) => saiDoNo(noId, l.aresta)),
  };
}

export function valorDaAresta(relacao: string, peso: number): string | null {
  if (["recebeu", "doou", "enviou_emenda"].includes(relacao)) {
    // soma negativa = devoluções maiores que os pagamentos no período
    return peso < 0 ? `${formataReais(peso)} (saldo de estornos)` : formataReais(peso);
  }
  if (relacao === "votou_com") return `${formataPercentual(peso)} dos votos iguais`;
  return null;
}

/** Só quando há dúvida (CF < 1): sociedade sem identidade confirmada, poucas votações em comum. */
export function certezaDaAresta(cf: number): string | null {
  return cf < 1 ? `certeza (CF) ${formataCf(cf)}` : null;
}

export interface InfoTipoNo {
  rotulo: string;
  plural: string;
  /** Forma Cytoscape: tipo de nó distinguível sem depender de cor. */
  forma: "ellipse" | "round-rectangle" | "rectangle" | "diamond" | "triangle" | "hexagon";
  /** Nome do token CSS de cor (resolvido em runtime para respeitar tema claro/escuro). */
  cor: string;
}

export const TIPOS_NO: Record<string, InfoTipoNo> = {
  deputado: { rotulo: "Deputado(a)", plural: "Deputados", forma: "ellipse", cor: "--no-deputado" },
  partido: { rotulo: "Partido", plural: "Partidos", forma: "hexagon", cor: "--no-partido" },
  empresa: { rotulo: "Empresa", plural: "Empresas", forma: "rectangle", cor: "--no-empresa" },
  municipio: { rotulo: "Município", plural: "Municípios", forma: "diamond", cor: "--no-municipio" },
  proposicao: { rotulo: "Proposição", plural: "Proposições", forma: "triangle", cor: "--no-proposicao" },
  pessoa: { rotulo: "Pessoa", plural: "Pessoas", forma: "round-rectangle", cor: "--no-pessoa" },
};

export interface ElementoNo {
  data: { id: string; rotulo: string; tipo: string; dist: number; sancionada: boolean };
}
export interface ElementoAresta {
  data: { id: string; source: string; target: string; relacao: string; peso: number };
}
export type Elemento = ElementoNo | ElementoAresta;

/** BFS não direcionado a partir do centro. Nós inalcançáveis ficam fora do mapa. */
export function distanciasDoCentro(g: Pick<GrafoResposta, "centro" | "edges">): Map<string, number> {
  const adj = new Map<string, string[]>();
  for (const e of g.edges) {
    (adj.get(e.origem) ?? adj.set(e.origem, []).get(e.origem)!).push(e.destino);
    (adj.get(e.destino) ?? adj.set(e.destino, []).get(e.destino)!).push(e.origem);
  }
  const dist = new Map<string, number>([[g.centro, 0]]);
  const fila = [g.centro];
  for (let i = 0; i < fila.length; i++) {
    const atual = fila[i]!;
    for (const viz of adj.get(atual) ?? []) {
      if (!dist.has(viz)) {
        dist.set(viz, dist.get(atual)! + 1);
        fila.push(viz);
      }
    }
  }
  return dist;
}

export function paraElementos(g: GrafoResposta): Elemento[] {
  const dist = distanciasDoCentro(g);
  const ids = new Set(g.nodes.map((n) => n.id));
  const maxDist = Math.max(0, ...dist.values());
  const nos: ElementoNo[] = g.nodes.map((n) => ({
    data: {
      id: n.id,
      rotulo: n.rotulo,
      tipo: n.tipo,
      dist: dist.get(n.id) ?? maxDist + 1,
      sancionada: n.atributos["sancionada"] === true,
    },
  }));
  const arestas: ElementoAresta[] = g.edges
    .filter((e) => ids.has(e.origem) && ids.has(e.destino))
    .map((e, i) => ({
      data: { id: `e${i}`, source: e.origem, target: e.destino, relacao: e.relacao, peso: e.peso },
    }));
  return [...nos, ...arestas];
}
