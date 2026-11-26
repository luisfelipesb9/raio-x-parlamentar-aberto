import { formataPercentual, formataReais } from "./formato";

const SEM_DATA = "—";
const dataBr = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "America/Sao_Paulo" });

/** Data para leigo (dd/mm/aaaa). Data pura não muda de dia por fuso; instante com hora vira o dia em Brasília. */
export function formataData(iso: string | null | undefined): string {
  if (!iso) return SEM_DATA;
  const pura = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (pura) return `${pura[3]}/${pura[2]}/${pura[1]}`;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? SEM_DATA : dataBr.format(d);
}

/** "em 23/11/2026" (um só dia) ou "de 20/11/2026 a 23/11/2026". */
export function periodoColeta(min: string | null | undefined, max: string | null | undefined): string {
  const a = formataData(min);
  const b = formataData(max ?? min);
  if (a === SEM_DATA && b === SEM_DATA) return "sem data registrada";
  return a === b ? `em ${a}` : `de ${a} a ${b}`;
}

const FONTES: Record<string, string> = {
  camara_api_v2: "Câmara dos Deputados (cadastro, votações e projetos)",
  camara_ceap: "Câmara dos Deputados: cota parlamentar (CEAP)",
  cgu_ceis: "CGU: empresas sancionadas (CEIS/CNEP)",
  cgu_emendas: "CGU: emendas parlamentares",
  tse_consulta_cand: "TSE: candidaturas",
  tse_prestacao_contas: "TSE: doações de campanha",
  tse_votacao_munzona: "TSE: votos por município",
  opensanctions_br_pep: "OpenSanctions: pessoas politicamente expostas (PEP)",
  brasilapi_cnpj: "Receita Federal (via BrasilAPI): empresas e sócios",
};

export const rotuloFonte = (fonte: string): string => FONTES[fonte] ?? fonte.replaceAll("_", " ");

const TIPOS_DE_FATO: Record<string, string> = {
  deputado: "deputados",
  votacao: "votações",
  voto: "votos",
  autoria: "autorias",
  proposicao: "projetos",
  despesa_ceap: "despesas da cota",
  sancao: "sanções",
  emenda: "emendas",
  doacao: "doações",
  candidatura: "candidaturas",
  votos_municipio: "votos por município",
  pep: "pessoas politicamente expostas",
  empresa: "empresas",
  socio: "sócios",
};

/** Tipos de fato de uma fonte, em palavras comuns ("votações, votos, projetos"). */
export function listaTipos(tipos: readonly string[]): string {
  if (tipos.length === 0) return SEM_DATA;
  return tipos.map((t) => TIPOS_DE_FATO[t] ?? t.replaceAll("_", " ")).join(", ");
}

const REGRAS: Record<string, string> = {
  R01: "Alinhamento com o governo nas votações",
  R03: "Pagamento a fornecedor com sanção",
  R04: "Gasto da cota fora do padrão",
  R05: "Produção legislativa",
  R06: "Doador que é sócio de fornecedor (identidade confirmada)",
  R06b: "Doador que pode ser sócio de fornecedor (indício)",
  R07: "Emendas concentradas onde teve mais votos",
  R09: "Atenção da fiscalização (combina outros sinais)",
};

export const nomeRegra = (regra: string): string => REGRAS[regra] ?? `Regra ${regra}`;

type Tipo ="inteiro" | "decimal" | "percentual" | "fracao" | "reais" | "texto";

