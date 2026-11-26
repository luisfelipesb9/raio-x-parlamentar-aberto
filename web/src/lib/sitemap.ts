/** Montagem pura do sitemap (a leitura da API fica em `app/sitemap.ts`). */
import type { MetadataRoute } from "next";
import { ID_SEGURO, urlAbsoluta } from "./seo";

export const ROTAS_FIXAS = ["/", "/deputados", "/grafo", "/perguntar", "/comparar", "/glossario", "/fontes"] as const;

/** Rotas cujo texto não depende dos dados coletados: não recebem `lastModified`. */
const SEM_DATA_DE_DADOS = new Set<string>(["/glossario"]);

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

/** Página de conteúdo (método, regras, termos): `atualizado` é a data AAAA-MM-DD do próprio texto, quando ele tem uma. */
export type RotaDeConteudoSitemap = { caminho: string; atualizado?: string };

export function montaSitemap(idsDeputados: ReadonlyArray<string>, coleta?: Date, conteudo: ReadonlyArray<RotaDeConteudoSitemap> = []): MetadataRoute.Sitemap {
  const comData = (caminho: string): MetadataRoute.Sitemap[number] => ({
    url: urlAbsoluta(caminho),
    ...(coleta ? { lastModified: coleta } : {}),
  });
  const fixas = ROTAS_FIXAS.map((r) => (SEM_DATA_DE_DADOS.has(r) ? { url: urlAbsoluta(r) } : comData(r)));
  const ids = [...new Set(idsDeputados)].filter((id) => ID_SEGURO.test(id));
  const fixasSet = new Set<string>(ROTAS_FIXAS);
  const paginas = conteudo
    .filter((p, i, todas) => !fixasSet.has(p.caminho) && todas.findIndex((q) => q.caminho === p.caminho) === i)
    .map((p) => {
      const data = p.atualizado ? new Date(`${p.atualizado}T00:00:00Z`) : undefined;
      return { url: urlAbsoluta(p.caminho), ...(data && !Number.isNaN(data.getTime()) ? { lastModified: data } : {}) };
    });
  return [...fixas, ...ids.map((id) => comData(`/deputado/${id}`)), ...paginas];
}

/**
 * Falha ao ler a API. Só durante o build (`NEXT_PHASE === "phase-production-build"`, ex.: CI sem API) devolve as rotas
 * fixas. Em runtime relança o erro: o Next mantém a versão anterior do sitemap em vez de publicar um sitemap sem fichas.
 */
export function fallbackSeBuild(erro: unknown, fase: string | undefined, conteudo: ReadonlyArray<RotaDeConteudoSitemap> = []): MetadataRoute.Sitemap {
  if (fase === "phase-production-build") return montaSitemap([], undefined, conteudo);
  throw erro;
}
