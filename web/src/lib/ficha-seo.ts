/**
 * Textos citáveis da ficha do deputado (título, resumo e descrição), sem React.
 * Usados na página (HTML visível) e nos metadados, para o mesmo texto aparecer nos dois lugares.
 * Linguagem de padrão nos dados com nível de certeza: nunca de culpa (ver AGENTS.md, princípios éticos).
 */
import type { Finding, PerfilDeputado } from "@/types/contracts";
import { NIVEIS } from "./nivel";
import { limitaDescricao } from "./seo";

type PerfilBasico = Pick<PerfilDeputado, "nome" | "partido" | "uf">;

/** "Nome (PARTIDO-UF)": o sufixo do site vem do template do layout. */
export function tituloFicha(p: PerfilBasico): string {
  const sigla = [p.partido, p.uf].filter(Boolean).join("-");
  return sigla ? `${p.nome} (${sigla})` : p.nome;
}

export interface ResumoFicha {
  /** Quem é. */
  frase: string;
  /** O que os dados mostram, sempre com o nível de certeza quando há alerta. */
  alertas: string;
}

/** Duas frases curtas e autossuficientes (boas para serem citadas fora de contexto). */
export function resumoFicha(p: PerfilBasico, findings: ReadonlyArray<Pick<Finding, "cf" | "nivel">>): ResumoFicha {
  const partes = ["Deputado(a) federal"];
  if (p.partido) partes[0] += ` pelo ${p.partido}`;
  if (p.uf) partes.push(`eleito(a) por ${p.uf}`);
  const frase = `${partes.join(", ")}.`;

  if (findings.length === 0) {
    return { frase, alertas: "Nenhum alerta nos dados já carregados; isso não quer dizer que esteja tudo certo." };
  }
  const maior = findings.reduce((a, b) => (b.cf > a.cf ? b : a));
  const n = findings.length;
  const contagem = n === 1 ? "1 alerta (um padrão nos dados, não uma acusação)" : `${n} alertas (padrões nos dados, não acusações)`;
  return { frase, alertas: `Os dados públicos mostram ${contagem}; o de maior certeza é: ${NIVEIS[maior.nivel].rotulo}.` };
}

/** Meta description: o resumo inteiro, cortado em 160 caracteres sem partir palavra. */
export function descricaoFicha(p: PerfilBasico, findings: ReadonlyArray<Pick<Finding, "cf" | "nivel">>): string {
  const r = resumoFicha(p, findings);
  return limitaDescricao(`${r.frase} ${r.alertas}`);
}
