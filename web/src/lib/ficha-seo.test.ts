import { describe, expect, it } from "vitest";
import type { Finding } from "@/types/contracts";
import { descricaoFicha, resumoFicha, tituloFicha } from "./ficha-seo";

const perfil = { id: "9900001", nome: "Ana Exemplo", partido: "PXX", uf: "MG" };

const alerta = (cf: number, nivel: Finding["nivel"], conclusao = `Conclusão de teste com cf ${cf}.`): Pick<Finding, "cf" | "nivel" | "conclusao"> => ({
  cf,
  nivel,
  conclusao,
});

describe("tituloFicha", () => {
  it("monta 'Nome (PARTIDO-UF)'", () => {
    expect(tituloFicha(perfil)).toBe("Ana Exemplo (PXX-MG)");
  });

  it("omite o que a API não informou", () => {
    expect(tituloFicha({ ...perfil, partido: null })).toBe("Ana Exemplo (MG)");
    expect(tituloFicha({ ...perfil, uf: null })).toBe("Ana Exemplo (PXX)");
    expect(tituloFicha({ ...perfil, partido: null, uf: null })).toBe("Ana Exemplo");
  });
});

describe("resumoFicha", () => {
  it("sem alertas: texto neutro, sem atestar que está tudo certo", () => {
    expect(resumoFicha([])).toBe("Sem alertas nos dados disponíveis. Isso não quer dizer que esteja tudo certo.");
  });

  it("cita a CONCLUSÃO do alerta de maior nível, não só o rótulo do nível", () => {
    const r = resumoFicha([alerta(0.5, "media", "Votou com o governo em 80% das votações nominais.")]);
    expect(r).toBe(
      "Os dados públicos mostram 1 alerta (um padrão nos dados, não uma acusação). O de nível mais alto (certeza média) diz: Votou com o governo em 80% das votações nominais.",
    );
  });

  it("escolhe o de maior cf entre os conclusivos e usa o plural", () => {
    const r = resumoFicha([alerta(0.25, "indicio", "A."), alerta(0.8, "alta", "B."), alerta(0.5, "media", "C.")]);
    expect(r).toBe("Os dados públicos mostram 3 alertas (padrões nos dados, não acusações). O de nível mais alto (certeza alta) diz: B.");
  });

  it("formata decimais em pt-BR na conclusão", () => {
    expect(resumoFicha([alerta(0.9, "alta", "Alinhamento de 0.87 com o governo.")])).toContain("Alinhamento de 0,87 com o governo.");
  });

  it("inconclusivo não é citado como achado: diz que o sistema não chegou a conclusão", () => {
    const r = resumoFicha([alerta(0.1, "inconclusivo", "Dados insuficientes para afirmar algo sobre gastos.")]);
    expect(r).toBe("Os dados públicos mostram 1 alerta (um padrão nos dados, não uma acusação). O sistema não chegou a conclusão sobre aquele ponto.");
    expect(r).not.toContain("Dados insuficientes");
  });

  it("com vários inconclusivos, usa o plural", () => {
    const r = resumoFicha([alerta(0.1, "inconclusivo"), alerta(0.05, "inconclusivo")]);
    expect(r).toContain("2 alertas");
    expect(r).toContain("O sistema não chegou a conclusão sobre esses pontos.");
  });

  it("um conclusivo vence um inconclusivo mesmo com cf menor", () => {
    const r = resumoFicha([alerta(0.19, "inconclusivo", "X."), alerta(0.2, "indicio", "Y.")]);
    expect(r).toContain("(apenas indício) diz: Y.");
  });
});

describe("descricaoFicha", () => {
  const LONGA = "Recebeu pagamentos da cota parlamentar de uma única empresa em proporção muito acima da mediana dos demais deputados do mesmo estado, ".repeat(3);

  it("não repete partido/UF (já estão no título) e abre com o aviso de padrão nos dados", () => {
    const d = descricaoFicha([alerta(0.5, "media", "Curta.")]);
    expect(d).toMatch(/^Os dados públicos mostram 1 alerta/);
    expect(d).not.toContain("PXX");
    expect(d).not.toContain("Deputado(a)");
  });

  it("sem alertas: descrição neutra", () => {
    expect(descricaoFicha([])).toBe("Sem alertas nos dados disponíveis. Isso não quer dizer que esteja tudo certo.");
  });

  it("conclusão enorme: corta em até 160 caracteres e o 'não acusações' sobrevive ao corte", () => {
    const d = descricaoFicha([alerta(0.8, "alta", LONGA), alerta(0.5, "media")]);
    expect(d.length).toBeLessThanOrEqual(160);
    expect(d).toMatch(/não acusaç/);
    expect(d).toContain("certeza alta");
  });

  it("singular também mantém 'não uma acusação' depois do corte", () => {
    const d = descricaoFicha([alerta(0.8, "alta", LONGA)]);
    expect(d.length).toBeLessThanOrEqual(160);
    expect(d).toMatch(/não uma acusaç/);
  });

  it("inconclusivo: não cita a conclusão como achado", () => {
    const d = descricaoFicha([alerta(0.1, "inconclusivo", "Texto que não pode virar achado.")]);
    expect(d).toContain("não chegou a conclusão");
    expect(d).not.toContain("não pode virar achado");
  });
});

describe("linguagem: nunca sugere culpa", () => {
  const PROIBIDAS = ["culpa", "corrup", "criminos", "ladr", "fraude", "condena"];
  const casos: [string, Parameters<typeof resumoFicha>[0]][] = [
    ["sem alertas", []],
    ["um conclusivo", [alerta(0.8, "alta")]],
    ["vários níveis", [alerta(0.25, "indicio"), alerta(0.8, "alta"), alerta(0.5, "media")]],
    ["só inconclusivo", [alerta(0.1, "inconclusivo")]],
    ["conclusão longa", [alerta(0.8, "alta", "Texto longo ".repeat(40))]],
  ];

  it.each(casos)("resumo e descrição (%s)", (_nome, findings) => {
    for (const texto of [resumoFicha(findings), descricaoFicha(findings)]) {
      for (const p of PROIBIDAS) expect(texto.toLowerCase()).not.toContain(p);
    }
  });
});
