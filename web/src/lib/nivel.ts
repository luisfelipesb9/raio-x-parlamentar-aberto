import type { Nivel } from "@/types/contracts";

export interface InfoNivel {
  /** Texto do selo: o nível NUNCA é comunicado só por cor. */
  rotulo: string;
  /** Quantas das 4 barras do indicador ficam preenchidas. */
  barras: 1 | 2 | 3 | 4;
  explicacao: string;
}

export const NIVEIS: Record<Nivel, InfoNivel> = {
  alta: {
    rotulo: "Certeza alta",
    barras: 4,
    explicacao:
      "Os dados públicos sustentam fortemente esta leitura. Ainda assim, é uma leitura dos dados, não um julgamento sobre a pessoa.",
  },
  media: {
    rotulo: "Certeza média",
    barras: 3,
    explicacao:
      "Há base razoável nos dados, mas faltam informações ou o volume é pequeno. Vale conferir nos documentos oficiais.",
  },
  indicio: {
    rotulo: "Apenas indício",
    barras: 2,
    explicacao:
      "Sinal fraco: algo chamou a atenção, mas os dados não bastam para concluir. Trate como pista para investigar, não como fato.",
  },
  inconclusivo: {
    rotulo: "Inconclusivo",
    barras: 1,
    explicacao:
      "O sistema não encontrou base suficiente para concluir. Isso não significa que esteja tudo certo nem que haja algo errado: só que estes dados não permitem afirmar nada.",
  },
};

/** Mesmos limiares de `Nivel.from_cf` em contracts/models.py. */
export function nivelDeCf(cf: number): Nivel {
  if (cf >= 0.7) return "alta";
  if (cf >= 0.4) return "media";
  if (cf >= 0.2) return "indicio";
  return "inconclusivo";
}

const fmtCf = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function formataCf(cf: number): string {
  return fmtCf.format(cf);
}
