import type { MetadataRoute } from "next";
import type { CoberturaResposta, DeputadoResumo } from "@/types/contracts";
import { CONTEUDO } from "@/content/conteudo";
import { rotasDeConteudo } from "@/content/rotas";
import { GLOSSARIO } from "@/lib/glossario";
import { servidorGet, servidorTodosDeputados } from "@/lib/server-api";
import { fallbackSeBuild, montaSitemap, ultimaColeta } from "@/lib/sitemap";

// Precisa ser um literal (o Next lê isto na análise do build). Mesmo valor de REVALIDAR_SEGUNDOS em lib/seo.ts.
export const revalidate = 3600;

/**
 * Rotas fixas + uma ficha por deputado. Se a API não responder: no build (ex.: CI) devolve só as rotas fixas;
 * em runtime relança o erro e o Next mantém o sitemap anterior.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // método, regras e glossário vêm dos arquivos do repositório: entram mesmo sem a API
  const paginas = rotasDeConteudo(CONTEUDO, GLOSSARIO);
  try {
    const [deputados, cobertura] = await Promise.all([
      servidorTodosDeputados<DeputadoResumo>(),
      servidorGet<CoberturaResposta>("/cobertura").catch(() => null),
    ]);
    return montaSitemap(
      deputados.map((d) => d.id),
      ultimaColeta(cobertura),
      paginas,
    );
  } catch (e) {
    return fallbackSeBuild(e, process.env.NEXT_PHASE, paginas);
  }
}
