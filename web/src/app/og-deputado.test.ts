import { beforeEach, describe, expect, it, vi } from "vitest";

const { buscar, capturado } = vi.hoisted(() => ({
  buscar: vi.fn(),
  capturado: { elemento: null as unknown, opcoes: null as { headers?: Record<string, string> } | null },
}));

vi.mock("@/lib/server-api", () => ({ servidorGetOuNull: buscar }));
vi.mock("next/og", () => ({
  ImageResponse: class {
    constructor(elemento: unknown, opcoes: { headers?: Record<string, string> }) {
      capturado.elemento = elemento;
      capturado.opcoes = opcoes;
    }
  },
}));

import Imagem from "./deputado/[id]/opengraph-image";

/** Todo o texto do elemento JSX, para checar o que a imagem diz. */
function textos(no: unknown): string {
  if (typeof no === "string" || typeof no === "number") return String(no);
  if (Array.isArray(no)) return no.map(textos).join(" ");
  if (no && typeof no === "object" && "props" in no) return textos((no as { props: { children?: unknown } }).props.children);
  return "";
}

const chamar = (id: string) => Imagem({ params: Promise.resolve({ id }) });

describe("imagem OG do deputado", () => {
  beforeEach(() => {
    buscar.mockReset();
    capturado.elemento = null;
  });

  it.each(["../x", "a b", "a<b", "x".repeat(40), "1/2"])("id inválido (%s) vira imagem genérica sem consultar a API", async (id) => {
    await chamar(id);
    expect(buscar).not.toHaveBeenCalled();
    expect(textos(capturado.elemento)).toContain("Raio-X Parlamentar");
  });

  it("id válido consulta a API e mostra nome, partido-UF e o texto padrão", async () => {
    buscar.mockResolvedValue({ id: "9900001", nome: "Alice Fictícia", partido: "PXY", uf: "MG", foto: null });
    await chamar("9900001");
    expect(buscar).toHaveBeenCalledWith("/deputados/9900001");
    const t = textos(capturado.elemento);
    expect(t).toContain("Alice Fictícia");
    expect(t).toContain("PXY - MG");
    expect(t).toContain("Dados públicos explicados, com fonte e nível de certeza");
  });

  it("API fora do ar não quebra: imagem genérica", async () => {
    buscar.mockRejectedValue(new Error("rede"));
    await chamar("9900001");
    expect(textos(capturado.elemento)).toContain("Raio-X Parlamentar");
  });

  it("deputado inexistente (null) vira imagem genérica", async () => {
    buscar.mockResolvedValue(null);
    await chamar("9900001");
    expect(textos(capturado.elemento)).not.toContain("FICHA DO DEPUTADO");
  });

  it("falha da API tem cache curto; resposta normal tem cache de 1 hora", async () => {
    buscar.mockRejectedValue(new Error("rede"));
    await chamar("9900001");
    expect(capturado.opcoes?.headers?.["Cache-Control"]).toMatch(/max-age=60\b/);
    buscar.mockResolvedValue({ id: "1", nome: "A", partido: null, uf: null, foto: null });
    await chamar("1");
    expect(capturado.opcoes?.headers?.["Cache-Control"]).toMatch(/max-age=3600\b/);
  });
});
