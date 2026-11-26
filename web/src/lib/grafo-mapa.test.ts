import { describe, expect, it } from "vitest";
import type { GraphEdge, GraphNode, GrafoResposta, OcultoResumo } from "@/types/contracts";
import { TIPOS_NO } from "./grafo";
import {
  FAMILIAS,
  LIMIAR_HUB,
  MANTER_VISIVEIS,
  MIN_GRUPO,
  TAM_MAX,
  TAM_MIN,
  TAM_SEM_VALOR,
  agrupaFolhas,
  buscaNos,
  contagemVisivel,
  csvArestas,
  csvNos,
  elementosDoMapa,
  espessuraDaAresta,
  familiaDaRelacao,
  posicoesIniciais,
  resumoOcultos,
  tamanhoDoNo,
  tracoDaCerteza,
  valoresPorNo,
  type NoMapa,
} from "./grafo-mapa";

const no = (id: string, tipo: string, rotulo = id, atributos: Record<string, unknown> = {}): GraphNode => ({ id, tipo, rotulo, atributos });
const lig = (origem: string, destino: string, relacao: string, peso = 1, cf = 1): GraphEdge => ({ origem, destino, relacao, peso, cf, evidencia_ids: [] });

function grafoDe(nodes: GraphNode[], edges: GraphEdge[], centro = "deputado:1", extra: Partial<GrafoResposta> = {}): GrafoResposta {
  return { centro, profundidade: 1, truncado: false, total_nos: null, total_arestas: null, ocultos: [], nodes, edges, ...extra };
}

/** Deputado 1 com `n` empresas folha (R$ 100, 200, ...) e 3 municípios folha. */
function hub(n: number): GrafoResposta {
  const nodes = [no("deputado:1", "deputado", "Ana")];
  const edges: GraphEdge[] = [];
  for (let i = 1; i <= n; i++) {
    nodes.push(no(`empresa:${i}`, "empresa", `Empresa ${i}`));
    edges.push(lig(`empresa:${i}`, "deputado:1", "recebeu", i * 100));
  }
  for (let i = 1; i <= 3; i++) {
    nodes.push(no(`municipio:${i}`, "municipio", `Cidade ${i}`));
    edges.push(lig("deputado:1", `municipio:${i}`, "enviou_emenda", 50 * i));
  }
  return grafoDe(nodes, edges);
}

const dados = (els: ReturnType<typeof elementosDoMapa>) => els.filter((e): e is NoMapa => !("source" in e.data));

describe("famílias de relação", () => {
  it("agrupa as relações em quatro famílias, cada uma com token de cor próprio", () => {
    expect(familiaDaRelacao("recebeu")).toBe("dinheiro");
    expect(familiaDaRelacao("doou")).toBe("dinheiro");
    expect(familiaDaRelacao("enviou_emenda")).toBe("dinheiro");
    expect(familiaDaRelacao("votou_com")).toBe("votos");
    expect(familiaDaRelacao("autor_de")).toBe("autoria");
    expect(familiaDaRelacao("relator_de")).toBe("autoria");
    expect(familiaDaRelacao("filiado_a")).toBe("filiacao");
    expect(familiaDaRelacao("socio_de")).toBe("filiacao");
    const cores = Object.values(FAMILIAS).map((f) => f.cor);
    expect(new Set(cores).size).toBe(4);
    for (const c of cores) expect(c).toMatch(/^--rel-/);
  });
});

