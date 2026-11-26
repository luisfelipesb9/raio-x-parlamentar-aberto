import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { gerarConteudo, parseYaml, serializa } from "../../scripts/gen-conteudo.mjs";
import type { Conteudo } from "./tipos";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const FIX = { dirConteudo: path.join(aqui, "__fixtures__/conteudo"), dirRegras: path.join(aqui, "__fixtures__/regras") };
const REAL = {
  dirConteudo: path.join(aqui, "../../../docs/conteudo"),
  dirRegras: path.join(aqui, "../../../knowledge/rules"),
};

describe("parseYaml (subconjunto usado nas regras)", () => {
  it("lê escalares tipados, mapas e listas, ignorando comentários", () => {
    const y = parseYaml(`
id: R01   # comentário
cf: 0.95
ativo: true
nada: null
texto: "com # dentro, e: dois pontos"
simples: Basômetro (Estadão)
mapa: {a: 1, b: "x, y", c: [1, dois]}
lista:
  - "um"
  - {se: "n < 3", fator: 0.7}
vazia: []
`) as Record<string, unknown>;
    expect(y).toEqual({
      id: "R01",
      cf: 0.95,
      ativo: true,
      nada: null,
      texto: "com # dentro, e: dois pontos",
      simples: "Basômetro (Estadão)",
      mapa: { a: 1, b: "x, y", c: [1, "dois"] },
      lista: ["um", { se: "n < 3", fator: 0.7 }],
      vazia: [],
    });
  });

  it("lê mapa aninhado em bloco", () => {
    expect(parseYaml("parametros:\n  peso: 0.25\n  max: 32\nfim: 1\n")).toEqual({ parametros: { peso: 0.25, max: 32 }, fim: 1 });
  });

  it("recusa construção que não suporta, em vez de interpretar errado", () => {
    expect(() => parseYaml("texto: |\n  bloco\n")).toThrow(/não suportad/i);
  });
});

describe("gerarConteudo com fixtures", () => {
  const c: Conteudo = gerarConteudo(FIX);

  it("traz só as páginas que existem, com o frontmatter e o corpo", () => {
    expect(Object.keys(c.paginas)).toEqual(["faq", "metodo"]);
    expect(c.paginas.metodo).toEqual({
      arquivo: "metodo",
      slug: "metodo",
      titulo: "Como o sistema chega às conclusões",
      descricao: "Texto de teste do método.",
      resposta: "O sistema aplica regras abertas aos fatos públicos e mostra o nível de certeza de cada conclusão.",
      atualizado: "2026-11-20",
      corpo: expect.stringMatching(/^## Passo a passo\n\nO sistema lê \*\*fatos\*\*[\s\S]*fonte externa\]\(https:\/\/dadosabertos\.camara\.leg\.br\/\)\.$/),
    });
  });

  it("lista as regras do YAML em ordem natural (R06b depois de R05, antes de R08), ignorando _schema", () => {
    expect(c.regras.map((r) => r.id)).toEqual(["R01", "R05", "R06b", "R08", "R09"]);
  });

  it("copia os parâmetros reais da regra (nome, limiar, cf, penalidades, limitações)", () => {
    const r = c.regras[0]!;
    expect(r).toMatchObject({
      id: "R01",
      nome: "Taxa de governismo",
      tipo: "inferencia",
      categoria: "votacao",
      predicado: "taxa_governismo",
      parametros: { minimo_votacoes: 10, limiar: 0.7 },
      se: "taxa_governismo >= 0.7",
      cf: 0.95,
      penalidades: [{ se: "n_votacoes < 30", fator: 0.7, motivo: "Poucas votações nominais, no período" }],
      limitacoes: ["Considera só votações nominais.", "Abstenção e obstrução ficam fora da conta."],
      fonteMetodologica: "Basômetro (Estadão)",
      composta: false,
    });
  });

  it("anexa o texto de regras/R01.md à regra R01 e deixa null nas demais", () => {
    expect(c.regras[0]!.texto).toMatchObject({ arquivo: "R01", regra: "R01", titulo: "R01: taxa de governismo", atualizado: "2026-11-22" });
    expect(c.regras.slice(1).every((r) => r.texto === null)).toBe(true);
  });

  it("distingue guardrail (sem cf) e regra composta (sem predicado, com requer)", () => {
    const [, r05, r06b, r08, r09] = c.regras;
    expect(r05!.parametros).toEqual({ peso_coautor: 0.25, max_iniciativa: 32 });
    expect(r06b!.parametros).toEqual({ modo: "indicio" });
    expect(r08).toMatchObject({ tipo: "guardrail", prioridade: 2, penalidades: [], composta: false });
    expect(r08!.cf).toBeUndefined();
    expect(r09).toMatchObject({ composta: true, requer: ["risco_integridade"], parametros: {} });
  });

  it("é determinístico: duas execuções dão exatamente o mesmo texto, sem data de geração", () => {
    const a = serializa(gerarConteudo(FIX));
    const b = serializa(gerarConteudo(FIX));
    expect(a).toBe(b);
    expect(a.endsWith("\n")).toBe(true);
    expect(a).not.toMatch(/gerado_em|generatedAt|timestamp/i);
  });
});

describe("gerarConteudo com arquivos ausentes", () => {
  it("sem pasta de conteúdo: nenhuma página, e as regras vêm só do YAML", () => {
    const c = gerarConteudo({ dirConteudo: path.join(aqui, "__fixtures__/nao-existe"), dirRegras: FIX.dirRegras });
    expect(c.paginas).toEqual({});
    expect(c.regras).toHaveLength(5);
    expect(c.regras.every((r) => r.texto === null)).toBe(true);
  });

  it("sem pasta de regras: lista de regras vazia, sem quebrar", () => {
    const c = gerarConteudo({ dirConteudo: FIX.dirConteudo, dirRegras: path.join(aqui, "__fixtures__/nao-existe") });
    expect(c.regras).toEqual([]);
  });

  it("frontmatter sem campo obrigatório é erro claro (não gera página pela metade)", () => {
    expect(() => gerarConteudo({ ...FIX, dirConteudo: path.join(aqui, "__fixtures__/invalido") })).toThrow(/resposta/);
  });
});

describe("conteudo.json committed", () => {
  it("é exatamente a saída do gerador sobre docs/conteudo e knowledge/rules (rode `pnpm gen:conteudo` se falhar)", () => {
    const committed = readFileSync(path.join(aqui, "gerado/conteudo.json"), "utf-8");
    expect(committed).toBe(serializa(gerarConteudo(REAL)));
  });
});
