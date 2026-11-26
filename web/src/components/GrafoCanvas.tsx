"use client";

import type { Core, NodeSingular, StylesheetJson } from "cytoscape";
import { useCallback, useEffect, useRef } from "react";
import { TIPOS_NO } from "@/lib/grafo";
import { FAMILIAS, type DadosNoMapa, type ElementoMapa } from "@/lib/grafo-mapa";
import { movimentoReduzido } from "@/lib/movimento";

/** Dados do nó sob o ponteiro (ou com foco), com a posição dentro do canvas, para o cartão. */
export interface InfoHover {
  data: DadosNoMapa;
  x: number;
  y: number;
}

/** Pedido de foco vindo da busca: `n` muda a cada pedido, então pedir o mesmo nó de novo funciona. */
export interface PedidoFoco {
  id: string;
  n: number;
}

interface Props {
  elementos: ElementoMapa[];
  centro: string;
  selecionado: string | null;
  onSelecionar: (id: string | null) => void;
  onExpandirGrupo: (id: string) => void;
  onHover: (info: InfoHover | null) => void;
  onCalculando: (calculando: boolean) => void;
  /** Tipos de nó escondidos pela legenda. */
  tiposEscondidos: ReadonlySet<string>;
  /** Com um nó selecionado, esconde tudo que não é vizinho dele (em vez de só esmaecer). */
  soVizinhos: boolean;
  /** Nó destacado pela busca. */
  achado: string | null;
  foco: PedidoFoco | null;
  /** ref para os botões da barra de ferramentas */
  cyRef: React.MutableRefObject<Core | null>;
}

const ZOOM_ROTULOS_R2 = 1.2;
const ZOOM_DO_FOCO = 1.6;

let registrado = false;

function estilo(): StylesheetJson {
  const css = getComputedStyle(document.documentElement);
  const v = (n: string) => css.getPropertyValue(n).trim() || "#888";
  const fundo = v("--surface-solida");
  const porTipo = Object.entries(TIPOS_NO).map(([tipo, info]) => ({
    selector: `node[tipo = "${tipo}"]`,
    style: { shape: info.forma, "background-color": v(info.cor), "underlay-color": v(info.cor), "underlay-opacity": 0.22, "underlay-padding": 5, "underlay-shape": "ellipse" },
  }));
  const bordaDoGrupo = Object.entries(TIPOS_NO).map(([tipo, info]) => ({
    selector: `node[?grupo][tipoMembros = "${tipo}"]`,
    style: { "border-color": v(info.cor) },
  }));
  const porFamilia = Object.entries(FAMILIAS).map(([familia, info]) => ({
    selector: `edge[familia = "${familia}"]`,
    style: { "line-color": v(info.cor) },
  }));
  return [
    {
      selector: "node",
      style: {
        width: "data(tam)",
        height: "data(tam)",
        label: "",
        color: v("--fg"),
        "font-family": "Manrope, system-ui, sans-serif",
        "font-size": 11,
        "text-wrap": "wrap",
        "text-max-width": "96px",
        "text-valign": "bottom",
        "text-margin-y": 4,
        // halo na cor do fundo do canvas: o texto lê por cima de linhas e de outros nós
        "text-outline-color": fundo,
        "text-outline-width": 3,
        "text-outline-opacity": 1,
        "min-zoomed-font-size": 8,
        "border-width": 1.5,
        "border-color": fundo,
        "overlay-opacity": 0,
        "z-index-compare": "manual",
        "z-index": 5,
      },
    },
    ...porTipo,
    // sem valor em R$: tamanho fixo e preenchimento vazado
    { selector: "node[valor = 0]", style: { "background-opacity": 0.5, "border-width": 2, "border-color": v("--fg") } },
    // rótulos por importância: r1 sempre; r2 com zoom; r3 só no hover/seleção/busca
    { selector: "node[rot = 'r1']", style: { label: "data(curto)", "min-zoomed-font-size": 0, "z-index": 8 } },
    { selector: "node[rot = 'r2'].zoom-alto", style: { label: "data(curto)" } },
    {
      selector: "node[dist = 0]",
      style: { label: "data(rotulo)", "font-size": 13, "font-weight": 600, "text-max-width": "130px", "border-width": 3, "border-color": v("--fg"), "min-zoomed-font-size": 0, "z-index": 99 },
    },
    {
      selector: "node[?grupo]",
      style: {
        shape: "round-rectangle",
        width: 92,
        height: 32,
        "background-color": v("--surface-2"),
        "background-opacity": 1,
        "border-width": 2.5,
        "border-style": "dashed",
        "border-color": v("--borda-forte"),
        label: "data(rotulo)",
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "none",
        "font-weight": 600,
        "min-zoomed-font-size": 0,
        "underlay-opacity": 0,
        "z-index": 9,
      },
    },
    ...bordaDoGrupo,
    { selector: "node[?sancionada]", style: { "border-width": 4, "border-color": v("--perigo"), "border-style": "double" } },
    {
      selector: "edge",
      style: { width: "data(esp)", "curve-style": "haystack", "haystack-radius": 0, "line-color": v("--borda-forte"), opacity: 0.8, "z-index": 1 },
    },
    ...porFamilia,
    { selector: "edge[traco = 'dashed']", style: { "line-style": "dashed", "line-dash-pattern": [6, 4] } },
    { selector: "edge[traco = 'dotted']", style: { "line-style": "dotted" } },
    { selector: "edge[?agrupada]", style: { "line-style": "dashed", "line-dash-pattern": [3, 3] } },
    { selector: ".dim", style: { opacity: 0.12 } },
    { selector: "node.dim", style: { opacity: 0.22 } },
    { selector: ".oculto, .fora", style: { display: "none" } },
    { selector: "edge.vizinha", style: { opacity: 1, "curve-style": "straight", "line-style": "dashed", "line-dash-pattern": [7, 5], "z-index": 3 } },
    { selector: "node.hover, node.vizinho", style: { label: "data(curto)", "min-zoomed-font-size": 0, "z-index": 30 } },
    { selector: "node.achado", style: { label: "data(curto)", "min-zoomed-font-size": 0, "underlay-color": v("--acento"), "underlay-opacity": 0.5, "underlay-padding": 12, "border-color": v("--acento"), "border-width": 4, "z-index": 40 } },
    { selector: "node:selected", style: { label: "data(curto)", "min-zoomed-font-size": 0, "border-width": 4, "border-color": v("--acento"), "z-index": 50 } },
    { selector: "node[dist = 0]:selected, node[dist = 0].hover", style: { label: "data(rotulo)" } },
  ] as unknown as StylesheetJson;
}

