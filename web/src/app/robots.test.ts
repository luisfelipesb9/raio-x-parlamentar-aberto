import { describe, expect, it } from "vitest";
import robots from "./robots";
import { SITE_URL } from "@/lib/seo";

type Regra = { userAgent?: string | string[]; allow?: string | string[]; disallow?: string | string[] };

function regras(): Regra[] {
  const r = robots().rules;
  return (Array.isArray(r) ? r : [r]) as Regra[];
}
const agentes = (r: Regra) => (Array.isArray(r.userAgent) ? r.userAgent : [r.userAgent ?? ""]);
const regraDe = (bot: string) => regras().find((r) => agentes(r).includes(bot));

describe("robots", () => {
  it("libera todo o site para qualquer robô", () => {
    const geral = regraDe("*");
    expect(geral?.allow).toBe("/");
    expect(geral?.disallow).toBeUndefined();
  });

  it.each([
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-SearchBot",
    "Claude-User",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
    "Applebot-Extended",
  ])("declara %s explicitamente como liberado", (bot) => {
    const r = regraDe(bot);
    expect(r, bot).toBeDefined();
    expect(r?.allow).toBe("/");
    expect(r?.disallow).toBeUndefined();
  });

  it("bloqueia só o CCBot (corpus de treino aberto, sem citação)", () => {
    const r = regraDe("CCBot");
    expect(r?.disallow).toBe("/");
    expect(r?.allow).toBeUndefined();
  });

  it("aponta para o sitemap do site", () => {
    expect(robots().sitemap).toBe(`${SITE_URL}/sitemap.xml`);
  });
});
