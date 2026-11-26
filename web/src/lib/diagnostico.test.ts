import { describe, expect, it } from "vitest";
import type { Diagnostico } from "@/types/contracts";
import { fraseDiagnostico, resumoDiagnosticos } from "./diagnostico";

const diag = (motivo: Diagnostico["motivo"], detalhes: Diagnostico["detalhes"] = {}): Diagnostico => ({ motivo, detalhes });

describe("fraseDiagnostico", () => {
  it("dados insuficientes diz quantos votos válidos há e quantos o sistema exige", () => {
    const f = fraseDiagnostico(diag("dados_insuficientes", { n_votos_validos: 4, minimo_votos: 10, taxa: 0.5 }));
    expect(f).toBe("Só encontramos 4 votos válidos para este deputado e o sistema precisa de pelo menos 10 para concluir.");
  });

  it("usa o singular com um único voto válido", () => {
    const f = fraseDiagnostico(diag("dados_insuficientes", { n_votos_validos: 1, minimo_votos: 10 }));
    expect(f).toContain("Só encontramos 1 voto válido para este deputado");
  });

  it("sem nenhum voto válido não diz 'só encontramos 0'", () => {
    const f = fraseDiagnostico(diag("dados_insuficientes", { n_votos_validos: 0, minimo_votos: 10 }));
    expect(f).toBe("Não encontramos nenhum voto válido para este deputado e o sistema precisa de pelo menos 10 para concluir.");
  });

  it("abaixo do limiar traz taxa e limiar em porcentagem e não sugere nada contra o deputado", () => {
    const f = fraseDiagnostico(diag("abaixo_do_limiar", { n_votos_validos: 120, minimo_votos: 10, taxa: 0.62, limiar: 0.7 }));
    expect(f).toBe(
      "Com 120 votos válidos, 62% acompanharam a orientação do governo; o sistema só conclui 'alinhado' a partir de 70%. " +
        "Isso não indica nada contra o deputado: só mostra que o padrão procurado não apareceu.",
    );
  });

  it("não deixa o arredondamento igualar a taxa ao limiar (69,9% não vira 70%)", () => {
    const f = fraseDiagnostico(diag("abaixo_do_limiar", { n_votos_validos: 300, minimo_votos: 10, taxa: 0.699, limiar: 0.7 }));
    expect(f).toContain("69,9% acompanharam");
    expect(f).toContain("a partir de 70%");
  });

  it("sem regra aplicável mantém o texto atual", () => {
    expect(fraseDiagnostico(diag("sem_regra_aplicavel"))).toBe("Os dados atuais não ativam esta regra.");
  });

  it("diagnóstico sem os números esperados cai no texto genérico em vez de mostrar 'undefined'", () => {
    expect(fraseDiagnostico(diag("abaixo_do_limiar", {}))).toBe("Os dados atuais não ativam esta regra.");
    expect(fraseDiagnostico(diag("dados_insuficientes", {}))).toBe("Os dados atuais não ativam esta regra.");
  });

  it("sem diagnóstico (null) devolve o texto genérico", () => {
    expect(fraseDiagnostico(null)).toBe("Os dados atuais não ativam esta regra.");
  });
});

describe("resumoDiagnosticos", () => {
  it("junta as frases dos passos com diagnóstico, sem repetir", () => {
    const d = diag("dados_insuficientes", { n_votos_validos: 4, minimo_votos: 10 });
    const r = resumoDiagnosticos([
      { diagnostico: d },
      { diagnostico: null },
      { diagnostico: { ...d } },
      { diagnostico: diag("sem_regra_aplicavel") },
    ]);
    expect(r.frases).toHaveLength(2);
  });

  it("sugere ver a cobertura quando falta dado e outra pergunta quando não há regra aplicável", () => {
    expect(resumoDiagnosticos([{ diagnostico: diag("dados_insuficientes", { n_votos_validos: 1, minimo_votos: 10 }) }]).proximos).toEqual([
      "cobertura",
      "outra-pergunta",
    ]);
    expect(resumoDiagnosticos([{ diagnostico: diag("sem_regra_aplicavel") }]).proximos).toEqual(["outra-pergunta", "cobertura"]);
  });

  it("lista vazia não gera frases", () => {
    expect(resumoDiagnosticos([]).frases).toEqual([]);
  });
});
