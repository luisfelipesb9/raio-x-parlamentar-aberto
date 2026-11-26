import { expect, test } from "@playwright/test";
import { deputadoComAlerta, CAMPO_BUSCA, alertaDaPagina } from "./helpers";

test("perguntar: mostra CF, nível em texto e a trilha de prova como árvore legível", async ({ page, request }) => {
  const alvo = await deputadoComAlerta(request);
  await page.goto(`/perguntar?deputado=${alvo.id}`);
  await page.getByLabel(/o que você quer saber/i).selectOption("merece_atencao_fiscalizacao");
  await page.getByRole("button", { name: /perguntar/i }).click();

  const resultado = page.getByRole("region", { name: /resposta do sistema/i });
  await expect(resultado).toBeVisible();
  await expect(resultado.getByText(/fator de certeza/i).first()).toBeVisible();
  await expect(resultado.getByText(/certeza (alta|média)|apenas indício|inconclusivo/i).first()).toBeVisible();
  const arvore = resultado.getByRole("tree", { name: /trilha da prova/i });
  await expect(arvore).toBeVisible();
  await expect(arvore.getByRole("treeitem").first()).toBeVisible();
  await expect(resultado.getByText(/isto não é acusação/i)).toBeVisible();
});

test("perguntar: a resposta recebe foco e a trilha da prova responde ao teclado", async ({ page, request }) => {
  const alvo = await deputadoComAlerta(request);
  await page.goto(`/perguntar?deputado=${alvo.id}`);
  await page.getByLabel(/o que você quer saber/i).selectOption("merece_atencao_fiscalizacao");
  await page.getByRole("button", { name: /perguntar/i }).click();

  const resultado = page.getByRole("region", { name: /resposta do sistema/i });
  await expect(resultado).toBeFocused();
  await expect(page.getByRole("status").filter({ hasText: /resposta pronta/i })).toBeAttached();

  const itens = resultado.getByRole("tree", { name: /trilha da prova/i }).getByRole("treeitem");
  const primeiro = itens.first();
  await expect(primeiro).toHaveAttribute("tabindex", "0");
  const temFilhos = (await primeiro.getAttribute("aria-expanded")) !== null;
  test.skip(!temFilhos, "a trilha desta consulta não tem passos aninhados");
  await primeiro.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(primeiro).toHaveAttribute("aria-expanded", "false");
  await page.keyboard.press("ArrowRight");
  await expect(primeiro).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("ArrowDown");
  await expect(itens.nth(1)).toBeFocused();
  await page.keyboard.press("Home");
  await expect(primeiro).toBeFocused();
});

test("perguntar sem deputado pede para escolher um", async ({ page }) => {
  await page.goto("/perguntar");
  await expect(page.getByRole("searchbox", { name: CAMPO_BUSCA })).toBeVisible();
});

test("comparar dois deputados mostra afinidade de votos e lado a lado", async ({ page, request }) => {
  const r = await request.get("http://localhost:8000/deputados?page_size=2");
  const { items } = (await r.json()) as { items: { id: string; nome: string }[] };
  const [a, b] = items as [{ id: string; nome: string }, { id: string; nome: string }];
  await page.goto(`/comparar?a=${a.id}&b=${b.id}`);
  await expect(page.getByRole("heading", { level: 1, name: /comparar/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: a.nome, exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: b.nome, exact: true })).toBeVisible();
  await expect(page.getByText(/votaram igual|afinidade/i).first()).toBeVisible();
});

test("comparar o mesmo deputado com ele mesmo mostra erro claro", async ({ page, request }) => {
  const { id } = await deputadoComAlerta(request);
  await page.goto(`/comparar?a=${id}&b=${id}`);
  await expect(alertaDaPagina(page)).toContainText(/dois deputados diferentes/i);
});
