import { expect, test } from "@playwright/test";
import { deputadoComAlerta, CAMPO_BUSCA, alertaDaPagina } from "./helpers";

test.describe("grafo", () => {
  test("abre o grafo do deputado; clicar num nó mostra atributos e backlinks", async ({ page, request }, info) => {
    test.skip(info.project.name.startsWith("mobile"), "clique por coordenadas só no desktop; mobile usa a lista");
    const alvo = await deputadoComAlerta(request);
    await page.goto(`/grafo?centro=deputado:${alvo.id}`);

    const canvas = page.getByRole("img", { name: /mapa de relações/i });
    await expect(canvas).toBeVisible();
    await expect(page.getByRole("list", { name: /legenda/i })).toBeVisible();

    // espera o Cytoscape montar e clica de verdade no nó central
    await page.waitForFunction(() => Boolean((window as unknown as { __raioXCy?: unknown }).__raioXCy));
    const pos = await page.evaluate(() => {
      const cy = (window as unknown as { __raioXCy: { getElementById(id: string): { renderedPosition(): { x: number; y: number } } } }).__raioXCy;
      return cy.getElementById(`deputado:${new URL(location.href).searchParams.get("centro")?.split(":")[1]}`).renderedPosition();
    });
    // a página tem animação de entrada: espera a caixa do canvas parar de se mover antes de clicar por coordenada
    let anterior = "";
    await expect
      .poll(async () => {
        const atual = JSON.stringify(await canvas.boundingBox());
        const estavel = atual === anterior;
        anterior = atual;
        return estavel;
      })
      .toBe(true);
    const caixa = (await canvas.boundingBox())!;
    await page.mouse.click(caixa.x + pos.x, caixa.y + pos.y);

    const painel = page.getByRole("complementary", { name: /detalhes do nó/i });
    await expect(painel).toBeVisible();
    await expect(painel.getByRole("heading", { name: alvo.nome })).toBeVisible();
    await expect(painel.getByRole("heading", { name: /backlinks|quem aponta para/i })).toBeVisible();
    await expect(painel.getByRole("list", { name: /backlinks/i }).getByRole("listitem").first()).toBeVisible();
  });

  test("lista alternativa dos nós é navegável por teclado e seleciona o nó", async ({ page, request }) => {
    const alvo = await deputadoComAlerta(request);
    await page.goto(`/grafo?centro=deputado:${alvo.id}`);
    await page.getByRole("button", { name: /ver os nós como lista/i }).click();
    const lista = page.getByRole("list", { name: /nós do grafo/i });
    await expect(lista).toBeVisible();
    const primeiro = lista.getByRole("button").first();
    await primeiro.focus();
    await page.keyboard.press("Enter");
    const painel = page.getByRole("complementary", { name: /detalhes do nó/i });
    await expect(painel).toBeVisible();
    await expect(painel.getByRole("heading", { level: 2 })).toBeInViewport();

    // volta até a lista e escolhe o MESMO nó: o painel tem de voltar para a vista
    await primeiro.scrollIntoViewIfNeeded();
    await primeiro.click();
    await expect(painel.getByRole("heading", { level: 2 })).toBeInViewport();
  });

  test("profundidade 2 e filtro de relação refazem a consulta e atualizam a contagem", async ({ page, request }) => {
    const alvo = await deputadoComAlerta(request);
    await page.goto(`/grafo?centro=deputado:${alvo.id}`);
    const resumo = page.getByTestId("resumo-grafo");
    await expect(resumo).toContainText(/1 salto/);
    const antes = await resumo.innerText();

    await page.getByRole("radio", { name: /2 saltos/i }).check();
    await expect(page).toHaveURL(/profundidade=2/);
    await expect(resumo).toContainText(/2 saltos/);

    await page.getByRole("checkbox", { name: /votos parecidos/i }).uncheck();
    await expect(page).toHaveURL(/relacoes=/);
    await expect(resumo).not.toHaveText(antes);
  });

  test("grafo truncado (300 nós) avisa que a visão é parcial", async ({ page }) => {
    // 107970 (base de amostra) passa de 300 nós com 2 saltos
    await page.goto("/grafo?centro=deputado:107970&profundidade=2");
    await expect(page.getByText(/mapa cortado/i)).toBeVisible();
    await expect(page.getByTestId("resumo-grafo")).toContainText(/300 nós/);
  });

  test("grafo de nó inexistente mostra erro com saída", async ({ page }) => {
    await page.goto("/grafo?centro=deputado:0000000");
    await expect(alertaDaPagina(page)).toContainText(/não encontr/i);
  });

  test("sem centro, convida a escolher um deputado", async ({ page }) => {
    await page.goto("/grafo");
    await expect(page.getByRole("searchbox", { name: CAMPO_BUSCA })).toBeVisible();
  });
});
