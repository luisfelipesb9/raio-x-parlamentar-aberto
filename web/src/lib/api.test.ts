import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiGet, apiUrl } from "./api";

afterEach(() => vi.unstubAllGlobals());

function resposta(corpo: unknown, init: { status?: number; tipo?: string } = {}) {
  return new Response(JSON.stringify(corpo), {
    status: init.status ?? 200,
    headers: { "content-type": init.tipo ?? "application/json" },
  });
}

describe("apiUrl", () => {
  it("usa localhost:8000 por padrão e ignora parâmetros vazios", () => {
    const url = apiUrl("/deputados", { q: "ana", uf: "", partido: undefined, page: 2 });
    expect(url).toBe("http://localhost:8000/deputados?q=ana&page=2");
  });

  it("codifica ids com dois-pontos", () => {
    expect(apiUrl("/grafo/backlinks/deputado:1")).toBe("http://localhost:8000/grafo/backlinks/deputado:1");
  });
});

describe("apiGet", () => {
  it("devolve o JSON em caso de sucesso", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(resposta({ total: 1 })));
    await expect(apiGet<{ total: number }>("/deputados")).resolves.toEqual({ total: 1 });
  });

  it("converte problem+json (RFC 7807) em ApiError com detalhe legível", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        resposta(
          { type: "about:blank", title: "Not Found", status: 404, detail: "Deputado 1 não encontrado." },
          { status: 404, tipo: "application/problem+json" },
        ),
      ),
    );
    const erro = await apiGet("/deputados/1").catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ApiError);
    const e = erro as ApiError;
    expect(e.status).toBe(404);
    expect(e.tipo).toBe("nao_encontrado");
    expect(e.detalhe).toBe("Deputado 1 não encontrado.");
  });

  it("classifica 503 como banco indisponível", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        resposta({ title: "Service Unavailable", status: 503, detail: "banco ausente" }, { status: 503, tipo: "application/problem+json" }),
      ),
    );
    const e = (await apiGet("/deputados").catch((x: unknown) => x)) as ApiError;
    expect(e.tipo).toBe("indisponivel");
  });

  it("falha de rede vira ApiError tipo 'rede' (sem vazar mensagem técnica)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const e = (await apiGet("/deputados").catch((x: unknown) => x)) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.tipo).toBe("rede");
    expect(e.mensagemParaLeigo).not.toContain("Failed to fetch");
  });

  it("resposta não-JSON com status de erro ainda vira ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>", { status: 502 })));
    const e = (await apiGet("/deputados").catch((x: unknown) => x)) as ApiError;
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(502);
  });

  it("propaga abort sem embrulhar", async () => {
    const abort = new DOMException("abortado", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(apiGet("/deputados")).rejects.toBe(abort);
  });
});
