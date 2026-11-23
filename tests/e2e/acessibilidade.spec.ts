import { expect, test } from "@playwright/test";
import { deputadoComAlerta } from "./helpers";

const emAnimacao = () => document.getAnimations().filter((a) => a.playState === "running").length;

test.describe("WCAG 2.2.2: pausar animações", () => {
  test("botão no cabeçalho pausa todos os loops, persiste e pode ser desfeito", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto("/");
    await expect.poll(() => page.evaluate(emAnimacao)).toBeGreaterThan(0);

    const botao = page.getByRole("button", { name: /pausar animações/i });
    await expect(botao).toHaveAttribute("aria-pressed", "false");
    await botao.click();
    await expect(page.getByRole("button", { name: /retomar animações/i })).toHaveAttribute("aria-pressed", "true");
    await expect.poll(() => page.evaluate(emAnimacao)).toBe(0);

    // persiste entre visitas (localStorage) e vale já na primeira pintura
    await page.reload();
    await expect(page.getByRole("button", { name: /retomar animações/i })).toBeVisible();
    expect(await page.evaluate(emAnimacao)).toBe(0);

    // e volta ao normal
    await page.getByRole("button", { name: /retomar animações/i }).click();
    await expect.poll(() => page.evaluate(emAnimacao)).toBeGreaterThan(0);
  });

  test("com localStorage bloqueado a página continua funcionando", async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(window, "localStorage", {
        get() {
          throw new DOMException("bloqueado", "SecurityError");
        },
      });
    });
    await page.goto("/");
    await page.getByRole("button", { name: /pausar animações/i }).click();
    await expect(page.getByRole("button", { name: /retomar animações/i })).toBeVisible();
  });
});

test.describe("termo do glossário no toque", () => {
  test("um toque abre o tooltip e fica aberto; tocar fora fecha", async ({ page, request, isMobile: _m }, info) => {
    test.skip(!info.project.name.startsWith("mobile"), "gesto de toque só no projeto mobile");
    const { id } = await deputadoComAlerta(request);
    await page.goto(`/deputado/${id}`);
    const termo = page.getByRole("button", { name: /votação nominal/i }).first();
    await termo.scrollIntoViewIfNeeded();
    await termo.tap();
    await expect(page.getByRole("tooltip")).toContainText(/voto de cada deputado/i);
    // continua aberto (sem fechar por focus + click emulados)
    await page.waitForFunction(() => document.querySelectorAll('[role="tooltip"]').length === 1);
    await expect(page.getByRole("tooltip")).toBeVisible();
    // tocar de novo no termo fecha
    await termo.tap();
    await expect(page.getByRole("tooltip")).toHaveCount(0);
    // reabre e fecha tocando fora
    await termo.tap();
    await expect(page.getByRole("tooltip")).toBeVisible();
    await page.getByRole("heading", { level: 1 }).tap();
    await expect(page.getByRole("tooltip")).toHaveCount(0);
  });
});
