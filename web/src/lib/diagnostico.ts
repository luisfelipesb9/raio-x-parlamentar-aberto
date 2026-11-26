import type { Diagnostico } from "@/types/contracts";

/** Texto para o passo que não se aplica (ou que o motor não sabe explicar melhor). */
export const FRASE_SEM_REGRA = "Os dados atuais não ativam esta regra.";

const pct0 = new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 0 });
const pct1 = new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });

const numero = (v: number | string | undefined): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

/** Porcentagem inteira; com uma casa quando o arredondamento igualaria a taxa ao limiar (69,9% não vira "70%"). */
function porcentagem(fracao: number, limiar?: number): string {
  const inteira = pct0.format(fracao);
  if (limiar !== undefined && fracao < limiar && inteira === pct0.format(limiar)) return pct1.format(Math.floor(fracao * 1000) / 1000);
  return inteira;
}

const votos = (n: number) => `${n} ${n === 1 ? "voto válido" : "votos válidos"}`;

/**
 * Frase, em linguagem simples e sem juízo de valor, de por que um passo da prova ficou sem conclusão.
 * Usa os números do `diagnostico` da API; se faltar algum, cai no texto genérico em vez de inventar.
 */
export function fraseDiagnostico(d: Diagnostico | null | undefined): string {
  if (!d) return FRASE_SEM_REGRA;
  const n = numero(d.detalhes["n_votos_validos"]);
  const minimo = numero(d.detalhes["minimo_votos"]);
  if (d.motivo === "dados_insuficientes" && n !== null && minimo !== null) {
    const inicio = n === 0 ? "Não encontramos nenhum voto válido" : `Só encontramos ${votos(n)}`;
    return `${inicio} para este deputado e o sistema precisa de pelo menos ${minimo} para concluir.`;
  }
  const taxa = numero(d.detalhes["taxa"]);
  const limiar = numero(d.detalhes["limiar"]);
  if (d.motivo === "abaixo_do_limiar" && n !== null && taxa !== null && limiar !== null) {
    return (
      `Com ${votos(n)}, ${porcentagem(taxa, limiar)} acompanharam a orientação do governo; ` +
      `o sistema só conclui 'alinhado' a partir de ${pct0.format(limiar)}. ` +
      "Isso não indica nada contra o deputado: só mostra que o padrão procurado não apareceu."
    );
  }
  return FRASE_SEM_REGRA;
}

export type ProximoPasso = "cobertura" | "outra-pergunta";

export interface ResumoDiagnosticos {
  frases: string[];
  /** Ordem sugerida dos próximos passos ("o que fazer"). */
  proximos: ProximoPasso[];
}

/** Junta as frases dos passos que têm diagnóstico (sem repetir) e define o que sugerir ao leitor. */
export function resumoDiagnosticos(passos: readonly { diagnostico?: Diagnostico | null }[]): ResumoDiagnosticos {
  const comDiag = passos.filter((p) => p.diagnostico);
  const frases = [...new Set(comDiag.map((p) => fraseDiagnostico(p.diagnostico)))];
  const faltaDado = comDiag.some((p) => p.diagnostico!.motivo === "dados_insuficientes");
  return { frases, proximos: faltaDado ? ["cobertura", "outra-pergunta"] : ["outra-pergunta", "cobertura"] };
}
