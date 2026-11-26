import { describe, expect, it } from "vitest";
import { OBJETIVOS, decimaisPtBr, origemDoCadastro } from "./formato";

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

describe("decimaisPtBr (números do texto das conclusões em pt-BR)", () => {
  it.each([
    ["Produção legislativa: 5.8 de 40 pontos (3 projetos).", "Produção legislativa: 5,8 de 40 pontos (3 projetos)."],
    ["cerca de 2.5x o que um deputado típico gasta", "cerca de 2,5x o que um deputado típico gasta"],
    ["Gastou R$ 1234.56 em 'Divulgação'", "Gastou R$ 1234,56 em 'Divulgação'"],
    ["pontos 20.23 de 40.0", "pontos 20,23 de 40,0"],
  ])("troca o ponto decimal por vírgula: %s", (entrada, esperado) => {
    expect(decimaisPtBr(entrada)).toBe(esperado);
  });

  it.each([
    "R$ 1.234.567 em emendas",
    "versão v1.2 do contrato",
    "CNPJ 12.345.678/0001-95",
    "Em 30. Depois seguiu",
    "já está em 5,8 de 40",
    "sem números",
  ])("não mexe em separador de milhar, versão, CNPJ nem pontuação: %s", (texto) => {
    expect(decimaisPtBr(texto)).toBe(texto);
  });
});

describe("origemDoCadastro (texto da ficha sobre a foto)", () => {
  it("cita a foto só quando há URL real", () => {
    expect(origemDoCadastro("https://www.camara.leg.br/internet/deputado/bandep/1.jpg")).toBe(
      "Cadastro e foto oficiais da Câmara dos Deputados.",
    );
  });

  it.each([null, "", "   "])("sem foto (%j) fala só do cadastro", (foto) => {
    expect(origemDoCadastro(foto)).toBe("Cadastro oficial da Câmara dos Deputados.");
  });
});