const tipoReal = (n: NodeSingular): string => (n.data("grupo") ? (n.data("tipoMembros") as string) : (n.data("tipo") as string));

export function GrafoCanvas({ elementos, centro, selecionado, onSelecionar, onExpandirGrupo, onHover, onCalculando, tiposEscondidos, soVizinhos, achado, foco, cyRef }: Props) {
  const container = useRef<HTMLDivElement>(null);
  // O canvas é criado uma vez por centro; o resto chega por estas refs (atualizadas depois de cada render).
  const vivo = useRef({ elementos, selecionado, onSelecionar, onExpandirGrupo, onHover, onCalculando, tiposEscondidos, soVizinhos, achado, foco });
  const pronto = useRef(false);
  const aplicados = useRef<ElementoMapa[] | null>(null);
  const reaplica = useRef<((cy: Core) => void) | null>(null);
  const focoPendente = useRef<PedidoFoco | null>(null);
  const zoomAlto = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    vivo.current = { elementos, selecionado, onSelecionar, onExpandirGrupo, onHover, onCalculando, tiposEscondidos, soVizinhos, achado, foco };
  });

  /** Foco por vizinhança: esmaece (ou esconde) o que não é vizinho do nó selecionado. */
  const atualizaFoco = useCallback((cy: Core) => {
    cy.elements().removeClass("dim vizinho vizinha fora");
    const sel = cy.$("node:selected");
    if (sel.empty()) return;
    const vizinhanca = sel.closedNeighborhood();
    cy.elements().not(vizinhanca).addClass(vivo.current.soVizinhos ? "fora" : "dim");
    vizinhanca.nodes().not(sel).addClass("vizinho");
    sel.connectedEdges().addClass("vizinha");
  }, []);

  const aplicaEstados = useCallback(
    (cy: Core) => {
      const esc = vivo.current.tiposEscondidos;
      cy.nodes().forEach((n) => {
        n.toggleClass("oculto", esc.has(tipoReal(n)));
        n.toggleClass("zoom-alto", zoomAlto.current);
        n.toggleClass("achado", n.id() === vivo.current.achado);
      });
      atualizaFoco(cy);
    },
    [atualizaFoco],
  );

  const executaFoco = useCallback((cy: Core, pedido: PedidoFoco) => {
    const no = cy.getElementById(pedido.id);
    if (no.empty()) return false;
    cy.$(":selected").unselect();
    no.select();
    cy.animate({ center: { eles: no }, zoom: Math.max(cy.zoom(), ZOOM_DO_FOCO) }, { duration: movimentoReduzido() ? 0 : 260 });
    return true;
  }, []);

  /** Atualiza o canvas para os novos elementos sem recriá-lo: mantém posições, zoom e seleção. */
  const aplica = useCallback(
    (cy: Core, els: ElementoMapa[], primeira: boolean) => {
      aplicados.current = els;
      const novos = new Set(els.map((e) => e.data.id));
      // grupos que somem (expandidos): as folhas nascem onde o grupo estava
      const ancora = new Map<string, { x: number; y: number }>();
      cy.nodes("[?grupo]").forEach((g) => {
        if (novos.has(g.id())) return;
        for (const m of g.data("membros") as string[]) ancora.set(m, { ...g.position() });
      });
      const posicoesAdicionadas = new Map<string, number>();
      cy.batch(() => {
        cy.elements().filter((el) => !novos.has(el.id())).remove();
        const adicionar: cytoscape.ElementDefinition[] = [];
        for (const e of els) {
          const existente = cy.getElementById(e.data.id);
          if (existente.nonempty()) {
            existente.data(e.data);
          } else if ("position" in e) {
            let position = e.position;
            if (!primeira) {
              const a = ancora.get(e.data.id) ?? vizinhoPosicionado(cy, els, e.data.id);
              if (a) {
                const k = posicoesAdicionadas.get(`${a.x},${a.y}`) ?? 0;
                posicoesAdicionadas.set(`${a.x},${a.y}`, k + 1);
                const ang = k * 2.399963; // ângulo áureo: espalha sem sobrepor
                const raio = 28 + 11 * Math.sqrt(k);
                position = { x: a.x + Math.cos(ang) * raio, y: a.y + Math.sin(ang) * raio };
              }
            }
            adicionar.push({ group: "nodes", data: e.data as unknown as Record<string, unknown>, position });
          } else {
            adicionar.push({ group: "edges", data: e.data as unknown as Record<string, unknown> });
          }
        }
        cy.add(adicionar);
      });
      aplicaEstados(cy);

      vivo.current.onCalculando(true);
      if (timer.current) clearTimeout(timer.current);
      // deixa o aviso "Calculando o mapa…" pintar antes de o layout ocupar o navegador
      timer.current = setTimeout(() => {
        if (cy.destroyed()) return;
        const nNos = els.filter((e) => "position" in e).length;
        const layout = cy.layout({
          name: "fcose",
          quality: primeira ? "default" : "draft",
          // sem aleatoriedade: parte das posições em anéis por tipo, então o mesmo grafo dá o mesmo desenho
          randomize: false,
          animate: false,
          fit: primeira,
          padding: 24,
          numIter: primeira ? 2500 : 700,
          // grafo pequeno ganha folga: o enquadramento fica abaixo do zoom em que aparecem os rótulos r2
          nodeRepulsion: () => (nNos > 120 ? 9000 : nNos > 60 ? 12000 : 18000),
          idealEdgeLength: () => (nNos > 120 ? 60 : nNos > 60 ? 100 : 150),
          nodeSeparation: nNos > 120 ? 60 : 90,
          packComponents: false,
          fixedNodeConstraint: [{ nodeId: centro, position: { x: 0, y: 0 } }],
        } as cytoscape.LayoutOptions);
        layout.one("layoutstop", () => {
          if (cy.destroyed()) return;
          if (primeira) cy.fit(undefined, 24); // o `fit` do fcose não age com randomize:false: enquadra aqui
          if (primeira && process.env.NEXT_PUBLIC_E2E === "1") (window as unknown as { __raioXCy?: Core }).__raioXCy = cy;
          pronto.current = true;
          vivo.current.onCalculando(false);
          // os elementos mudaram enquanto o primeiro layout rodava: aplica a versão mais nova
          if (vivo.current.elementos !== aplicados.current) {
            reaplica.current?.(cy);
            return;
          }
          const pedido = focoPendente.current;
          if (pedido && executaFoco(cy, pedido)) focoPendente.current = null;
        });
        layout.run();
      }, 40);
    },
    [centro, aplicaEstados, executaFoco],
  );

  useEffect(() => {
    reaplica.current = (cy) => aplica(cy, vivo.current.elementos, false);
  }, [aplica]);

  // cria o canvas (uma vez por centro)
  useEffect(() => {
    let cy: Core | null = null;
    let cancelado = false;
    let obs: MutationObserver | null = null;
    const instancias = import("cytoscape");
    const extensao = import("cytoscape-fcose");

    void Promise.all([instancias, extensao]).then(([{ default: cytoscape }, { default: fcose }]) => {
      if (cancelado || !container.current) return;
      if (!registrado) {
        cytoscape.use(fcose);
        registrado = true;
      }
      cy = cytoscape({
        container: container.current,
        elements: [],
        style: estilo(),
        minZoom: 0.15,
        maxZoom: 3.5,
        wheelSensitivity: 0.25,
        boxSelectionEnabled: false,
        autounselectify: false,
      });
      const c = cy;
      cyRef.current = c;

      c.on("tap", "node", (e) => {
        const alvo = e.target as NodeSingular;
        if (alvo.data("grupo")) vivo.current.onExpandirGrupo(alvo.id());
        else vivo.current.onSelecionar(alvo.id());
      });
      c.on("tap", (e) => {
        if (e.target === c) vivo.current.onSelecionar(null);
      });
      c.on("mouseover", "node", (e) => {
        const alvo = e.target as NodeSingular;
        alvo.addClass("hover");
        container.current?.style.setProperty("cursor", "pointer");
        const p = alvo.renderedPosition();
        vivo.current.onHover({ data: alvo.data() as DadosNoMapa, x: p.x, y: p.y });
      });
      c.on("mouseout", "node", (e) => {
        (e.target as NodeSingular).removeClass("hover");
        container.current?.style.removeProperty("cursor");
        vivo.current.onHover(null);
      });
      c.on("select unselect", () => atualizaFoco(c));
      c.on("zoom", () => {
        const alto = c.zoom() >= ZOOM_ROTULOS_R2;
        if (alto !== zoomAlto.current) {
          zoomAlto.current = alto;
          c.nodes().toggleClass("zoom-alto", alto);
        }
        vivo.current.onHover(null);
      });
      c.on("pan drag", () => vivo.current.onHover(null));

      obs = new MutationObserver(() => c.style(estilo()));
      obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

      aplica(c, vivo.current.elementos, true);
    });

    return () => {
      cancelado = true;
      obs?.disconnect();
      if (timer.current) clearTimeout(timer.current);
      cy?.destroy();
      cyRef.current = null;
      pronto.current = false;
      vivo.current.onCalculando(false);
      delete (window as unknown as { __raioXCy?: Core }).__raioXCy;
    };
  }, [centro, cyRef, aplica, atualizaFoco]);

  // elementos novos (filtro, profundidade, grupo aberto ou fechado): atualiza no lugar, sem recriar
  useEffect(() => {
    const cy = cyRef.current;
    if (cy && pronto.current) aplica(cy, elementos, false);
  }, [elementos, aplica, cyRef]);

  // legenda (tipos escondidos), "só vizinhos" e nó achado
  useEffect(() => {
    const cy = cyRef.current;
    if (cy) aplicaEstados(cy);
  }, [tiposEscondidos, soVizinhos, achado, aplicaEstados, cyRef]);

  // arestas do nó selecionado "correm" (dash animado, ~24 fps). Desligado com prefers-reduced-motion e com "Pausar animações".
  useEffect(() => {
    if (!selecionado || movimentoReduzido()) return;
    let raf = 0;
    let ultimo = 0;
    let deslocamento = 0;
    const passo = (t: number) => {
      raf = requestAnimationFrame(passo);
      if (t - ultimo < 42 || movimentoReduzido()) return;
      ultimo = t;
      deslocamento = (deslocamento - 1.4) % 12;
      cyRef.current?.edges(".vizinha").style("line-dash-offset", deslocamento);
    };
    raf = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(raf);
  }, [selecionado, cyRef]);

  // seleção vinda de fora (lista de nós, backlinks) -> reflete no canvas
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.$(":selected").unselect();
    if (selecionado) {
      const no = cy.getElementById(selecionado);
      if (no.nonempty()) {
        no.select();
        cy.animate({ center: { eles: no }, duration: movimentoReduzido() ? 0 : 200 });
      }
    }
  }, [selecionado, cyRef]);

  // busca: centraliza e aproxima. Se o nó ainda está dentro de um grupo, espera o grupo abrir.
  useEffect(() => {
    const cy = cyRef.current;
    if (!foco) return;
    if (!cy || !pronto.current || !executaFoco(cy, foco)) focoPendente.current = foco;
  }, [foco, executaFoco, cyRef]);

  return <div ref={container} className="grafo-canvas" />;
}

/** Posição de um vizinho que já está no canvas (para o nó novo nascer perto dele). */
function vizinhoPosicionado(cy: Core, els: ElementoMapa[], id: string): { x: number; y: number } | null {
  for (const e of els) {
    if (!("source" in e.data)) continue;
    const outro = e.data.source === id ? e.data.target : e.data.target === id ? e.data.source : null;
    if (!outro) continue;
    const n = cy.getElementById(outro);
    if (n.nonempty() && n.isNode()) return { ...(n as NodeSingular).position() };
  }
  return null;
}
