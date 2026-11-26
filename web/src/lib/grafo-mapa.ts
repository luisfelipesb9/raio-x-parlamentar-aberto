import type { GraphEdge, GraphNode, GrafoResposta, OcultoResumo } from "@/types/contracts";
import { TIPOS_NO, distanciasDoCentro, rotuloCurto } from "./grafo";

/* ---------------------------------------------------------------- famílias de relação (cor da aresta) */

export type FamiliaRelacao = "dinheiro" | "votos" | "autoria" | "filiacao";

export const FAMILIAS: Record<FamiliaRelacao, { rotulo: string; cor: string; ajuda: string }> = {
  dinheiro: { rotulo: "Dinheiro", cor: "--rel-dinheiro", ajuda: "pagamentos, doações e emendas (espessura = valor)" },
  votos: { rotulo: "Votos parecidos", cor: "--rel-votos", ajuda: "deputados que votam parecido" },
  autoria: { rotulo: "Autoria", cor: "--rel-autoria", ajuda: "projetos que o deputado escreveu ou relatou" },
  filiacao: { rotulo: "Partido e sociedade", cor: "--rel-filiacao", ajuda: "filiação a partido e participação em empresa" },
};

const RELACOES_DINHEIRO: ReadonlySet<string> = new Set(["recebeu", "doou", "enviou_emenda"]);
const POR_RELACAO: Record<string, FamiliaRelacao> = {
  recebeu: "dinheiro",
  doou: "dinheiro",
  enviou_emenda: "dinheiro",
  votou_com: "votos",
  autor_de: "autoria",
  relator_de: "autoria",
  filiado_a: "filiacao",
  socio_de: "filiacao",
};

export function familiaDaRelacao(relacao: string): FamiliaRelacao {
  return POR_RELACAO[relacao] ?? "filiacao";
}

/* ---------------------------------------------------------------- valor, tamanho, espessura, traço */

export const TAM_MIN = 14;
export const TAM_MAX = 40;
export const TAM_SEM_VALOR = 16;
export const TAM_CENTRO = 52;

/** R$ ligado a cada nó (soma, em módulo, das ligações de dinheiro). Votos e autoria não têm valor. */
export function valoresPorNo(g: Pick<GrafoResposta, "edges">): Map<string, number> {
  const v = new Map<string, number>();
  for (const e of g.edges) {
    if (!RELACOES_DINHEIRO.has(e.relacao)) continue;
    const p = Math.abs(e.peso);
    v.set(e.origem, (v.get(e.origem) ?? 0) + p);
    v.set(e.destino, (v.get(e.destino) ?? 0) + p);
  }
  return v;
}

/** Escala de raiz quadrada (a área segue o valor); um valor muito grande não engole os demais. */
export function tamanhoDoNo(valor: number, max: number): number {
  if (!(valor > 0) || !(max > 0)) return TAM_SEM_VALOR;
  return TAM_MIN + (TAM_MAX - TAM_MIN) * Math.min(1, Math.sqrt(valor / max));
}

/** 1 a 4 px; só dinheiro varia com o valor. */
export function espessuraDaAresta(relacao: string, peso: number, max: number): number {
  if (!RELACOES_DINHEIRO.has(relacao) || !(max > 0)) return 1;
  return 1 + 3 * Math.min(1, Math.sqrt(Math.abs(peso) / max));
}

export type Traco = "solid" | "dashed" | "dotted";

/** A certeza nunca depende só de cor: sólido (alta), tracejado (média), pontilhado (baixa). */
export function tracoDaCerteza(cf: number): Traco {
  if (cf >= 0.8) return "solid";
  return cf >= 0.5 ? "dashed" : "dotted";
}

/* ---------------------------------------------------------------- agrupamento de folhas */

/** Nó com mais folhas que isto é um hub. */
export const LIMIAR_HUB = 12;
/** Por hub e tipo, as folhas de maior valor que continuam visíveis. */
export const MANTER_VISIVEIS = 8;
/** Grupo com menos nós que isto não vale o clique: as folhas ficam à mostra. */
export const MIN_GRUPO = 4;

