import { describe, expect, it } from "vitest";
import { OBJETIVOS } from "./formato";

describe("OBJETIVOS (perguntar ao sistema)", () => {
  it("usa exatamente os objetivos do engine", () => {
    expect(OBJETIVOS.map((o) => o.id).sort()).toEqual(
      ["alinhado_governo", "concentracao_eleitoral_emendas", "merece_atencao_fiscalizacao", "pontuacao_producao_legislativa", "risco_integridade"].sort(),
    );
  });

  it("a produção legislativa é descrita como medida, não como pergunta de sim/não", () => {
    const o = OBJETIVOS.find((x) => x.id === "pontuacao_producao_legislativa");
    expect(o?.pergunta).toMatch(/pontuação/i);
    expect(o?.pergunta).not.toMatch(/relevante|produz bem/i);
  });
});
