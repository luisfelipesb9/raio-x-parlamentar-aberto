import { expect, test } from "@playwright/test";
import { API, semScrollHorizontal } from "./helpers";

test.describe("/fontes: fontes e método", () => {
  test("mostra janela de votos e tabela de fontes vindas da API, o aviso e como conferir", async ({ page, request }) => {
    const cob = (await (await request.get(`${API}/cobertura`)).json()) as { fontes: { fonte: string }[]; janela_votos: { n_votacoes: number } };
    await page.goto("/fontes");
    await expect(page.getByRole("heading", { level: 1, name: /fontes e método/i })).toBeVisible();
    await expect(page.getByText(/isto não é acusação/i).first()).toBeVisible();
    await expect(page.getByText(/janela de votação/i).first()).toBeVisible();
    const tabela = page.getByRole("table", { name: /fontes oficiais usadas/i });
    await expect(tabela).toBeVisible();
    await expect(tabela.getByRole("row")).toHaveCount(cob.fontes.length + 1);
    await expect(page.getByRole("heading", { name: /por que o nível de certeza tem um teto/i })).toBeVisible();
    await expect(page.getByText("make verifica")).toBeVisible();
  });

  test("tem link no menu e no rodapé", async ({ page }) => {
    await page.goto("/glossario");
    await page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name: /fontes e método/i }).click();
    await expect(page).toHaveURL(/\/fontes$/);
    await expect(page.getByRole("contentinfo").getByRole("link", { name: /fontes e método/i })).toBeVisible();
  });

  test("em 375px não rola na horizontal", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/fontes");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await semScrollHorizontal(page);
  });
});
