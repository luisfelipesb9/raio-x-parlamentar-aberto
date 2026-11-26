import { describe, expect, it } from "vitest";
import { canonical, limitaDescricao, urlAbsoluta } from "./seo";

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
});
