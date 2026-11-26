import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { FAMILIAS } from "./grafo-mapa";
import { TIPOS_NO } from "./grafo";

/**
 * Contraste WCAG 2.x calculado sobre os tokens reais de globals.css, nos dois temas.
 * Texto: >= 4,5:1 (1.4.3). Nós, arestas e bordas do mapa: >= 3:1 (1.4.11).
 */
const CSS = readFileSync(fileURLToPath(new URL("../app/globals.css", import.meta.url)), "utf8");

function bloco(abre: string): Record<string, string> {
  const i = CSS.indexOf(abre);
  if (i < 0) throw new Error(`bloco não encontrado: ${abre}`);
  const corpo = CSS.slice(i + abre.length, CSS.indexOf("\n}", i));
  const tokens: Record<string, string> = {};
  for (const m of corpo.matchAll(/(--[\w-]+):\s*([^;]+);/g)) tokens[m[1]!] = m[2]!.trim();
  return tokens;
}

const claro = bloco(":root {");
const escuro = { ...claro, ...bloco(':root[data-theme="dark"] {') };

const luminancia = (hex: string): number => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
export function contraste(a: string, b: string): number {
  const [claroL, escuroL] = [luminancia(a), luminancia(b)].sort((x, y) => y - x) as [number, number];
  return (claroL + 0.05) / (escuroL + 0.05);
}

const temas = [
  ["claro", claro],
  ["escuro", escuro],
] as const;

describe("contraste dos tokens do mapa (WCAG AA)", () => {
  for (const [nome, t] of temas) {
    const fundo = t["--surface-solida"]!;
    const pagina = t["--bg"]!;

    it(`${nome}: texto (--fg, --muted) passa de 4,5:1 sobre o canvas e a página`, () => {
      expect(contraste(t["--fg"]!, fundo)).toBeGreaterThanOrEqual(4.5);
      expect(contraste(t["--muted"]!, fundo)).toBeGreaterThanOrEqual(4.5);
      expect(contraste(t["--muted"]!, pagina)).toBeGreaterThanOrEqual(4.5);
      expect(contraste(t["--acento-fg"]!, t["--acento"]!)).toBeGreaterThanOrEqual(4.5);
    });

    it(`${nome}: os 6 tipos de nó passam de 3:1 sobre o canvas`, () => {
      for (const [tipo, info] of Object.entries(TIPOS_NO)) {
        expect(contraste(t[info.cor]!, fundo), `${tipo} (${info.cor})`).toBeGreaterThanOrEqual(3);
      }
    });

    it(`${nome}: as 4 famílias de aresta existem e passam de 3:1 sobre o canvas`, () => {
      for (const [fam, info] of Object.entries(FAMILIAS)) {
        expect(t[info.cor], `${fam} (${info.cor}) sem valor no tema ${nome}`).toBeDefined();
        expect(contraste(t[info.cor]!, fundo), `${fam} (${info.cor})`).toBeGreaterThanOrEqual(3);
      }
    });

    it(`${nome}: bordas do super-nó, da seleção e da sanção passam de 3:1 sobre o canvas`, () => {
      for (const token of ["--borda-forte", "--acento", "--perigo", "--fg"]) {
        expect(contraste(t[token]!, fundo), token).toBeGreaterThanOrEqual(3);
      }
    });
  }

  it("as famílias de aresta têm cores diferentes entre si em cada tema", () => {
    for (const [, t] of temas) {
      const cores = Object.values(FAMILIAS).map((f) => t[f.cor]);
      expect(new Set(cores).size).toBe(cores.length);
    }
  });
});
