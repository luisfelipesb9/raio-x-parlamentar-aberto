/**
 * Leitura da API feita NO SERVIDOR (páginas renderizadas para SEO).
 * Usa a mesma API somente-leitura do navegador; só difere em poder pedir cache/revalidação do Next.
 * Endereço: API_URL (só servidor) ou, se ausente, NEXT_PUBLIC_API_URL.
 */
import { ApiError, classifica, type Params } from "./api";
import { REVALIDAR_SEGUNDOS } from "./seo";

function baseServidor(): string {
  return (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
}

export type OpcoesServidor = {
  /** Segundos até refazer a página (ISR). `false` = nunca; padrão: REVALIDAR_SEGUNDOS. */
  revalidate?: number | false;
};

function montaUrl(path: string, params?: Params): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v === undefined || v === null || v === "") continue;
    qs.set(k, String(v));
  }
  const s = qs.toString();
  return `${baseServidor()}${path}${s ? `?${s}` : ""}`;
}

/** GET na API a partir do servidor. Lança `ApiError` (tipada) em qualquer falha. */
export async function servidorGet<T>(path: string, params?: Params, opcoes: OpcoesServidor = {}): Promise<T> {
  const revalidate = opcoes.revalidate ?? REVALIDAR_SEGUNDOS;
  let resp: Response;
  try {
    resp = await fetch(montaUrl(path, params), { headers: { Accept: "application/json" }, next: { revalidate } });
  } catch {
    throw new ApiError("rede", 0, null);
  }
  if (!resp.ok) {
    let detalhe: string | null = null;
    try {
      const p = (await resp.json()) as { detail?: unknown };
      detalhe = typeof p.detail === "string" ? p.detail : null;
    } catch {
      /* corpo que não é JSON (proxy): segue sem detalhe */
    }
    throw new ApiError(classifica(resp.status), resp.status, detalhe);
  }
  try {
    return (await resp.json()) as T;
  } catch {
    throw new ApiError("interno", resp.status, null);
  }
}

/** Igual a `servidorGet`, mas devolve `null` só quando a API responde 404 (a página chama `notFound()`). */
export async function servidorGetOuNull<T>(path: string, params?: Params, opcoes?: OpcoesServidor): Promise<T | null> {
  try {
    return await servidorGet<T>(path, params, opcoes);
  } catch (e) {
    if (e instanceof ApiError && e.tipo === "nao_encontrado") return null;
    throw e;
  }
}

/** Lista todos os deputados (páginas de 100) para sitemap e lista pública. */
export async function servidorTodosDeputados<T extends { id: string }>(opcoes?: OpcoesServidor): Promise<T[]> {
  const todos: T[] = [];
  for (let page = 1; page <= 50; page++) {
    const pag = await servidorGet<{ items: T[]; total: number }>("/deputados", { page, page_size: 100 }, opcoes);
    todos.push(...pag.items);
    if (todos.length >= pag.total || pag.items.length === 0) break;
  }
  return todos;
}
