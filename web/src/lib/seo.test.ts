import { describe, expect, it } from "vitest";
import { ID_SEGURO, canonical, limitaDescricao, permiteIndexar, urlAbsoluta } from "./seo";

describe("seo", () => {
  it("monta URL absoluta sem barra dupla", () => {
    expect(urlAbsoluta("/deputado/1")).toBe("http://localhost:3000/deputado/1");
    expect(urlAbsoluta("fontes")).toBe("http://localhost:3000/fontes");
  });

  it("canonical usa a URL absoluta", () => {
    expect(canonical("/glossario")).toEqual({ canonical: "http://localhost:3000/glossario" });
  });

  it("limitaDescricao não parte palavra e termina com reticências", () => {
    const t = "Votou com o governo em quase todas as votações nominais da janela de dados observada pelo sistema.";
    const d = limitaDescricao(t, 60);
    expect(d.length).toBeLessThanOrEqual(60);
    expect(d.endsWith("…")).toBe(true);
    expect(d).not.toMatch(/\s…$/);
  });

  it("limitaDescricao mantém texto curto e normaliza espaços", () => {
    expect(limitaDescricao("  um   texto \n curto ")).toBe("um texto curto");
  });

  it("ID_SEGURO aceita o formato de id da API e recusa o resto", () => {
    for (const ok of ["9900001", "a_b-9", "x".repeat(32)]) expect(ID_SEGURO.test(ok), ok).toBe(true);
    for (const ruim of ["", "../x", "a b", "a<b", "x".repeat(33), "1/2"]) expect(ID_SEGURO.test(ruim), ruim).toBe(false);
  });
});

describe("permiteIndexar", () => {
  it("indexa um site público em produção ou sem VERCEL_ENV", () => {
    expect(permiteIndexar("https://raio-x.example.org", undefined)).toBe(true);
    expect(permiteIndexar("https://raio-x.example.org", "production")).toBe(true);
  });

  it("não indexa localhost, em nenhuma forma", () => {
    for (const u of ["http://localhost:3000", "http://127.0.0.1:3000", "http://[::1]:3000", "http://app.localhost:3000"]) {
      expect(permiteIndexar(u, undefined), u).toBe(false);
    }
  });

  it("não indexa deploy de pré-visualização, mesmo com endereço público", () => {
    expect(permiteIndexar("https://raio-x.example.org", "preview")).toBe(false);
  });

  it("endereço inválido não indexa", () => {
    expect(permiteIndexar("isto não é url", undefined)).toBe(false);
  });
});
