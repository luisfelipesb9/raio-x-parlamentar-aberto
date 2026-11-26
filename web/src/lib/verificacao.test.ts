import { describe, expect, it } from "vitest";
import {
  formataData,
  formataTeto,
  linhasMetricas,
  listaTipos,
  nivelMaximoR01,
  nomeRegra,
  periodoColeta,
  R01_CF_BASE,
  R01_FATOR_POUCOS_VOTOS,
  R01_LIMIAR,
  R01_VOTOS_PARA_SEM_PENALIDADE,
  rotuloFonte,
  rotuloMetrica,
} from "./verificacao";

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

describe("listaTipos", () => {
  it("troca tipos de fato por palavras comuns e junta em uma frase", () => {
    expect(listaTipos(["despesa_ceap"])).toBe("despesas da cota");
    expect(listaTipos(["autoria", "deputado", "voto"])).toBe("autorias, deputados, votos");
    expect(listaTipos(["tipo_novo"])).toBe("tipo novo");
    expect(listaTipos([])).toBe("—");
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

  it("métricas da R06/R06b têm rótulo de leigo e valores em reais", () => {
    for (const chave of ["n_circuitos", "n_confirmados", "valor_ceap", "valor_doado"]) {
      expect(rotuloMetrica(chave)).not.toBe(chave.replaceAll("_", " "));
    }
    const linhas = linhasMetricas({ n_circuitos: 2, n_confirmados: 1, valor_ceap: 15234.5, valor_doado: 3000 });
    const por = Object.fromEntries(linhas.map((l) => [l.chave, l.valor]));
    expect(por["n_circuitos"]).toBe("2");
    expect(por["n_confirmados"]).toBe("1");
    expect(por["valor_ceap"]).toMatch(/^R\$\s?15\.235$/);
    expect(por["valor_doado"]).toMatch(/^R\$\s?3\.000$/);
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

describe("formataTeto", () => {
  it("mostra 0,665 sem arredondar para 0,67 e 0,95 com duas casas", () => {
    expect(formataTeto(0.95 * 0.7)).toBe("0,665");
    expect(formataTeto(0.95)).toBe("0,95");
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

describe("constantes e teto da R01", () => {
  it("exporta os números da regra para o texto da página de fontes", () => {
    expect(R01_CF_BASE).toBe(0.95);
    expect(R01_LIMIAR).toBe(0.7);
    expect(R01_FATOR_POUCOS_VOTOS).toBe(0.7);
    expect(R01_VOTOS_PARA_SEM_PENALIDADE).toBe(30);
  });

  it("o teto é 0,665 com poucos votos possíveis e volta a 0,95 com 30 ou mais", () => {
    expect(formataTeto(nivelMaximoR01(13))).toBe("0,665");
    expect(nivelMaximoR01(30)).toBe(0.95);
  });
});
