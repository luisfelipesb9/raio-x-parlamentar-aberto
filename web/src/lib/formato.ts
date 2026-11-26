const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
const pct = new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 0 });

export const formataReais = (v: number): string => brl.format(v);
export const formataPercentual = (fracao: number): string => pct.format(fracao);

/**
 * O texto das conclusões vem pronto do motor, com ponto decimal ("5.8 de 40"). Aqui o decimal vira
 * vírgula (pt-BR). Só troca "dígitos.dígitos" isolados: milhar (1.234.567), CNPJ, versão (v1.2) e
 * ponto final de frase ficam como estão.
 */
export const decimaisPtBr = (texto: string): string => texto.replace(/(?<![\w.,])(\d+)\.(\d+)(?!\d|\.\d)/g, "$1,$2");

/** De onde vêm o cadastro e a foto: a foto só é citada quando há URL real (senão a ficha mostra iniciais). */
export const origemDoCadastro = (foto: string | null | undefined): string =>
  foto?.trim() ? "Cadastro e foto oficiais da Câmara dos Deputados." : "Cadastro oficial da Câmara dos Deputados.";

export function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/).filter(Boolean);
  const a = partes[0]?.[0] ?? "?";
  const b = partes.length > 1 ? (partes[partes.length - 1]?.[0] ?? "") : "";
  return (a + b).toUpperCase();
}

export const CATEGORIAS: Record<string, string> = {
  votacao: "Votações",
  gastos: "Gastos da cota",
  integridade: "Integridade",
  producao: "Produção legislativa",
  emendas: "Emendas",
  geral: "Geral",
};

export const rotuloCategoria = (c: string): string => CATEGORIAS[c] ?? c.replaceAll("_", " ");

export const TIPOS_EVIDENCIA: Record<string, string> = {
  votacao: "Votação nominal",
  despesa_ceap: "Despesa da cota (CEAP)",
  sancao: "Sanção (CEIS/CNEP)",
  emenda: "Emenda parlamentar",
  doacao: "Doação eleitoral",
  candidatura: "Candidatura (TSE)",
  empresa: "Empresa (Receita Federal)",
  socio: "Quadro de sócios",
  proposicao: "Proposição",
};

export const rotuloEvidencia = (t: string): string => TIPOS_EVIDENCIA[t] ?? t.replaceAll("_", " ");

/** Perguntas descritivas (não sugerem sim/não que a regra não decide). Os `id` são os objetivos da API. */
export const OBJETIVOS: { id: string; pergunta: string; ajuda: string }[] = [
  { id: "alinhado_governo", pergunta: "Como é o alinhamento com o governo nas votações?", ajuda: "Olha só votações nominais em que o governo deu orientação." },
  { id: "pontuacao_producao_legislativa", pergunta: "Qual é a pontuação de produção legislativa?", ajuda: "Medida descritiva: projetos de que foi autor ou relator, ponderados por importância. Não diz se produz bem ou mal." },
  { id: "concentracao_eleitoral_emendas", pergunta: "Como as emendas se distribuem em relação à base eleitoral?", ajuda: "Compara o destino das emendas com onde o deputado teve votos." },
  { id: "risco_integridade", pergunta: "Que sinais de integridade os dados públicos mostram?", ajuda: "Cruza gastos, fornecedores punidos e doações." },
  { id: "merece_atencao_fiscalizacao", pergunta: "Que atenção os sinais reunidos pedem da fiscalização?", ajuda: "Combina outros sinais; é a pergunta mais ampla." },
];