export interface Grupo {
  id: string; // grupo:<hub>:<tipo>
  hub: string;
  tipo: string; // tipo dos membros
  membros: string[]; // ids, do maior valor para o menor
}

export const idDoGrupo = (hub: string, tipo: string): string => `grupo:${hub}:${tipo}`;

export function agrupaFolhas(
  g: Pick<GrafoResposta, "centro" | "nodes" | "edges">,
  expandidos: ReadonlySet<string> = new Set(),
): Grupo[] {
  const ids = new Set(g.nodes.map((n) => n.id));
  const tipoDe = new Map(g.nodes.map((n) => [n.id, n.tipo]));
  const ligacoes = g.edges.filter((e) => ids.has(e.origem) && ids.has(e.destino));
  const grau = new Map<string, number>();
  for (const e of ligacoes) {
    grau.set(e.origem, (grau.get(e.origem) ?? 0) + 1);
    grau.set(e.destino, (grau.get(e.destino) ?? 0) + 1);
  }
  const folhasDoHub = new Map<string, string[]>();
  for (const e of ligacoes) {
    for (const [folha, hub] of [[e.origem, e.destino], [e.destino, e.origem]] as const) {
      if (folha !== g.centro && grau.get(folha) === 1) (folhasDoHub.get(hub) ?? folhasDoHub.set(hub, []).get(hub)!).push(folha);
    }
  }
  const valor = valoresPorNo(g);
  const grupos: Grupo[] = [];
  for (const [hub, folhas] of folhasDoHub) {
    if (folhas.length <= LIMIAR_HUB) continue;
    const porTipo = new Map<string, string[]>();
    for (const f of folhas) {
      const t = tipoDe.get(f) ?? "?";
      (porTipo.get(t) ?? porTipo.set(t, []).get(t)!).push(f);
    }
    for (const [tipo, lista] of porTipo) {
      const ordenada = [...lista].sort((a, b) => (valor.get(b) ?? 0) - (valor.get(a) ?? 0) || a.localeCompare(b));
      const membros = ordenada.slice(MANTER_VISIVEIS);
      const id = idDoGrupo(hub, tipo);
      if (membros.length >= MIN_GRUPO && !expandidos.has(id)) grupos.push({ id, hub, tipo, membros });
    }
  }
  return grupos.sort((a, b) => a.id.localeCompare(b.id));
}

/* ---------------------------------------------------------------- elementos do Cytoscape */

export type ImportanciaRotulo = "r1" | "r2" | "r3";

export interface DadosNoMapa {
  id: string;
  /** Texto completo (painel, lista, tooltip, busca). */
  rotulo: string;
  /** Texto abreviado para o canvas. */
  curto: string;
  tipo: string; // tipo real ou "grupo"
  dist: number;
  sancionada: boolean;
  valor: number;
  tam: number;
  cf: number;
  grau: number;
  rot: ImportanciaRotulo;
  grupo: boolean;
  n: number;
  membros: string[];
  tipoMembros: string;
}
export interface DadosArestaMapa {
  id: string;
  source: string;
  target: string;
  relacao: string;
  peso: number;
  familia: FamiliaRelacao;
  esp: number;
  traco: Traco;
  cf: number;
  agrupada: boolean;
  n: number;
}
export interface NoMapa {
  data: DadosNoMapa;
  position: { x: number; y: number };
}
export interface ArestaMapa {
  data: DadosArestaMapa;
}
export type ElementoMapa = NoMapa | ArestaMapa;

/** Quantos rótulos aparecem sempre (r1) e quantos só com zoom (r2). O resto só no hover ou na seleção (r3). */
export const ROTULOS_SEMPRE = 12;
export const ROTULOS_COM_ZOOM = 40;

const ORDEM_ANEIS = ["partido", "deputado", "municipio", "proposicao", "pessoa", "empresa", "grupo"];
const RAIO_BASE = 110;
const RAIO_PASSO = 75;
const ESPACO_NO_ANEL = 34;

