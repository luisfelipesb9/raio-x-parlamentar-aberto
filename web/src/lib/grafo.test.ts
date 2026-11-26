import { describe, expect, it } from "vitest";
import { RELACOES, TIPOS_NO, certezaDaAresta, distanciasDoCentro, paraElementos, rotuloCurto, rotuloRelacao, saiDoNo, separaLigacoes, valorDaAresta, type ElementoNo } from "./grafo";
import type { GrafoResposta } from "@/types/contracts";

const grafo: GrafoResposta = {
  centro: "deputado:1",
  profundidade: 2,
  truncado: false,
  total_nos: null,
  total_arestas: null,
  ocultos: [],
  nodes: [
    { id: "deputado:1", tipo: "deputado", rotulo: "Ana", atributos: { partido: "PT" } },
    { id: "partido:PT", tipo: "partido", rotulo: "PT", atributos: {} },
    { id: "deputado:2", tipo: "deputado", rotulo: "Beto", atributos: {} },
    { id: "deputado:3", tipo: "deputado", rotulo: "Isolado", atributos: {} },
  ],
  edges: [
    { origem: "deputado:1", destino: "partido:PT", relacao: "filiado_a", peso: 1, cf: 1, evidencia_ids: [] },
    { origem: "deputado:2", destino: "partido:PT", relacao: "filiado_a", peso: 1, cf: 1, evidencia_ids: [] },
  ],
};

describe("distanciasDoCentro", () => {
  it("BFS não direcionado a partir do centro; inalcançável fica fora", () => {
    const d = distanciasDoCentro(grafo);
    expect(d.get("deputado:1")).toBe(0);
    expect(d.get("partido:PT")).toBe(1);
    expect(d.get("deputado:2")).toBe(2);
    expect(d.has("deputado:3")).toBe(false);
  });
});

describe("paraElementos", () => {
  it("gera elementos Cytoscape com distância e descarta arestas órfãs", () => {
    const el = paraElementos({ ...grafo, edges: [...grafo.edges, { origem: "deputado:1", destino: "empresa:x", relacao: "doou", peso: 1, cf: 1, evidencia_ids: [] }] });
    const nos = el.filter((e): e is ElementoNo => !("source" in e.data));
    const arestas = el.filter((e) => "source" in e.data);
    expect(nos).toHaveLength(4);
    expect(arestas).toHaveLength(2);
    expect(nos.find((n) => n.data.id === "deputado:1")!.data.dist).toBe(0);
    expect(nos.find((n) => n.data.id === "deputado:3")!.data.dist).toBe(3);
  });
});

describe("saiDoNo", () => {
  it("diz o sentido da frase no painel; voto parecido não tem sentido", () => {
    expect(saiDoNo("pessoa:a", { origem: "pessoa:a", relacao: "doou" })).toBe(true);
    expect(saiDoNo("deputado:1", { origem: "pessoa:a", relacao: "doou" })).toBe(false);
    expect(saiDoNo("deputado:1", { origem: "deputado:1", relacao: "votou_com" })).toBe(false);
  });
});

describe("painel de ligações", () => {
  const l = (origem: string, relacao: string) => ({ aresta: { origem, relacao } });

  it("separa o que chega (e voto parecido) do que sai, na ordem recebida", () => {
    const itens = [l("empresa:a", "recebeu"), l("deputado:1", "votou_com"), l("deputado:1", "enviou_emenda")];
    const { chegam, saem } = separaLigacoes("deputado:1", itens);
    expect(chegam).toEqual([itens[0], itens[1]]);
    expect(saem).toEqual([itens[2]]);
  });

  it("soma negativa é dita como estorno, não como dinheiro recebido", () => {
    expect(valorDaAresta("recebeu", -30)).toContain("saldo de estornos");
    expect(valorDaAresta("recebeu", 30)).not.toContain("estorno");
    expect(valorDaAresta("filiado_a", 1)).toBeNull();
  });

  it("mostra a certeza só quando há dúvida", () => {
    expect(certezaDaAresta(0.4)).toBe("certeza (CF) 0,40");
    expect(certezaDaAresta(1)).toBeNull();
  });
});

describe("vocabulário", () => {
  it("toda relação do backend tem rótulo em português simples", () => {
    for (const r of RELACOES) {
      expect(rotuloRelacao(r).length).toBeGreaterThan(3);
      expect(rotuloRelacao(r)).not.toContain("_");
    }
    expect(RELACOES).toContain("votou_com");
  });

  it("relação desconhecida cai num rótulo legível (sem underscore)", () => {
    expect(rotuloRelacao("nova_relacao")).toBe("nova relacao");
  });

  it("todo tipo de nó tem forma distinta (não depender só de cor)", () => {
    const formas = Object.values(TIPOS_NO).map((t) => t.forma);
    expect(new Set(formas).size).toBe(formas.length);
    expect(Object.keys(TIPOS_NO).sort()).toEqual(["deputado", "empresa", "municipio", "partido", "pessoa", "proposicao"]);
  });
});

describe("rotuloCurto", () => {
  it("abrevia o sócio sem repetir a razão social inteira", () => {
    const curto = rotuloCurto("Sócio(a) de FACEBOOK SERVICOS ONLINE DO BRASIL LTDA");
    expect(curto).toBe("Sócio(a) · FACEBOOK…");
    expect(curto.length).toBeLessThanOrEqual(22);
  });

  it("não mexe em rótulo que já cabe e junta espaços repetidos", () => {
    expect(rotuloCurto("Ana  Souza")).toBe("Ana Souza");
    expect(rotuloCurto("PL 1234/2024")).toBe("PL 1234/2024");
  });

  it("corta no limite, de preferência numa palavra inteira, e marca com reticências", () => {
    const curto = rotuloCurto("MARIA APARECIDA DA SILVA SOUZA", 22);
    expect(curto).toBe("MARIA APARECIDA DA…");
    expect(rotuloCurto("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 10)).toBe("ABCDEFGHI…");
  });

  it("sócio com razão social curta continua legível", () => {
    expect(rotuloCurto("Sócio(a) de ACME")).toBe("Sócio(a) · ACME");
  });
});
