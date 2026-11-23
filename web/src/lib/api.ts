import type { Problem } from "@/types/contracts";

const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export type TipoErro = "rede" | "nao_encontrado" | "invalido" | "indisponivel" | "interno";

const MENSAGENS: Record<TipoErro, string> = {
  rede: "Não conseguimos falar com o servidor de dados. Verifique se a API está no ar e tente de novo.",
  nao_encontrado: "Não encontramos o que você procurou.",
  invalido: "Algum dado informado não é válido.",
  indisponivel: "O banco de dados ainda não está disponível. Tente de novo em instantes.",
  interno: "Algo deu errado do nosso lado. Tente de novo.",
};

function classifica(status: number): TipoErro {
  if (status === 404) return "nao_encontrado";
  if (status === 400 || status === 422) return "invalido";
  if (status === 503) return "indisponivel";
  return "interno";
}

export class ApiError extends Error {
  readonly status: number;
  readonly tipo: TipoErro;
  readonly detalhe: string | null;

  constructor(tipo: TipoErro, status: number, detalhe: string | null) {
    super(detalhe ?? MENSAGENS[tipo]);
    this.name = "ApiError";
    this.tipo = tipo;
    this.status = status;
    this.detalhe = detalhe;
  }

  /** Texto seguro para mostrar a leigos (nunca stack ou mensagem técnica do fetch). */
  get mensagemParaLeigo(): string {
    if (this.tipo === "nao_encontrado" || this.tipo === "invalido") return this.detalhe ?? MENSAGENS[this.tipo];
    return MENSAGENS[this.tipo];
  }
}

export type Params = Record<string, string | number | undefined | null>;

export function apiUrl(path: string, params?: Params): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v === undefined || v === null || v === "") continue;
    qs.set(k, String(v));
  }
  const s = qs.toString();
  return `${BASE}${path}${s ? `?${s}` : ""}`;
}

export async function apiGet<T>(path: string, params?: Params, signal?: AbortSignal): Promise<T> {
  return apiGetUrl<T>(apiUrl(path, params), signal);
}

export async function apiGetUrl<T>(url: string, signal?: AbortSignal): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(url, { signal, headers: { Accept: "application/json" } });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError("rede", 0, null);
  }
  if (!resp.ok) {
    let detalhe: string | null = null;
    try {
      const p = (await resp.json()) as Partial<Problem>;
      detalhe = typeof p.detail === "string" ? p.detail : null;
    } catch {
      /* corpo não-JSON (ex.: proxy): segue sem detalhe */
    }
    throw new ApiError(classifica(resp.status), resp.status, detalhe);
  }
  try {
    return (await resp.json()) as T;
  } catch {
    throw new ApiError("interno", resp.status, null);
  }
}
