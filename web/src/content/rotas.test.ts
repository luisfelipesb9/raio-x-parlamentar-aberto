import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { gerarConteudo } from "../../scripts/gen-conteudo.mjs";
import { GLOSSARIO } from "@/lib/glossario";
import { linksSaibaMais, rotasDeConteudo } from "./rotas";
import type { Conteudo } from "./tipos";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const comTextos: Conteudo = gerarConteudo({ dirConteudo: path.join(aqui, "__fixtures__/conteudo"), dirRegras: path.join(aqui, "__fixtures__/regras") });
const semTextos: Conteudo = { paginas: {}, regras: comTextos.regras.map((r) => ({ ...r, texto: null })) };
const vazio: Conteudo = { paginas: {}, regras: [] };

describe("rotasDeConteudo", () => {
  it("lista só as páginas que existem, mais regras e termos do glossário", () => {
    const c = rotasDeConteudo(comTextos, GLOSSARIO).map((r) => r.caminho);
    expect(c).toContain("/metodo");
    expect(c).toContain("/faq");
    expect(c).not.toContain("/dados");
    expect(c).not.toContain("/para-estudantes");
    expect(c).toContain("/regras");
    expect(c).toEqual(expect.arrayContaining(["/regras/R01", "/regras/R06b", "/regras/R09"]));
    expect(c).toContain("/glossario/ceap");
    expect(c.filter((x) => x.startsWith("/glossario/"))).toHaveLength(GLOSSARIO.length);
  });

  it("usa a data 'atualizado' do texto quando existe, e nada quando não existe", () => {
    const por = (cam: string) => rotasDeConteudo(comTextos, GLOSSARIO).find((r) => r.caminho === cam);
    expect(por("/metodo")?.atualizado).toBe("2026-11-20");
    expect(por("/regras/R01")?.atualizado).toBe("2026-11-22");
    expect(por("/regras/R05")?.atualizado).toBeUndefined();
    expect(por("/glossario/ceap")?.atualizado).toBeUndefined();
  });

  it("sem nenhum texto, as regras (do YAML) e o glossário continuam existindo", () => {
    const c = rotasDeConteudo(semTextos, GLOSSARIO).map((r) => r.caminho);
    expect(c).toContain("/regras/R01");
    expect(c).not.toContain("/metodo");
  });

  it("sem regras, não lista o índice /regras", () => {
    expect(rotasDeConteudo(vazio, GLOSSARIO).map((r) => r.caminho)).not.toContain("/regras");
  });
});

describe("linksSaibaMais (rodapé)", () => {
  it("mostra só o que existe, na ordem Método, Regras, FAQ, Glossário, Dados e API, Para estudantes", () => {
    expect(linksSaibaMais(comTextos).map((l) => l.href)).toEqual(["/metodo", "/regras", "/faq", "/glossario"]);
    expect(linksSaibaMais(vazio).map((l) => l.href)).toEqual(["/glossario"]);
  });
});
