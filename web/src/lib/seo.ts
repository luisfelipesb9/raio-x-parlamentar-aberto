/** Base compartilhada de SEO: endereço do site, canonical e textos padrão (sem dependência de React). */

export const NOME_SITE = "Raio-X Parlamentar";

/** Endereço público do site, sem barra final. Em produção vem de NEXT_PUBLIC_SITE_URL. */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/+$/, "");

/** Quantos segundos uma página renderizada no servidor vale antes de ser refeita (ISR). */
export const REVALIDAR_SEGUNDOS = 3600;

export const DESCRICAO_PADRAO =
  "Tudo o que é público sobre deputados federais, explicado em linguagem simples, com nível de certeza e link para a fonte oficial.";

export const AVISO_NAO_ACUSACAO =
  "Isto não é acusação. Um alerta indica um padrão nos dados públicos, com um nível de certeza, e sempre cita a fonte oficial.";

/** Caminho absoluto (começa com "/") → URL completa do site. */
export function urlAbsoluta(caminho: string): string {
  const c = caminho.startsWith("/") ? caminho : `/${caminho}`;
  return `${SITE_URL}${c}`;
}

/** Valor para `metadata.alternates` com o endereço canônico da página. */
export function canonical(caminho: string): { canonical: string } {
  return { canonical: urlAbsoluta(caminho) };
}

/** Corta o texto em `max` caracteres sem partir palavra, tirando espaços repetidos. */
export function limitaDescricao(texto: string, max = 160): string {
  const limpo = texto.replace(/\s+/g, " ").trim();
  if (limpo.length <= max) return limpo;
  const corte = limpo.slice(0, max - 1);
  const ultimoEspaco = corte.lastIndexOf(" ");
  return `${(ultimoEspaco > max * 0.6 ? corte.slice(0, ultimoEspaco) : corte).replace(/[\s.,;:]+$/, "")}…`;
}
