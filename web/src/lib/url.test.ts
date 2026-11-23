import { describe, expect, it } from "vitest";
import { urlSegura } from "./url";

describe("urlSegura", () => {
  it("aceita só http(s)", () => {
    expect(urlSegura("https://dadosabertos.camara.leg.br/api/v2/votacoes/1")).toBe("https://dadosabertos.camara.leg.br/api/v2/votacoes/1");
    expect(urlSegura("http://exemplo.gov.br/x")).toBe("http://exemplo.gov.br/x");
  });

  it.each(["javascript:alert(1)", "data:text/html,<b>x</b>", "ftp://x.org/a", "//evil.com/x", "/relativo", "", "not a url", " JavaScript:alert(1)"])(
    "rejeita %j",
    (u) => {
      expect(urlSegura(u)).toBeNull();
    },
  );

  it("null/undefined viram null", () => {
    expect(urlSegura(null)).toBeNull();
    expect(urlSegura(undefined)).toBeNull();
  });
});
