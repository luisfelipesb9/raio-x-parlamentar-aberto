import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const API = "http://localhost:8000";

/** Campo de busca por nome (início: "Buscar deputado por nome"; seletores: "Nome do deputado"). */
export const CAMPO_BUSCA = /nome.*deputado|deputado.*nome/i;

/** Alerta de erro da página (ignora o anunciador de rotas do Next, que também tem role=alert). */
export function alertaDaPagina(page: Page) {
  return page.locator('[role="alert"]:not(#__next-route-announcer__)');
}

export interface DeputadoAlvo {
  id: string;
  nome: string;
}

/** Acha, pela API real, um deputado com pelo menos um alerta (não fixa ids: o banco muda a cada ingest). */
export async function deputadoComAlerta(request: APIRequestContext): Promise<DeputadoAlvo> {
  for (let page = 1; page <= 7; page++) {
    const r = await request.get(`${API}/deputados`, { params: { page, page_size: 100 } });
    expect(r.ok()).toBeTruthy();
    const corpo = (await r.json()) as { items: { id: string; nome: string }[] };
    for (const d of corpo.items) {
      const p = await request.get(`${API}/deputados/${d.id}`);
      const perfil = (await p.json()) as { n_findings: number };
      if (perfil.n_findings > 0) return { id: d.id, nome: d.nome };
    }
  }
  throw new Error("Nenhum deputado com alerta no banco usado pelo e2e (rode `make infer`).");
}

/** Acha um deputado sem nenhum alerta (para testar o estado vazio da ficha). */
export async function deputadoSemAlerta(request: APIRequestContext): Promise<DeputadoAlvo> {
  const r = await request.get(`${API}/deputados`, { params: { page_size: 100 } });
  const corpo = (await r.json()) as { items: { id: string; nome: string }[] };
  for (const d of corpo.items) {
    const perfil = (await (await request.get(`${API}/deputados/${d.id}`)).json()) as { n_findings: number };
    if (perfil.n_findings === 0) return { id: d.id, nome: d.nome };
  }
  throw new Error("Nenhum deputado sem alerta no banco do e2e.");
}

/** Falha se a página rola na horizontal (largura do conteúdo > largura da janela). */
export async function semScrollHorizontal(page: Page): Promise<void> {
  const { scroll, client } = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
  }));
  expect(scroll, `scrollWidth ${scroll} > clientWidth ${client}`).toBeLessThanOrEqual(client);
}
