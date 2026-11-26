import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { REVALIDAR_SEGUNDOS } from "./seo";

/**
 * O Next só lê `export const revalidate` quando é um literal (não aceita importar a constante).
 * Este teste impede que o literal das páginas com ISR se afaste de REVALIDAR_SEGUNDOS (lib/seo.ts).
 */
const PAGINAS_ISR = ["app/deputado/[id]/page.tsx", "app/deputados/page.tsx", "app/page.tsx"];

describe("revalidate das páginas com ISR", () => {
  it.each(PAGINAS_ISR)("%s declara revalidate = REVALIDAR_SEGUNDOS", (arquivo) => {
    const fonte = readFileSync(path.join(__dirname, "..", arquivo), "utf-8");
    const m = /^export const revalidate = (\d+);/m.exec(fonte);
    expect(m, `${arquivo} precisa de "export const revalidate = <literal>;"`).not.toBeNull();
    expect(Number(m?.[1])).toBe(REVALIDAR_SEGUNDOS);
  });
});