/** Posição inicial em anéis por tipo ao redor do centro: o layout parte daqui, então o desenho se repete. */
export function posicoesIniciais(
  nos: readonly Pick<DadosNoMapa, "id" | "tipo" | "dist">[],
  centro: string,
): Map<string, { x: number; y: number }> {
  const pos = new Map<string, { x: number; y: number }>([[centro, { x: 0, y: 0 }]]);
  const porTipo = new Map<string, typeof nos[number][]>();
  for (const n of nos) {
    if (n.id === centro) continue;
    (porTipo.get(n.tipo) ?? porTipo.set(n.tipo, []).get(n.tipo)!).push(n);
  }
  const tipos = [...porTipo.keys()].sort((a, b) => {
    const ia = ORDEM_ANEIS.indexOf(a);
    const ib = ORDEM_ANEIS.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b);
  });
  let raioAnterior = RAIO_BASE - RAIO_PASSO;
  tipos.forEach((tipo, anel) => {
    const lista = [...porTipo.get(tipo)!].sort((a, b) => a.dist - b.dist || a.id.localeCompare(b.id));
    const raio = Math.max(raioAnterior + RAIO_PASSO, (lista.length * ESPACO_NO_ANEL) / (2 * Math.PI));
    raioAnterior = raio;
    lista.forEach((n, i) => {
      const ang = (2 * Math.PI * i) / lista.length + anel * 0.5;
      pos.set(n.id, { x: Math.cos(ang) * raio, y: Math.sin(ang) * raio });
    });
  });
  return pos;
}

function plural(tipo: string, n: number): string {
  const info = TIPOS_NO[tipo];
  return (n === 1 ? info?.rotulo : info?.plural)?.toLowerCase() ?? tipo;
}

