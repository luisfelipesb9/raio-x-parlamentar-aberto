import { describe, expect, it } from "vitest";
import type { Finding } from "@/types/contracts";
import { descricaoFicha, resumoFicha, tituloFicha } from "./ficha-seo";

const perfil = { id: "9900001", nome: "Ana Exemplo", partido: "PXX", uf: "MG" };

const alerta = (cf: number, nivel: Finding["nivel"]): Pick<Finding, "cf" | "nivel"> => ({ cf, nivel });

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
  it("abre com partido e UF, sem citar alerta quando não há nenhum", () => {
    const r = resumoFicha(perfil, []);
    expect(r.frase).toBe("Deputado(a) federal pelo PXX, eleito(a) por MG.");
    expect(r.alertas).toBe("Nenhum alerta nos dados já carregados; isso não quer dizer que esteja tudo certo.");
  });

  it("usa o singular e cita o maior nível de certeza", () => {
    const r = resumoFicha(perfil, [alerta(0.5, "media")]);
    expect(r.alertas).toBe("Os dados públicos mostram 1 alerta (um padrão nos dados, não uma acusação); o de maior certeza é: Certeza média.");
  });

  it("usa o plural e escolhe o alerta de maior cf, não o primeiro da lista", () => {
    const r = resumoFicha(perfil, [alerta(0.25, "indicio"), alerta(0.8, "alta"), alerta(0.5, "media")]);
    expect(r.alertas).toBe("Os dados públicos mostram 3 alertas (padrões nos dados, não acusações); o de maior certeza é: Certeza alta.");
  });

  it("tolera partido e UF ausentes", () => {
    expect(resumoFicha({ ...perfil, partido: null, uf: null }, []).frase).toBe("Deputado(a) federal.");
    expect(resumoFicha({ ...perfil, uf: null }, []).frase).toBe("Deputado(a) federal pelo PXX.");
    expect(resumoFicha({ ...perfil, partido: null }, []).frase).toBe("Deputado(a) federal, eleito(a) por MG.");
  });
});

describe("descricaoFicha", () => {
  it("junta as duas frases do resumo", () => {
    expect(descricaoFicha(perfil, [])).toBe(
      "Deputado(a) federal pelo PXX, eleito(a) por MG. Nenhum alerta nos dados já carregados; isso não quer dizer que esteja tudo certo.",
    );
  });

  it("nunca passa de 160 caracteres", () => {
    const d = descricaoFicha(perfil, [alerta(0.8, "alta"), alerta(0.5, "media")]);
    expect(d.length).toBeLessThanOrEqual(160);
    expect(d).toMatch(/^Deputado\(a\) federal pelo PXX/);
  });

  it("não usa palavras que sugiram culpa", () => {
    const d = descricaoFicha(perfil, [alerta(0.8, "alta")]).toLowerCase();
    for (const proibida of ["culpa", "corrup", "criminos", "ladr", "fraude", "condena"]) expect(d).not.toContain(proibida);
  });
});
