/**
 * Textos citáveis da ficha do deputado (título, resumo e descrição), sem React.
 * Usados na página (HTML visível) e nos metadados, para o mesmo texto aparecer nos dois lugares.
 * Linguagem de padrão nos dados com nível de certeza: nunca de culpa (ver AGENTS.md, princípios éticos).
 */
import type { Finding, PerfilDeputado } from "@/types/contracts";
import { decimaisPtBr } from "./formato";
import { NIVEIS } from "./nivel";
import { limitaDescricao } from "./seo";

type PerfilBasico = Pick<PerfilDeputado, "nome" | "partido" | "uf">;
type AlertaResumivel = Pick<Finding, "cf" | "nivel" | "conclusao">;

/** "Nome (PARTIDO-UF)": o sufixo do site vem do template do layout. */
export function tituloFicha(p: PerfilBasico): string {
  const sigla = [p.partido, p.uf].filter(Boolean).join("-");
  return sigla ? `${p.nome} (${sigla})` : p.nome;
}

/**
 * Resumo citável da ficha, autossuficiente (partido/UF já estão no título e no cabeçalho).
 * Cita a conclusão do alerta de maior nível entre os conclusivos (alta, média, indício). Alerta
 * inconclusivo nunca é citado como achado: o texto diz que o sistema não chegou a conclusão.
 */
export function resumoFicha(findings: ReadonlyArray<AlertaResumivel>): string {
  if (findings.length === 0) return "Sem alertas nos dados disponíveis. Isso não quer dizer que esteja tudo certo.";

  const n = findings.length;
  const abertura =
    n === 1 ? "Os dados públicos mostram 1 alerta (um padrão nos dados, não uma acusação)." : `Os dados públicos mostram ${n} alertas (padrões nos dados, não acusações).`;

  const conclusivos = findings.filter((f) => f.nivel !== "inconclusivo");
  if (conclusivos.length === 0) {
    return `${abertura} O sistema não chegou a conclusão sobre ${n === 1 ? "aquele ponto" : "esses pontos"}.`;
  }
  const maior = conclusivos.reduce((a, b) => (b.cf > a.cf ? b : a));
  return `${abertura} O de nível mais alto (${NIVEIS[maior.nivel].rotulo.toLowerCase()}) diz: ${decimaisPtBr(maior.conclusao)}`;
}

/** Meta description: o resumo cortado em 160 caracteres sem partir palavra (a abertura, com "não acusações", vem primeiro). */
export function descricaoFicha(findings: ReadonlyArray<AlertaResumivel>): string {
  return limitaDescricao(resumoFicha(findings));
}
