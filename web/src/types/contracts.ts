/* eslint-disable */
// ARQUIVO GERADO por `pnpm gen:types` a partir de src/types/schemas/*.json — não edite à mão.
export const CONTRACT_VERSION = "0.1.0" as const;

export interface Afinidade {
  deputado_a: string;
  deputado_b: string;
  n_votacoes_comuns: number;
  n_iguais: number;
  afinidade: number;
  cf: number;
}

export interface Backlink {
  no: GraphNode;
  aresta: GraphEdge;
}

export interface GraphNode {
  id: string;
  tipo: string;
  rotulo: string;
  atributos: {
    [k: string]: unknown;
  };
}

export interface GraphEdge {
  origem: string;
  destino: string;
  relacao: string;
  peso: number;
  cf: number;
  evidencia_ids: string[];
}

export interface BacklinksResposta {
  node_id: string;
  total: number;
  backlinks: Backlink[];
}

export type Nivel = "alta" | "media" | "indicio" | "inconclusivo";

export interface ComparacaoCategoria {
  categoria: string;
  a: ResumoCategoria | null;
  b: ResumoCategoria | null;
}

export interface ResumoCategoria {
  categoria: string;
  n_findings: number;
  cf_max: number;
  nivel_max: Nivel;
}

export interface ComparacaoResposta {
  a: PerfilDeputado;
  b: PerfilDeputado;
  categorias: ComparacaoCategoria[];
  afinidade_votos: Afinidade | null;
  em_comum: GraphNode[];
  findings_a: Finding[];
  findings_b: Finding[];
}

export interface PerfilDeputado {
  id: string;
  nome: string;
  partido: string | null;
  uf: string | null;
  foto: string | null;
  n_findings: number;
  categorias: ResumoCategoria[];
}

export interface Finding {
  id: string;
  deputado_id: string;
  regra: string;
  categoria: string;
  conclusao: string;
  cf: number;
  nivel: Nivel;
  evidencias: Evidence[];
  guardrails_aplicados: string[];
  valores: {
    [k: string]: unknown;
  };
}

export interface Evidence {
  tipo: string;
  id_oficial: string;
  url: string | null;
  descricao: string | null;
}

export interface DeputadoResumo {
  id: string;
  nome: string;
  partido: string | null;
  uf: string | null;
  foto: string | null;
}

export interface Explanation {
  finding_id: string;
  como: ExplanationStep[];
  por_que: string;
  limitacoes: string[];
}

export interface ExplanationStep {
  regra: string;
  condicao: string;
  resultado: boolean;
  detalhe: string | null;
}

export interface Fact {
  tipo: string;
  chave: string;
  atributos: {
    [k: string]: unknown;
  };
  fonte: string;
  id_oficial: string;
  url: string | null;
  coletado_em: string;
}

export interface GrafoResposta {
  centro: string;
  profundidade: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncado: boolean;
}

export interface PaginaDeputados {
  items: DeputadoResumo[];
  total: number;
  page: number;
  page_size: number;
}

export interface PassoProva {
  profundidade: number;
  objetivo: string;
  regra: string | null;
  cf: number;
  nota: string;
}

export interface PerguntarResposta {
  objetivo: string;
  deputado_id: string;
  cf: number;
  nivel: Nivel;
  regras_usadas: string[];
  finding_ids: string[];
  trilha: PassoProva[];
}

export interface Problem {
  type: string;
  title: string;
  status: number;
  detail: string | null;
  errors:
    | {
        [k: string]: string;
      }[]
    | null;
}