const METRICAS: Record<string, { rotulo: string; tipo: Tipo }> = {
  taxa_governismo: { rotulo: "Votos junto com o governo", tipo: "fracao" },
  n_votacoes: { rotulo: "Votações consideradas", tipo: "inteiro" },
  n_despesas: { rotulo: "Despesas da cota", tipo: "inteiro" },
  valor_total: { rotulo: "Valor total", tipo: "reais" },
  n_cnpjs: { rotulo: "Empresas diferentes", tipo: "inteiro" },
  n_categorias: { rotulo: "Categorias de gasto", tipo: "inteiro" },
  z_max: { rotulo: "Distância da média dos colegas (desvios)", tipo: "decimal" },
  categoria_top: { rotulo: "Categoria que mais destoa", tipo: "texto" },
  valor_top: { rotulo: "Gasto nessa categoria", tipo: "reais" },
  mediana_top: { rotulo: "Gasto típico dos colegas nela", tipo: "reais" },
  vezes_mediana: { rotulo: "Quantas vezes o típico", tipo: "decimal" },
  autorias: { rotulo: "Projetos como autor", tipo: "inteiro" },
  coautorias: { rotulo: "Projetos como coautor", tipo: "inteiro" },
  relatorias: { rotulo: "Projetos como relator", tipo: "inteiro" },
  iniciativa: { rotulo: "Projetos de iniciativa própria", tipo: "inteiro" },
  pontos: { rotulo: "Pontos de produção legislativa", tipo: "decimal" },
  pontos_max: { rotulo: "Pontuação máxima possível", tipo: "decimal" },
  contexto_media_partido: { rotulo: "Média do partido", tipo: "decimal" },
  pct_destino: { rotulo: "Votos nas cidades que receberam emendas (% dos votos válidos)", tipo: "percentual" },
  pct_resto: { rotulo: "Votos nas demais cidades do estado (% dos votos válidos)", tipo: "percentual" },
  razao: { rotulo: "Votação nas cidades das emendas, em vezes a das demais", tipo: "decimal" },
  n_municipios_destino: { rotulo: "Cidades que receberam emendas", tipo: "inteiro" },
  n_municipios_resto: { rotulo: "Demais cidades comparadas", tipo: "inteiro" },
  n_emendas: { rotulo: "Emendas", tipo: "inteiro" },
  valor_emendas: { rotulo: "Valor das emendas", tipo: "reais" },
  n_emendas_pix_pre_2027: { rotulo: "Emendas Pix", tipo: "inteiro" },
  ano_eleicao: { rotulo: "Ano da eleição usada", tipo: "texto" },
};

/** Chaves que repetem outra já mostrada (taxa_pct é a taxa_governismo em %). */
const REDUNDANTES = new Set(["taxa_pct"]);

export const rotuloMetrica = (chave: string): string => METRICAS[chave]?.rotulo ?? chave.replaceAll("_", " ");

const decimal = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

function formataValor(chave: string, valor: number | string): string {
  if (typeof valor === "string") return valor;
  switch (METRICAS[chave]?.tipo) {
    case "fracao":
      return formataPercentual(valor);
    case "percentual":
      return `${decimal.format(valor)}%`;
    case "reais":
      return formataReais(valor);
    case "inteiro":
      return inteiro.format(valor);
    case "texto":
      return String(valor);
    default:
      return decimal.format(valor);
  }
}

export interface LinhaMetrica {
  chave: string;
  rotulo: string;
  valor: string;
}

export function linhasMetricas(valores: Readonly<Record<string, number | string>>): LinhaMetrica[] {
  return Object.entries(valores)
    .filter(([chave]) => !REDUNDANTES.has(chave))
    .map(([chave, valor]) => ({ chave, rotulo: rotuloMetrica(chave), valor: formataValor(chave, valor) }));
}

const teto = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 3 });

/** Nível de certeza com até 3 casas (0,665 não pode virar 0,67); 0,95 continua com duas. */
export const formataTeto = (cf: number): string => teto.format(cf);

/** Espelha knowledge/rules/R01_*.yaml: CF base 0,95 e fator 0,7 quando há menos de 30 votações com orientação. */
const R01_CF_BASE = 0.95;
const R01_FATOR_POUCAS_VOTACOES = 0.7;
const R01_VOTACOES_PARA_SEM_PENALIDADE = 30;

/** Maior nível de certeza que a R01 pode atingir com `nVotacoes` votações nominais com orientação do governo. */
export function nivelMaximoR01(nVotacoes: number): number {
  return nVotacoes < R01_VOTACOES_PARA_SEM_PENALIDADE ? R01_CF_BASE * R01_FATOR_POUCAS_VOTACOES : R01_CF_BASE;
}