export function elementosDoMapa(g: GrafoResposta, opcoes: { expandidos?: ReadonlySet<string> } = {}): ElementoMapa[] {
  const grupos = agrupaFolhas(g, opcoes.expandidos);
  const grupoDoMembro = new Map<string, Grupo>();
  for (const gr of grupos) for (const m of gr.membros) grupoDoMembro.set(m, gr);

  const ids = new Set(g.nodes.map((n) => n.id));
  const ligacoes = g.edges.filter((e) => ids.has(e.origem) && ids.has(e.destino));
  const dist = distanciasDoCentro(g);
  const maxDist = Math.max(0, ...dist.values());
  const valor = valoresPorNo(g);
  const grau = new Map<string, number>();
  const cf = new Map<string, number>();
  for (const e of ligacoes) {
    for (const id of [e.origem, e.destino]) {
      grau.set(id, (grau.get(id) ?? 0) + 1);
      cf.set(id, Math.min(cf.get(id) ?? 1, e.cf));
    }
  }

  const visiveis = g.nodes.filter((n) => !grupoDoMembro.has(n.id));
  const vmax = Math.max(0, ...visiveis.filter((n) => n.id !== g.centro).map((n) => valor.get(n.id) ?? 0));
  const importancia = new Map<string, ImportanciaRotulo>([[g.centro, "r1"]]);
  [...visiveis]
    .filter((n) => n.id !== g.centro)
    .sort((a, b) => (valor.get(b.id) ?? 0) - (valor.get(a.id) ?? 0) || (grau.get(b.id) ?? 0) - (grau.get(a.id) ?? 0) || a.id.localeCompare(b.id))
    .forEach((n, i) => importancia.set(n.id, i < ROTULOS_SEMPRE ? "r1" : i < ROTULOS_SEMPRE + ROTULOS_COM_ZOOM ? "r2" : "r3"));

  const dadosNos: DadosNoMapa[] = visiveis.map((n) => ({
    id: n.id,
    rotulo: n.rotulo,
    curto: rotuloCurto(n.rotulo),
    tipo: n.tipo,
    dist: dist.get(n.id) ?? maxDist + 1,
    sancionada: n.atributos["sancionada"] === true,
    valor: valor.get(n.id) ?? 0,
    tam: n.id === g.centro ? TAM_CENTRO : tamanhoDoNo(valor.get(n.id) ?? 0, vmax),
    cf: cf.get(n.id) ?? 1,
    grau: grau.get(n.id) ?? 0,
    rot: importancia.get(n.id) ?? "r3",
    grupo: false,
    n: 1,
    membros: [],
    tipoMembros: "",
  }));
  for (const gr of grupos) {
    const soma = gr.membros.reduce((s, m) => s + (valor.get(m) ?? 0), 0);
    const rotulo = `+${gr.membros.length} ${plural(gr.tipo, gr.membros.length)}`;
    dadosNos.push({
      id: gr.id,
      rotulo,
      curto: rotulo,
      tipo: "grupo",
      dist: (dist.get(gr.hub) ?? 0) + 1,
      sancionada: false,
      valor: soma,
      tam: Math.max(tamanhoDoNo(soma, vmax), 26),
      cf: Math.min(...gr.membros.map((m) => cf.get(m) ?? 1)),
      grau: 1,
      rot: "r1",
      grupo: true,
      n: gr.membros.length,
      membros: gr.membros,
      tipoMembros: gr.tipo,
    });
  }

  const emax = Math.max(0, ...ligacoes.filter((e) => !grupoDoMembro.has(e.origem) && !grupoDoMembro.has(e.destino)).map((e) => Math.abs(e.peso)));
  const arestas: ArestaMapa[] = [];
  const doGrupo = new Map<string, GraphEdge[]>();
  for (const e of ligacoes) {
    const gr = grupoDoMembro.get(e.origem) ?? grupoDoMembro.get(e.destino);
    if (gr) (doGrupo.get(gr.id) ?? doGrupo.set(gr.id, []).get(gr.id)!).push(e);
    else {
      arestas.push({
        data: {
          id: `${e.origem}>${e.relacao}>${e.destino}`,
          source: e.origem,
          target: e.destino,
          relacao: e.relacao,
          peso: e.peso,
          familia: familiaDaRelacao(e.relacao),
          esp: espessuraDaAresta(e.relacao, e.peso, emax),
          traco: tracoDaCerteza(e.cf),
          cf: e.cf,
          agrupada: false,
          n: 1,
        },
      });
    }
  }
  for (const gr of grupos) {
    const es = doGrupo.get(gr.id) ?? [];
    const contagem = new Map<string, number>();
    for (const e of es) contagem.set(e.relacao, (contagem.get(e.relacao) ?? 0) + 1);
    const relacao = [...contagem.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0] ?? "recebeu";
    const peso = es.reduce((s, e) => s + Math.abs(e.peso), 0);
    const cfMin = Math.min(1, ...es.map((e) => e.cf));
    arestas.push({
      data: {
        id: `ge:${gr.id}`,
        source: gr.id,
        target: gr.hub,
        relacao,
        peso,
        familia: familiaDaRelacao(relacao),
        esp: espessuraDaAresta(relacao, peso, emax),
        traco: tracoDaCerteza(cfMin),
        cf: cfMin,
        agrupada: true,
        n: gr.membros.length,
      },
    });
  }

  const pos = posicoesIniciais(dadosNos, g.centro);
  const nos: NoMapa[] = dadosNos
    .sort((a, b) => a.id.localeCompare(b.id))
    .map((data) => ({ data, position: pos.get(data.id) ?? { x: 0, y: 0 } }));
  return [...nos, ...arestas];
}

/* ---------------------------------------------------------------- legenda viva: contagens */

export function contagemVisivel(
  els: readonly ElementoMapa[],
  tiposEscondidos: ReadonlySet<string>,
): { tipos: Map<string, number>; familias: Map<FamiliaRelacao, number> } {
  const tipos = new Map<string, number>();
  const familias = new Map<FamiliaRelacao, number>();
  const visivel = new Map<string, boolean>();
  for (const e of els) {
    if ("source" in e.data) continue;
    const real = e.data.grupo ? e.data.tipoMembros : e.data.tipo;
    visivel.set(e.data.id, !tiposEscondidos.has(real));
    if (!e.data.grupo) tipos.set(e.data.tipo, (tipos.get(e.data.tipo) ?? 0) + (tiposEscondidos.has(e.data.tipo) ? 0 : 1));
  }
  for (const e of els) {
    if (!("source" in e.data)) continue;
    if (visivel.get(e.data.source) && visivel.get(e.data.target)) familias.set(e.data.familia, (familias.get(e.data.familia) ?? 0) + e.data.n);
  }
  return { tipos, familias };
}

