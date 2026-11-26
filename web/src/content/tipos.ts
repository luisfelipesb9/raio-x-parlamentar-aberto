/** Estrutura de `gerado/conteudo.json`, produzido por `scripts/gen-conteudo.mjs` (não editar o JSON à mão). */

export interface PaginaConteudo {
  /** Nome do arquivo sem extensão (`metodo`, `faq`, `R01`...). */
  arquivo: string;
  slug: string;
  titulo: string;
  descricao: string;
  /** Primeira frase citável da página. */
  resposta: string;
  /** Data no formato AAAA-MM-DD. */
  atualizado: string;
  /** Só nas páginas de regra: o id (ex.: `R01`). */
  regra?: string;
  /** Corpo em Markdown (subconjunto de `lib/markdown.tsx`). */
  corpo: string;
}

export interface Penalidade {
  se: string;
  fator: number;
  motivo: string;
}

export type ValorParametro = string | number | boolean;

/** Parâmetros reais de uma regra, lidos de `knowledge/rules/*.yaml`. */
export interface RegraConteudo {
  id: string;
  nome: string;
  tipo: string;
  categoria: string;
  conclui?: string;
  predicado?: string;
  parametros: Record<string, ValorParametro>;
  se?: string;
  cf?: number;
  penalidades: Penalidade[];
  porQue?: string;
  limitacoes: string[];
  fonteMetodologica?: string;
  prioridade?: number;
  requer: string[];
  /** Regra composta: sem predicado, só no encadeamento regressivo. */
  composta: boolean;
  /** Texto de `docs/conteudo/regras/<id>.md`, se existir. */
  texto: PaginaConteudo | null;
}

export type ArquivoPagina = "metodo" | "para-estudantes" | "dados-e-api" | "faq";

export interface Conteudo {
  /** Só as páginas cujo arquivo existe. */
  paginas: Partial<Record<ArquivoPagina, PaginaConteudo>>;
  /** Uma por arquivo de `knowledge/rules/R*.yaml`, em ordem de id. */
  regras: RegraConteudo[];
}
