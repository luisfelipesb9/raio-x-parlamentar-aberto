/** Quais páginas de conteúdo existem e onde ficam. Funções puras sobre `Conteudo` (testáveis sem o JSON real). */
import type { Termo } from "@/lib/glossario";
import type { ArquivoPagina, Conteudo } from "./tipos";

/** Rota pública de cada arquivo de `docs/conteudo/`. */
export const ROTA_DA_PAGINA: Record<ArquivoPagina, string> = {
  metodo: "/metodo",
  "para-estudantes": "/para-estudantes",
  "dados-e-api": "/dados",
  faq: "/faq",
};

export type RotaDeConteudo = { caminho: string; nome: string; atualizado?: string };

/** Nome de cada página: única fonte (rotas, rodapé, breadcrumb e "Veja também"). */
export const NOME_DA_PAGINA: Record<ArquivoPagina, string> = {
  metodo: "Método",
  "para-estudantes": "Para estudantes",
  "dados-e-api": "Dados e API",
  faq: "Perguntas frequentes",
};

export function rotasDeConteudo(c: Conteudo, termos: readonly Termo[]): RotaDeConteudo[] {
  const rotas: RotaDeConteudo[] = [];
  for (const arquivo of Object.keys(ROTA_DA_PAGINA) as ArquivoPagina[]) {
    const p = c.paginas[arquivo];
    if (p) rotas.push({ caminho: ROTA_DA_PAGINA[arquivo], nome: NOME_DA_PAGINA[arquivo], atualizado: p.atualizado });
  }
  if (c.regras.length > 0) {
    rotas.push({ caminho: "/regras", nome: "Regras do sistema" });
    for (const r of c.regras) {
      rotas.push({ caminho: `/regras/${r.id}`, nome: `${r.id}: ${r.nome}`, ...(r.texto ? { atualizado: r.texto.atualizado } : {}) });
    }
  }
  for (const t of termos) rotas.push({ caminho: `/glossario/${t.id}`, nome: t.termo });
  return rotas;
}

/** Links da seção "Saiba mais" do rodapé: só o que existe, em ordem fixa. */
export function linksSaibaMais(c: Conteudo): { href: string; texto: string }[] {
  const links: { href: string; texto: string }[] = [];
  const pagina = (a: ArquivoPagina) => {
    if (c.paginas[a]) links.push({ href: ROTA_DA_PAGINA[a], texto: NOME_DA_PAGINA[a] });
  };
  pagina("metodo");
  if (c.regras.length > 0) links.push({ href: "/regras", texto: "Regras" });
  pagina("faq");
  links.push({ href: "/glossario", texto: "Glossário" });
  pagina("dados-e-api");
  pagina("para-estudantes");
  return links;
}
