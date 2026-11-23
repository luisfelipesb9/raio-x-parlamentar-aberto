import { expect, test } from "@playwright/test";
import { deputadoComAlerta, semScrollHorizontal, CAMPO_BUSCA } from "./helpers";

test.use({ viewport: { width: 375, height: 812 } });

test.describe("mobile 375px: nada rola na horizontal", () => {
  test("início, busca com filtros e glossário", async ({ page }) => {
    for (const rota of ["/", "/glossario"]) {
      await page.goto(rota);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await semScrollHorizontal(page);
    }
    await page.goto("/");
    await page.getByRole("searchbox", { name: CAMPO_BUSCA }).fill("ana");
    await expect(page.getByRole("link", { name: /ana/i }).first()).toBeVisible();
    await semScrollHorizontal(page);
  });

  test("ficha com trilha aberta, grafo, perguntar e comparar", async ({ page, request }) => {
    const { id } = await deputadoComAlerta(request);

    await page.goto(`/deputado/${id}`);
    await page.getByRole("button", { name: /como sabemos disso\?/i }).first().click();
    await expect(page.getByRole("region", { name: /como sabemos disso/i }).first()).toBeVisible();
    await semScrollHorizontal(page);

    await page.goto(`/grafo?centro=deputado:${id}`);
    await expect(page.getByRole("img", { name: /mapa de relações/i })).toBeVisible();
    await page.getByRole("button", { name: /ver os nós como lista/i }).click();
    await semScrollHorizontal(page);

    await page.goto(`/perguntar?deputado=${id}`);
    await page.getByRole("button", { name: /perguntar/i }).click();
    await expect(page.getByRole("region", { name: /resposta do sistema/i })).toBeVisible();
    await semScrollHorizontal(page);

    const lista = await request.get("http://localhost:8000/deputados?page_size=2");
    const { items } = (await lista.json()) as { items: { id: string }[] };
    await page.goto(`/comparar?a=${items[0]!.id}&b=${items[1]!.id}`);
    await expect(page.getByRole("heading", { level: 1, name: /comparar/i })).toBeVisible();
    await semScrollHorizontal(page);
  });
});