/** Três tamanhos de referência (maior valor, 1/4 e 1/16) para a legenda "maior = mais R$". */
export function escalaDeTamanho(els: readonly ElementoMapa[]): { valor: number; tam: number }[] {
  let max = 0;
  for (const e of els) {
    if ("source" in e.data || e.data.grupo || e.data.dist === 0) continue;
    max = Math.max(max, e.data.valor);
  }
  if (!(max > 0)) return [];
  return [max, max / 4, max / 16].map((valor) => ({ valor, tam: tamanhoDoNo(valor, max) }));
}

/* ---------------------------------------------------------------- busca */

const semAcento = (s: string): string => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

/** Até `limite` nós cujo nome contém o termo (sem acento, sem caixa). Começo do nome ou da palavra vem antes. */
export function buscaNos(nos: readonly GraphNode[], termo: string, limite = 8, valores: ReadonlyMap<string, number> = new Map()): GraphNode[] {
  const q = semAcento(termo).trim();
  if (q.length < 2) return [];
  const achados: { n: GraphNode; tier: number; idx: number }[] = [];
  for (const n of nos) {
    const l = semAcento(n.rotulo);
    const idx = l.indexOf(q);
    if (idx < 0) continue;
    achados.push({ n, tier: idx === 0 ? 0 : l[idx - 1] === " " ? 1 : 2, idx });
  }
  achados.sort(
    (a, b) =>
      a.tier - b.tier ||
      a.idx - b.idx ||
      (valores.get(b.n.id) ?? 0) - (valores.get(a.n.id) ?? 0) ||
      a.n.rotulo.localeCompare(b.n.rotulo, "pt-BR"),
  );
  return achados.slice(0, limite).map((a) => a.n);
}

/* ---------------------------------------------------------------- aviso de corte */

/** "812 empresas, 90 municípios": o que o limite de nós deixou de fora, do maior grupo para o menor. */
export function resumoOcultos(ocultos: readonly OcultoResumo[]): string {
  const porTipo = new Map<string, number>();
  for (const o of ocultos) porTipo.set(o.tipo, (porTipo.get(o.tipo) ?? 0) + o.quantidade);
  const fmt = new Intl.NumberFormat("pt-BR");
  return [...porTipo.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([tipo, q]) => `${fmt.format(q)} ${plural(tipo, q)}`)
    .join(", ");
}

/* ---------------------------------------------------------------- exportação (analista) */

/** Célula de CSV: aspas escapadas e, no começo, `=`, `+`, `-`, `@` neutralizados (a planilha não executa fórmula). */
function celula(texto: string): string {
  const seguro = /^[=+\-@\t\r]/.test(texto) ? `'${texto}` : texto;
  return /[",\n\r]/.test(seguro) ? `"${seguro.replaceAll('"', '""')}"` : seguro;
}

export function csvNos(g: Pick<GrafoResposta, "nodes" | "edges">): string {
  const valor = valoresPorNo(g);
  const linhas = g.nodes.map((n) =>
    [celula(n.id), celula(n.tipo), celula(n.rotulo), String(valor.get(n.id) ?? 0), n.atributos["sancionada"] === true ? "sim" : "não"].join(","),
  );
  return ["id,tipo,rotulo,valor_rs,sancionada", ...linhas].join("\n");
}

export function csvArestas(g: Pick<GrafoResposta, "nodes" | "edges">): string {
  const rotulo = new Map(g.nodes.map((n) => [n.id, n.rotulo]));
  const linhas = g.edges.map((e) =>
    [
      celula(e.origem),
      celula(rotulo.get(e.origem) ?? ""),
      celula(e.destino),
      celula(rotulo.get(e.destino) ?? ""),
      celula(e.relacao),
      String(e.peso),
      String(e.cf),
      celula(e.evidencia_ids.join("|")),
    ].join(","),
  );
  return ["origem,origem_rotulo,destino,destino_rotulo,relacao,peso,certeza_cf,evidencias", ...linhas].join("\n");
}
