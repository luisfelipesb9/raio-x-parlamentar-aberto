import { describe, expect, it } from "vitest";
import { idValido } from "./id-deputado";

describe("idValido", () => {
  it.each(["9900001", "abc", "id-que-nao-existe", "A_b-9", "x".repeat(32)])("aceita %s", (id) => {
    expect(idValido(id)).toBe(true);
  });

  it.each([
    ["HTML na URL (/deputado/%3Cimg…)", '<img src=x onerror=alert(1)>'],
    ["subida de diretório (/deputado/..%2Fcobertura)", "../cobertura"],
    ["barra", "1/2"],
    ["query", "1?x=2"],
    ["espaço", "1 2"],
    ["vazio", ""],
    ["longo demais (33)", "x".repeat(33)],
    ["quebra de linha no fim", "123\n"],
  ])("rejeita %s", (_nome, id) => {
    expect(idValido(id)).toBe(false);
  });
});
