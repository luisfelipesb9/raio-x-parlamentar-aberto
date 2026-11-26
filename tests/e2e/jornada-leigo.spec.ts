import { expect, test } from "@playwright/test";
import { deputadoComAlerta, deputadoSemAlerta, CAMPO_BUSCA, alertaDaPagina } from "./helpers";

test.describe("busca -> ficha -> 'Como sabemos disso?'", () => {
  test("encontra o deputado pelo nome, abre a ficha e vê a trilha da explicação", async ({ page, request }) => {
    const alvo = await deputadoComAlerta(request);

    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await page.getByRole("searchbox", { name: CAMPO_BUSCA }).fill(alvo.nome);
    const cartao = page.getByRole("link", { name: new RegExp(alvo.nome, "i") }).first();
    await expect(cartao).toBeVisible();
    await cartao.click();

    await expect(page).toHaveURL(new RegExp(`/deputado/${alvo.id}`));
    await expect(page.getByRole("heading", { level: 1, name: alvo.nome })).toBeVisible();

    // aviso permanente de que não é acusação
    await expect(page.getByText(/isto não é acusação/i).first()).toBeVisible();

    // seções da ficha, em linguagem simples
    for (const titulo of ["Quem é", "Como vota", "Quanto gasta", "Para onde mandou dinheiro", "Quem financiou", "Alertas", "Dados e verificação"]) {
      await expect(page.getByRole("heading", { name: titulo, exact: true })).toBeVisible();
    }

    // cartão de alerta: selo de certeza em TEXTO e botão da trilha
    const botao = page.getByRole("button", { name: /como sabemos disso\?/i }).first();
    await expect(botao).toBeVisible();
    await expect(page.getByText(/certeza (alta|média)|apenas indício|inconclusivo/i).first()).toBeVisible();
    await expect(botao).toHaveAttribute("aria-expanded", "false");
    await botao.click();
    await expect(botao).toHaveAttribute("aria-expanded", "true");

    const trilha = page.getByRole("region", { name: /como sabemos disso/i }).first();
    await expect(trilha).toBeVisible();
    await expect(trilha.getByText(/passo a passo|como chegamos/i).first()).toBeVisible();
    await expect(trilha.getByText(/limitações/i).first()).toBeVisible();

    // "Verificar na fonte": link oficial, identificador e data de coleta de cada documento
    await page.getByRole("button", { name: /verificar na fonte/i }).first().click();
    const fonte = page.getByRole("region", { name: /verificar na fonte/i }).first();
    await expect(fonte.getByRole("link", { name: /abrir na fonte/i }).first()).toBeVisible();
    await expect(fonte.getByText(/identificador oficial/i).first()).toBeVisible();
    await expect(fonte.getByText(/coletado em \d{2}\/\d{2}\/\d{4}/i).first()).toBeVisible();
  });

  test("ficha mostra 'Dados e verificação': janela de votos, números por regra e fontes", async ({ page, request }) => {
    const { id } = await deputadoComAlerta(request);
    await page.goto(`/deputado/${id}`);
    const secao = page.getByRole("region", { name: "Dados e verificação" });
    await expect(secao.getByText(/janela de votação/i).first()).toBeVisible();
    await expect(secao.getByText(/votos? válidos?/i).first()).toBeVisible();
    await expect(secao.getByRole("heading", { name: /de onde vêm os dados/i })).toBeVisible();
    await expect(secao.getByRole("link", { name: /ver todas as fontes/i })).toBeVisible();
  });

  test("busca sem resultado mostra estado vazio amigável, não tela quebrada", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("searchbox", { name: CAMPO_BUSCA }).fill("zzzzzzzzqx");
    await expect(page.getByText(/nenhum deputado encontrado/i)).toBeVisible();
  });

  test("ficha de deputado inexistente mostra erro claro com saída", async ({ page }) => {
    await page.goto("/deputado/id-que-nao-existe");
    await expect(alertaDaPagina(page)).toContainText(/não encontr/i);
    await expect(page.getByRole("link", { name: /voltar à busca/i })).toBeVisible();
  });

  test("deputado sem alertas explica que 'sem alerta' não é atestado de nada", async ({ page, request }) => {
    const semAlerta = await deputadoSemAlerta(request);
    await page.goto(`/deputado/${semAlerta.id}`);
    await expect(page.getByRole("heading", { level: 1, name: semAlerta.nome })).toBeVisible();
    await expect(page.getByText(/ausência de alerta não/i).first()).toBeVisible();
  });
});

test("glossário: termo da ficha mostra tooltip com a definição", async ({ page, request }) => {
  const { id } = await deputadoComAlerta(request);
  await page.goto(`/deputado/${id}`);
  const termo = page.getByRole("button", { name: /votação nominal/i }).first();
  await termo.focus();
  await expect(page.getByRole("tooltip")).toContainText(/voto de cada deputado/i);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("tooltip")).toHaveCount(0);

  await page.goto("/glossario");
  await expect(page.getByRole("heading", { level: 1, name: /glossário/i })).toBeVisible();
  await expect(page.getByText(/emenda pix/i).first()).toBeVisible();
});