describe("valor, tamanho e espessura", () => {
  it("valoresPorNo soma só dinheiro (recebeu, doou, emenda), em módulo, nas duas pontas", () => {
    const g = grafoDe(
      [no("deputado:1", "deputado"), no("empresa:1", "empresa"), no("deputado:2", "deputado")],
      [lig("empresa:1", "deputado:1", "recebeu", 100), lig("empresa:1", "deputado:1", "doou", -30), lig("deputado:1", "deputado:2", "votou_com", 0.9)],
    );
    const v = valoresPorNo(g);
    expect(v.get("deputado:1")).toBe(130);
    expect(v.get("empresa:1")).toBe(130);
    expect(v.get("deputado:2") ?? 0).toBe(0);
  });

  it("tamanho usa raiz quadrada: área proporcional ao valor, com piso e teto fixos", () => {
    expect(tamanhoDoNo(1000, 1000)).toBe(TAM_MAX);
    expect(tamanhoDoNo(250, 1000)).toBeCloseTo(TAM_MIN + (TAM_MAX - TAM_MIN) / 2, 5);
    expect(tamanhoDoNo(0.01, 1_000_000)).toBeGreaterThanOrEqual(TAM_MIN);
    expect(tamanhoDoNo(5000, 1000)).toBe(TAM_MAX); // passou do máximo: não estoura
    expect(tamanhoDoNo(0, 1000)).toBe(TAM_SEM_VALOR);
    expect(tamanhoDoNo(10, 0)).toBe(TAM_SEM_VALOR);
  });

  it("um valor muito maior não engole os demais (raiz, não linear)", () => {
    expect(tamanhoDoNo(10_000, 1_000_000)).toBeGreaterThan(TAM_MIN + 2);
  });

  it("espessura da aresta vai de 1 a 4 px e só varia com dinheiro", () => {
    expect(espessuraDaAresta("recebeu", 0, 1000)).toBe(1);
    expect(espessuraDaAresta("recebeu", 1000, 1000)).toBe(4);
    expect(espessuraDaAresta("recebeu", 250, 1000)).toBeCloseTo(2.5, 5);
    expect(espessuraDaAresta("votou_com", 0.95, 1000)).toBe(1);
    expect(espessuraDaAresta("recebeu", -1000, 1000)).toBe(4); // estorno também pesa
  });

  it("traço da certeza: sólido, tracejado, pontilhado (certeza nunca só por cor)", () => {
    expect(tracoDaCerteza(1)).toBe("solid");
    expect(tracoDaCerteza(0.6)).toBe("dashed");
    expect(tracoDaCerteza(0.4)).toBe("dotted");
  });
});

describe("agrupaFolhas", () => {
  it(`hub com mais de ${LIMIAR_HUB} folhas guarda as ${MANTER_VISIVEIS} de maior valor e agrupa o resto por tipo`, () => {
    const grupos = agrupaFolhas(hub(20));
    expect(grupos).toHaveLength(1);
    const g = grupos[0]!;
    expect(g.id).toBe("grupo:deputado:1:empresa");
    expect(g.hub).toBe("deputado:1");
    expect(g.tipo).toBe("empresa");
    expect(g.membros).toHaveLength(20 - MANTER_VISIVEIS);
    expect(g.membros).not.toContain("empresa:20"); // a de maior valor segue visível
    expect(g.membros).toContain("empresa:1");
  });

  it(`hub pequeno, grupo com menos de ${MIN_GRUPO} nós e nó central folha não são agrupados`, () => {
    expect(agrupaFolhas(hub(10))).toEqual([]);
    const g = grafoDe([no("deputado:1", "deputado"), no("partido:A", "partido")], [lig("deputado:1", "partido:A", "filiado_a")]);
    expect(agrupaFolhas(g)).toEqual([]);
  });

  it("grupo expandido some (as folhas voltam ao mapa)", () => {
    expect(agrupaFolhas(hub(20), new Set(["grupo:deputado:1:empresa"]))).toEqual([]);
  });

  it("só agrupa quem tem uma única ligação: empresa ligada a dois deputados fica", () => {
    const g = hub(20);
    g.nodes.push(no("deputado:2", "deputado", "Beto"));
    g.edges.push(lig("empresa:1", "deputado:2", "recebeu", 10));
    const grupos = agrupaFolhas(g);
    expect(grupos[0]!.membros).not.toContain("empresa:1");
  });
});

