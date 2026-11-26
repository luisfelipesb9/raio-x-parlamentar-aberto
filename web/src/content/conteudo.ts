/** O conteúdo gerado (committed), tipado. Para regenerar: `pnpm gen:conteudo`. */
import dados from "./gerado/conteudo.json";
import type { Conteudo } from "./tipos";

export const CONTEUDO = dados as unknown as Conteudo;
