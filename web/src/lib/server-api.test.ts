import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";
import { servidorGet, servidorGetOuNull, servidorTodosDeputados } from "./server-api";

afterEach(() => vi.unstubAllGlobals());

const json = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), { status, headers: { "content-type": "application/json" } });

describe("servidorGet", () => {
  it("devolve o JSON e pede revalidação ao Next", async () => {
    const f = vi.fn().mockResolvedValue(json({ ok: 1 }));
    vi.stubGlobal("fetch", f);
    await expect(servidorGet("/saude")).resolves.toEqual({ ok: 1 });
    const [url, init] = f.mock.calls[0] as [string, { next: unknown }];
    expect(url).toBe("http://localhost:8000/saude");
    expect(init.next).toEqual({ revalidate: 3600 });
  });

  it("converte 404 em ApiError nao_encontrado e servidorGetOuNull devolve null", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ detail: "não achei" }, 404)));
    await expect(servidorGet("/deputados/x")).rejects.toMatchObject({ tipo: "nao_encontrado", status: 404 });
    await expect(servidorGetOuNull("/deputados/x")).resolves.toBeNull();
  });

  it("servidorGetOuNull propaga erros que não são 404", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({}, 503)));
    await expect(servidorGetOuNull("/deputados/x")).rejects.toBeInstanceOf(ApiError);
  });

  it("falha de rede vira ApiError rede", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("boom")));
    await expect(servidorGet("/saude")).rejects.toMatchObject({ tipo: "rede" });
  });
});

describe("servidorTodosDeputados", () => {
  it("percorre as páginas até o total", async () => {
    const f = vi
      .fn()
      .mockResolvedValueOnce(json({ items: [{ id: "1" }, { id: "2" }], total: 3 }))
      .mockResolvedValueOnce(json({ items: [{ id: "3" }], total: 3 }));
    vi.stubGlobal("fetch", f);
    const todos = await servidorTodosDeputados<{ id: string }>();
    expect(todos.map((d) => d.id)).toEqual(["1", "2", "3"]);
    expect(f).toHaveBeenCalledTimes(2);
  });
});