describe("elementosDoMapa", () => {
  it("troca as folhas agrupadas por um super-nó '+N empresas' ligado ao hub", () => {
    const els = elementosDoMapa(hub(20));
    const nos = dados(els);
    const grupo = nos.find((n) => n.data.grupo)!;
    expect(grupo.data.id).toBe("grupo:deputado:1:empresa");
    expect(grupo.data.tipo).toBe("grupo");
    expect(grupo.data.rotulo).toBe("+12 empresas");
    expect(grupo.data.n).toBe(12);
    expect(grupo.data.membros).toHaveLength(12);
    expect(nos.filter((n) => n.data.tipo === "empresa")).toHaveLength(MANTER_VISIVEIS);
    const arestas = els.filter((e) => "source" in e.data);
    const doGrupo = arestas.filter((a) => "source" in a.data && (a.data.source === grupo.data.id || a.data.target === grupo.data.id));
    expect(doGrupo).toHaveLength(1);
    // 8 empresas visíveis + 3 municípios + 1 aresta de grupo
    expect(arestas).toHaveLength(MANTER_VISIVEIS + 3 + 1);
  });

  it("o pseudo-tipo 'grupo' fica fora de TIPOS_NO (a legenda só lista os 6 tipos reais)", () => {
    expect(Object.keys(TIPOS_NO)).not.toContain("grupo");
    expect(Object.keys(TIPOS_NO)).toHaveLength(6);
  });

  it("expandir devolve todos os nós, sem super-nó", () => {
    const nos = dados(elementosDoMapa(hub(20), { expandidos: new Set(["grupo:deputado:1:empresa"]) }));
    expect(nos.some((n) => n.data.grupo)).toBe(false);
    expect(nos).toHaveLength(1 + 20 + 3);
  });

  it("ids de nós e arestas são estáveis entre chamadas (permite atualizar sem recriar o canvas)", () => {
    const a = elementosDoMapa(hub(20)).map((e) => e.data.id);
    const b = elementosDoMapa(hub(20)).map((e) => e.data.id);
    expect(a).toEqual(b);
    expect(new Set(a).size).toBe(a.length);
  });

  it("nó traz valor, tamanho, rótulo curto e importância do rótulo", () => {
    const nos = dados(elementosDoMapa(hub(5)));
    const maior = nos.find((n) => n.data.id === "empresa:5")!;
    expect(maior.data.valor).toBe(500);
    expect(maior.data.tam).toBeGreaterThan(nos.find((n) => n.data.id === "empresa:1")!.data.tam);
    const centro = nos.find((n) => n.data.id === "deputado:1")!;
    expect(centro.data.rot).toBe("r1");
    expect(centro.data.dist).toBe(0);
    expect(nos.find((n) => n.data.id === "municipio:1")!.data.dist).toBe(1);
  });

  it("rótulos por importância: centro e os 12 de maior valor sempre (r1), depois r2 e r3", () => {
    const g = hub(60);
    const nos = dados(elementosDoMapa(g, { expandidos: new Set(["grupo:deputado:1:empresa"]) }));
    const por = (r: string) => nos.filter((n) => n.data.rot === r);
    expect(por("r1")).toHaveLength(13); // centro + 12
    expect(por("r1").map((n) => n.data.id)).toContain("empresa:60");
    expect(por("r2").length).toBeGreaterThan(0);
    expect(por("r3").length).toBeGreaterThan(0);
    expect(por("r1").length + por("r2").length + por("r3").length).toBe(nos.length);
  });

  it("o super-nó sempre mostra o rótulo (r1) e o sócio abrevia no canvas mas guarda o texto completo", () => {
    const g = hub(20);
    g.nodes.push(no("pessoa:s", "pessoa", "Sócio(a) de EMPRESA MUITO LONGA DO BRASIL LTDA"));
    g.edges.push(lig("pessoa:s", "empresa:20", "socio_de", 1, 0.4));
    const nos = dados(elementosDoMapa(g));
    expect(nos.find((n) => n.data.grupo)!.data.rot).toBe("r1");
    const socio = nos.find((n) => n.data.id === "pessoa:s")!;
    expect(socio.data.rotulo).toBe("Sócio(a) de EMPRESA MUITO LONGA DO BRASIL LTDA");
    expect(socio.data.curto.length).toBeLessThanOrEqual(22);
    expect(socio.data.cf).toBe(0.4);
  });

  it("aresta traz família, espessura e traço da certeza", () => {
    const g = grafoDe(
      [no("deputado:1", "deputado"), no("empresa:1", "empresa"), no("deputado:2", "deputado")],
      [lig("empresa:1", "deputado:1", "recebeu", 1000), lig("deputado:1", "deputado:2", "votou_com", 0.8, 0.5)],
    );
    const arestas = elementosDoMapa(g).flatMap((e) => ("source" in e.data ? [e.data] : []));
    const dinheiro = arestas.find((a) => a.relacao === "recebeu")!;
    expect(dinheiro.familia).toBe("dinheiro");
    expect(dinheiro.esp).toBe(4);
    expect(dinheiro.traco).toBe("solid");
    const voto = arestas.find((a) => a.relacao === "votou_com")!;
    expect(voto.familia).toBe("votos");
    expect(voto.traco).toBe("dashed");
  });
});

describe("posicoesIniciais (layout determinístico)", () => {
  const nos = dados(elementosDoMapa(hub(40), { expandidos: new Set(["grupo:deputado:1:empresa"]) }));

  it("centro na origem; mesmo tipo no mesmo anel; tipos em anéis diferentes; nada empilhado", () => {
    const pos = posicoesIniciais(nos.map((n) => n.data), "deputado:1");
    expect(pos.get("deputado:1")).toEqual({ x: 0, y: 0 });
    const raio = (id: string) => Math.hypot(pos.get(id)!.x, pos.get(id)!.y);
    expect(raio("empresa:1")).toBeCloseTo(raio("empresa:40"), 5);
    expect(raio("municipio:1")).toBeCloseTo(raio("municipio:3"), 5);
    expect(raio("municipio:1")).not.toBeCloseTo(raio("empresa:1"), 0);
    const chaves = new Set([...pos.values()].map((p) => `${Math.round(p.x)},${Math.round(p.y)}`));
    expect(chaves.size).toBe(pos.size);
  });

  it("mesmo grafo, mesmas posições, qualquer que seja a ordem de entrada", () => {
    const a = posicoesIniciais(nos.map((n) => n.data), "deputado:1");
    const b = posicoesIniciais([...nos].reverse().map((n) => n.data), "deputado:1");
    expect([...a.entries()].sort()).toEqual([...b.entries()].sort());
  });

  it("elementosDoMapa já entrega a posição inicial em cada nó", () => {
    for (const n of nos) expect(Number.isFinite(n.position.x) && Number.isFinite(n.position.y)).toBe(true);
  });
});

