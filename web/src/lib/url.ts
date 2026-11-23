/** Devolve a URL só se for http(s) absoluta; qualquer outro esquema (javascript:, data:…) vira null. */
export function urlSegura(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    return u.protocol === "https:" || u.protocol === "http:" ? url : null;
  } catch {
    return null;
  }
}
