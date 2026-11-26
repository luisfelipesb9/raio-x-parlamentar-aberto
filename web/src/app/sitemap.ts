import type { MetadataRoute } from "next";
import type { CoberturaResposta, DeputadoResumo } from "@/types/contracts";
import { servidorGet, servidorTodosDeputados } from "@/lib/server-api";
import { montaSitemap, ultimaColeta } from "@/lib/sitemap";

// Precisa ser um literal (o Next lê isto na análise do build). Mesmo valor de REVALIDAR_SEGUNDOS em lib/seo.ts.
export const revalidate = 3600;

/** Rotas fixas + uma ficha por deputado. Se a API não responder (ex.: build no CI), devolve só as rotas fixas. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  try {
    const [deputados, cobertura] = await Promise.all([
      servidorTodosDeputados<DeputadoResumo>(),
      servidorGet<CoberturaResposta>("/cobertura").catch(() => null),
    ]);
    return montaSitemap(
      deputados.map((d) => d.id),
      ultimaColeta(cobertura),
    );
  } catch {
    return montaSitemap([]);
  }
}
