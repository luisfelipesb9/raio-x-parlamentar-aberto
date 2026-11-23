import { expect, test } from "@playwright/test";
import { API, deputadoComAlerta, semScrollHorizontal } from "./helpers";

const emAnimacao = () => document.getAnimations().filter((a) => a.playState === "running").length;

test.describe("identidade visual: efeitos e prefers-reduced-motion", () => {
  test("com movimento normal, a varredura do hero está rodando", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect.poll(() => page.evaluate(emAnimacao)).toBeGreaterThan(0);
  });

  test("prefers-reduced-motion desliga TODAS as animações e mostra o valor final dos números", async ({ page, request }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    const lista = page.getByRole("list", { name: /o sistema em números/i });
    await expect(lista).toBeVisible();
    const { total } = (await (await request.get(`${API}/deputados?page_size=1`)).json()) as { total: number };
    await expect(lista).toContainText(total.toLocaleString("pt-BR"));
    expect(await page.evaluate(emAnimacao)).toBe(0);
    expect(await page.locator(".cursor-halo").evaluate((el) => getComputedStyle(el).display)).toBe("none");

    // ficha: nenhuma seção fica escondida esperando o scroll
    const { id } = await deputadoComAlerta(request);
    await page.goto(`/deputado/${id}`);
    await expect(page.getByRole("heading", { name: "Alertas", exact: true })).toBeVisible();
    expect(await page.locator(".secao.revela").count()).toBe(0);
    expect(await page.evaluate(emAnimacao)).toBe(0);
  });

  test("ficha: seção abaixo da dobra nasce escondida (revela) e só aparece (visivel) ao rolar", async ({ page, request }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    const { id } = await deputadoComAlerta(request);
    await page.goto(`/deputado/${id}`);
    const alertas = page.locator("section#alertas");
    // antes de rolar: marcada para revelar e ainda invisível
    await expect(alertas).toHaveClass(/\brevela\b/);
    await expect(alertas).not.toHaveClass(/\bvisivel\b/);
    await expect.poll(() => alertas.evaluate((el) => getComputedStyle(el).opacity)).toBe("0");
    // depois de rolar: revelada
    await alertas.scrollIntoViewIfNeeded();
    await expect(alertas).toHaveClass(/\bvisivel\b/);
    await expect.poll(() => alertas.evaluate((el) => getComputedStyle(el).opacity)).toBe("1");
  });

  test("LCP da home abaixo de 2,5 s", async ({ page }) => {
    await page.addInitScript(() => {
      (window as unknown as { __lcp: number }).__lcp = 0;
      new PerformanceObserver((lista) => {
        const e = lista.getEntries().at(-1);
        if (e) (window as unknown as { __lcp: number }).__lcp = e.startTime;
      }).observe({ type: "largest-contentful-paint", buffered: true });
    });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForLoadState("load");
    const lerLcp = () => page.evaluate(() => (window as unknown as { __lcp: number }).__lcp);
    await expect.poll(lerLcp).toBeGreaterThan(0);
    expect(await lerLcp()).toBeLessThan(2500);
  });

  test("favicon e imagem OG existem", async ({ request }) => {
    const icon = await request.get("/icon.svg");
    expect(icon.ok()).toBeTruthy();
    expect(icon.headers()["content-type"]).toContain("svg");
    const og = await request.get("/opengraph-image");
    expect(og.ok()).toBeTruthy();
    expect(og.headers()["content-type"]).toContain("image/png");
  });

  test("tema claro e escuro: home sem scroll horizontal", async ({ page }) => {
    for (const esquema of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: esquema });
      await page.goto("/");
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await semScrollHorizontal(page);
    }
  });
});
