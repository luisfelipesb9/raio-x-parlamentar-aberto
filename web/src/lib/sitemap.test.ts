import { describe, expect, it } from "vitest";
import { ROTAS_FIXAS, fallbackSeBuild, montaSitemap, ultimaColeta } from "./sitemap";
import { SITE_URL } from "./seo";

describe("ultimaColeta", () => {
  it("escolhe a coleta mais recente entre as fontes", () => {
    const d = ultimaColeta({
      fontes: [
        { coletado_em_max: "2026-11-01T10:00:00Z" },
        { coletado_em_max: "2026-11-20T08:30:00Z" },
        { coletado_em_max: null },
      ],
    });
    expect(d?.toISOString()).toBe("2026-11-20T08:30:00.000Z");
  });

  it("devolve undefined (não inventa data) sem cobertura, sem fontes ou com data inválida", () => {
    expect(ultimaColeta(null)).toBeUndefined();
    expect(ultimaColeta({ fontes: [] })).toBeUndefined();
    expect(ultimaColeta({ fontes: [{ coletado_em_max: null }, { coletado_em_max: "xx" }] })).toBeUndefined();
  });
});

describe("montaSitemap", () => {
  it("sempre traz as rotas fixas, com URL absoluta", () => {
    const urls = montaSitemap([]).map((e) => e.url);
    for (const r of ROTAS_FIXAS) expect(urls).toContain(`${SITE_URL}${r}`);
    expect(ROTAS_FIXAS).toEqual(["/", "/deputados", "/grafo", "/perguntar", "/comparar", "/glossario", "/fontes"]);
  });

  it("acrescenta uma entrada por deputado, sem repetir id", () => {
    const urls = montaSitemap(["9900001", "9900002", "9900001"]).map((e) => e.url);
    expect(urls.filter((u) => u.includes("/deputado/"))).toEqual([`${SITE_URL}/deputado/9900001`, `${SITE_URL}/deputado/9900002`]);
  });

  it("usa a data da coleta nas páginas que mostram dados, mas não no glossário", () => {
    const coleta = new Date("2026-11-20T08:30:00Z");
    const s = montaSitemap(["9900001"], coleta);
    const por = (u: string) => s.find((e) => e.url === `${SITE_URL}${u}`);
    expect(por("/deputado/9900001")?.lastModified).toEqual(coleta);
    expect(por("/")?.lastModified).toEqual(coleta);
    expect(por("/glossario")).not.toHaveProperty("lastModified");
  });

  it("sem data de coleta, nenhuma entrada ganha lastModified", () => {
    for (const e of montaSitemap(["1"])) expect(e).not.toHaveProperty("lastModified");
  });

  it("ignora ids que não são seguros para URL", () => {
    const urls = montaSitemap(["12", "../x", "a b", ""]).map((e) => e.url);
    expect(urls.filter((u) => u.includes("/deputado/"))).toEqual([`${SITE_URL}/deputado/12`]);
  });
});

describe("fallbackSeBuild", () => {
  const erro = new Error("API fora do ar");

  it("durante o build devolve só as rotas fixas, sem quebrar", () => {
    const s = fallbackSeBuild(erro, "phase-production-build");
    expect(s.map((e) => e.url)).toEqual(ROTAS_FIXAS.map((r) => `${SITE_URL}${r}`));
  });

  it.each([undefined, "phase-production-server", "phase-development-server"])("em runtime (%s) relança o erro para o Next manter a versão anterior", (fase) => {
    expect(() => fallbackSeBuild(erro, fase)).toThrow(erro);
  });
});

describe("páginas de conteúdo no sitemap", () => {
  const extras = [
    { caminho: "/metodo", atualizado: "2026-11-20" },
    { caminho: "/regras/R01" },
    { caminho: "/glossario/ceap" },
  ];

  it("entram depois das rotas fixas e das fichas, com URL absoluta", () => {
    const urls = montaSitemap(["9900001"], undefined, extras).map((e) => e.url);
    expect(urls.slice(-4)).toEqual([`${SITE_URL}/deputado/9900001`, `${SITE_URL}/metodo`, `${SITE_URL}/regras/R01`, `${SITE_URL}/glossario/ceap`]);
  });

  it("lastModified é a data 'atualizado' do texto (nunca a da coleta) e só existe quando o texto tem data", () => {
    const coleta = new Date("2026-11-25T00:00:00Z");
    const s = montaSitemap([], coleta, extras);
    const por = (u: string) => s.find((e) => e.url === `${SITE_URL}${u}`);
    expect(por("/metodo")?.lastModified).toEqual(new Date("2026-11-20T00:00:00Z"));
    expect(por("/regras/R01")).not.toHaveProperty("lastModified");
    expect(por("/glossario/ceap")).not.toHaveProperty("lastModified");
  });

  it("sem a API (fallback do build) as páginas de conteúdo continuam no sitemap", () => {
    const urls = fallbackSeBuild(new Error("x"), "phase-production-build", extras).map((e) => e.url);
    expect(urls).toContain(`${SITE_URL}/metodo`);
    expect(urls).toContain(`${SITE_URL}/`);
  });

  it("não repete uma rota que já é fixa", () => {
    const urls = montaSitemap([], undefined, [{ caminho: "/glossario" }]).map((e) => e.url);
    expect(urls.filter((u) => u === `${SITE_URL}/glossario`)).toHaveLength(1);
  });
});
