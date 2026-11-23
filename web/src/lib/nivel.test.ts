import { describe, expect, it } from "vitest";
import { NIVEIS, nivelDeCf, formataCf } from "./nivel";

describe("nivelDeCf (espelha Nivel.from_cf do backend)", () => {
  it.each([
    [1, "alta"],
    [0.7, "alta"],
    [0.69, "media"],
    [0.4, "media"],
    [0.39, "indicio"],
    [0.2, "indicio"],
    [0.19, "inconclusivo"],
    [0, "inconclusivo"],
    [-0.5, "inconclusivo"],
  ])("cf %s => %s", (cf, esperado) => {
    expect(nivelDeCf(cf)).toBe(esperado);
  });
});

describe("NIVEIS", () => {
  it("todo nível tem rótulo em texto, número de barras e explicação para leigo", () => {
    for (const nivel of ["alta", "media", "indicio", "inconclusivo"] as const) {
      const n = NIVEIS[nivel];
      expect(n.rotulo.length).toBeGreaterThan(3);
      expect(n.barras).toBeGreaterThanOrEqual(1);
      expect(n.explicacao.length).toBeGreaterThan(20);
    }
    expect(NIVEIS.alta.barras).toBeGreaterThan(NIVEIS.media.barras);
    expect(NIVEIS.media.barras).toBeGreaterThan(NIVEIS.indicio.barras);
    expect(NIVEIS.indicio.barras).toBeGreaterThan(NIVEIS.inconclusivo.barras);
  });

  it("inconclusivo nunca é apresentado como ausência de problema", () => {
    expect(NIVEIS.inconclusivo.explicacao.toLowerCase()).toContain("não significa");
  });
});

describe("formataCf", () => {
  it("usa vírgula decimal e duas casas (pt-BR)", () => {
    expect(formataCf(0.665)).toBe("0,67");
    expect(formataCf(1)).toBe("1,00");
  });
});
