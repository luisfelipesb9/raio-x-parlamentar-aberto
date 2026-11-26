/** Montagem pura do sitemap (a leitura da API fica em `app/sitemap.ts`). */
import type { MetadataRoute } from "next";
import { urlAbsoluta } from "./seo";

export const ROTAS_FIXAS = ["/", "/deputados", "/grafo", "/perguntar", "/comparar", "/glossario", "/fontes"] as const;

/** Rotas cujo texto não depende dos dados coletados: não recebem `lastModified`. */
const SEM_DATA_DE_DADOS = new Set<string>(["/glossario"]);

/** Mesmo formato de id aceito pela API em /deputados/{id}. */
const ID_SEGURO = /^[A-Za-z0-9_-]{1,32}$/;

/** Data da coleta mais recente entre as fontes da cobertura; `undefined` se não houver nenhuma válida (nada de data inventada). */
export function ultimaColeta(cobertura: { fontes: ReadonlyArray<{ coletado_em_max: string | null }> } | null): Date | undefined {
  let melhor: Date | undefined;
  for (const f of cobertura?.fontes ?? []) {
    if (!f.coletado_em_max) continue;
    const d = new Date(f.coletado_em_max);
    if (Number.isNaN(d.getTime())) continue;
    if (!melhor || d > melhor) melhor = d;
  }
  return melhor;
}

export function montaSitemap(idsDeputados: ReadonlyArray<string>, coleta?: Date): MetadataRoute.Sitemap {
  const comData = (caminho: string): MetadataRoute.Sitemap[number] => ({
    url: urlAbsoluta(caminho),
    ...(coleta ? { lastModified: coleta } : {}),
  });
  const fixas = ROTAS_FIXAS.map((r) => (SEM_DATA_DE_DADOS.has(r) ? { url: urlAbsoluta(r) } : comData(r)));
  const ids = [...new Set(idsDeputados)].filter((id) => ID_SEGURO.test(id));
  return [...fixas, ...ids.map((id) => comData(`/deputado/${id}`))];
}
