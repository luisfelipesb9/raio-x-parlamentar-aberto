/** Agrupamento da lista pública de deputados por UF (sem React). Ordem alfabética: nunca ranking. */
import type { DeputadoResumo } from "@/types/contracts";

export const SEM_UF = "UF não informada";

export interface GrupoUf {
  uf: string;
  deputados: DeputadoResumo[];
}

const porNome = new Intl.Collator("pt-BR", { sensitivity: "base" });

export function agrupaPorUf(deputados: ReadonlyArray<DeputadoResumo>): GrupoUf[] {
  const mapa = new Map<string, DeputadoResumo[]>();
  for (const dep of deputados) {
    const chave = dep.uf?.trim() || SEM_UF;
    const lista = mapa.get(chave);
    if (lista) lista.push(dep);
    else mapa.set(chave, [dep]);
  }
  const grupos = [...mapa].map(([uf, lista]) => ({ uf, deputados: lista.sort((a, b) => porNome.compare(a.nome, b.nome)) }));
  // o grupo "sem UF" vai por último; as demais, em ordem alfabética
  return grupos.sort((a, b) => (a.uf === SEM_UF ? 1 : b.uf === SEM_UF ? -1 : porNome.compare(a.uf, b.uf)));
}
