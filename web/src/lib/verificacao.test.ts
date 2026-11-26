import { describe, expect, it } from "vitest";
import { formataData, linhasMetricas, nivelMaximoR01, nomeRegra, periodoColeta, rotuloFonte, rotuloMetrica } from "./verificacao";

describe("formataData", () => {
  it("data pura (AAAA-MM-DD) não muda de dia por fuso", () => {
    expect(formataData("2025-02-04")).toBe("04/02/2025");
    expect(formataData("2025-03-27")).toBe("27/03/2025");
  });

  it("instante com hora vira a data no horário de Brasília", () => {
    expect(formataData("2026-11-23T01:10:04.431378Z")).toBe("22/11/2026");
    expect(formataData("2026-11-23T15:00:00Z")).toBe("23/11/2026");
  });

  it("vazio ou inválido vira travessão, nunca 'Invalid Date'", () => {
    expect(formataData(null)).toBe("—");
    expect(formataData(undefined)).toBe("—");
    expect(formataData("ontem")).toBe("—");
  });
});

describe("periodoColeta", () => {
  it("mesmo dia vira 'em' e dias diferentes viram 'de … a …'", () => {
    expect(periodoColeta("2026-11-23T15:00:00Z", "2026-11-23T16:00:00Z")).toBe("em 23/11/2026");
    expect(periodoColeta("2026-11-20T15:00:00Z", "2026-11-23T15:00:00Z")).toBe("de 20/11/2026 a 23/11/2026");
  });

  it("sem datas diz que não há registro", () => {
    expect(periodoColeta(null, null)).toBe("sem data registrada");
  });
});

describe("rotuloFonte", () => {
  it("troca o id técnico por um nome que a pessoa reconhece", () => {
    expect(rotuloFonte("camara_ceap")).toMatch(/cota parlamentar/i);
    expect(rotuloFonte("tse_prestacao_contas")).toMatch(/doa/i);
  });

  it("fonte desconhecida não quebra: mostra o id legível", () => {
    expect(rotuloFonte("fonte_nova")).toBe("fonte nova");
  });
});

describe("rotuloMetrica e linhasMetricas", () => {
  it("traduz as chaves do motor", () => {
    expect(rotuloMetrica("n_votacoes")).toBe("Votações consideradas");
    expect(rotuloMetrica("chave_desconhecida")).toBe("chave desconhecida");
  });

  it("formata valores por tipo (porcentagem, reais, contagem) e esconde a duplicata taxa_pct", () => {
    const linhas = linhasMetricas({ taxa_governismo: 0.846, taxa_pct: 85, n_votacoes: 13, valor_emendas: 256801560.16, categoria_top: "Combustíveis" });
    expect(linhas.map((l) => l.chave)).not.toContain("taxa_pct");
    const por = Object.fromEntries(linhas.map((l) => [l.chave, l.valor]));
    expect(por["taxa_governismo"]).toBe("85%");
    expect(por["n_votacoes"]).toBe("13");
    expect(por["valor_emendas"]).toMatch(/R\$\s?256\.801\.560/);
    expect(por["categoria_top"]).toBe("Combustíveis");
  });

  it("sem valores devolve lista vazia", () => {
    expect(linhasMetricas({})).toEqual([]);
  });
});

describe("nomeRegra", () => {
  it("dá nome de leigo às regras e não quebra com regra nova", () => {
    expect(nomeRegra("R01")).toMatch(/governo/i);
    expect(nomeRegra("R07")).toMatch(/emendas/i);
    expect(nomeRegra("R99")).toBe("Regra R99");
  });
});

describe("nivelMaximoR01", () => {
  it("com menos de 30 votações com orientação a penalidade de 0,7 limita a certeza a 0,665", () => {
    expect(nivelMaximoR01(22)).toBeCloseTo(0.665, 5);
    expect(nivelMaximoR01(29)).toBeCloseTo(0.665, 5);
  });

  it("com 30 ou mais votações o teto é o CF base da regra (0,95)", () => {
    expect(nivelMaximoR01(30)).toBe(0.95);
    expect(nivelMaximoR01(150)).toBe(0.95);
  });
});