describe("buscaNos", () => {
  const todos = [
    no("empresa:1", "empresa", "PADARIA SÃO JOÃO LTDA"),
    no("municipio:1", "municipio", "SÃO JOÃO DEL REI"),
    no("pessoa:1", "pessoa", "João Pereira"),
    no("empresa:2", "empresa", "Auto Posto Joana"),
    no("empresa:3", "empresa", "Mercado Central"),
  ];

  it("ignora acento e caixa; quem começa com o termo vem antes de quem só contém", () => {
    const r = buscaNos(todos, "joao");
    expect(r.map((n) => n.id)).toEqual(["pessoa:1", "municipio:1", "empresa:1"]);
    expect(buscaNos(todos, "SÃO joão").map((n) => n.id)).toEqual(["municipio:1", "empresa:1"]);
  });

  it("exige 2 letras, respeita o limite e usa o valor para desempatar", () => {
    expect(buscaNos(todos, "j")).toEqual([]);
    expect(buscaNos(todos, "jo", 2)).toHaveLength(2);
    const iguais = [...todos, no("empresa:4", "empresa", "Joao Zeta"), no("empresa:5", "empresa", "Joao Alfa")];
    const valores = new Map([["empresa:4", 500]]);
    expect(buscaNos(iguais, "joao", 8, valores)[0]!.id).toBe("empresa:4"); // mesmo tipo de acerto: maior valor primeiro
  });

  it("termo sem resultado devolve lista vazia", () => {
    expect(buscaNos(todos, "xyzzy")).toEqual([]);
  });
});

describe("resumoOcultos", () => {
  const o = (tipo: string, quantidade: number, relacao: string | null = null): OcultoResumo => ({ tipo, relacao, quantidade });

  it("soma por tipo, do maior para o menor, com singular e plural em português", () => {
    expect(resumoOcultos([o("empresa", 500, "recebeu"), o("empresa", 312, "doou"), o("municipio", 90), o("deputado", 1)])).toBe(
      "812 empresas, 90 municípios, 1 deputado(a)",
    );
  });

  it("vazio devolve texto vazio", () => {
    expect(resumoOcultos([])).toBe("");
  });
});

describe("contagemVisivel", () => {
  it("conta nós por tipo e conexões por família, respeitando os tipos escondidos", () => {
    const g = hub(5);
    const els = elementosDoMapa(g);
    const c = contagemVisivel(els, new Set(["municipio"]));
    expect(c.tipos.get("empresa")).toBe(5);
    expect(c.tipos.get("municipio")).toBe(0);
    expect(c.familias.get("dinheiro")).toBe(5); // as 3 emendas ligam municípios escondidos
  });
});

describe("exportação CSV", () => {
  const g = grafoDe(
    [no("deputado:1", "deputado", 'Ana "Anita", Souza'), no("empresa:1", "empresa", "=SOMA(A1)", { sancionada: true })],
    [lig("empresa:1", "deputado:1", "recebeu", -12.5, 0.4)],
  );

  it("nós: cabeçalho, aspas escapadas e fórmula neutralizada", () => {
    const linhas = csvNos(g).split("\n");
    expect(linhas[0]).toBe("id,tipo,rotulo,valor_rs,sancionada");
    expect(linhas[1]).toBe('deputado:1,deputado,"Ana ""Anita"", Souza",12.5,não');
    expect(linhas[2]).toBe("empresa:1,empresa,'=SOMA(A1),12.5,sim");
  });

  it("conexões: nomes das duas pontas, peso numérico preservado (inclusive negativo) e certeza", () => {
    const linhas = csvArestas(g).split("\n");
    expect(linhas[0]).toBe("origem,origem_rotulo,destino,destino_rotulo,relacao,peso,certeza_cf,evidencias");
    expect(linhas[1]).toBe("empresa:1,'=SOMA(A1),deputado:1,\"Ana \"\"Anita\"\", Souza\",recebeu,-12.5,0.4,");
  });
});
