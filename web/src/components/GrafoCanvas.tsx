"use client";

import type { Core, StylesheetJson } from "cytoscape";
import { movimentoReduzido } from "@/lib/movimento";
import { useEffect, useRef } from "react";
import { TIPOS_NO, type Elemento } from "@/lib/grafo";

interface Props {
  elementos: Elemento[];
  centro: string;
  selecionado: string | null;
  onSelecionar: (id: string | null) => void;
  /** ref para os botões de zoom da barra de ferramentas */
  cyRef: React.MutableRefObject<Core | null>;
}

let registrado = false;

function tokens() {
  const css = getComputedStyle(document.documentElement);
  const v = (n: string) => css.getPropertyValue(n).trim() || "#888";
  return { v };
}

function estilo(muitos: boolean): StylesheetJson {
  const { v } = tokens();
  const porTipo = Object.entries(TIPOS_NO).map(([tipo, info]) => ({
    selector: `node[tipo = "${tipo}"]`,
    style: { shape: info.forma, "background-color": v(info.cor), "underlay-color": v(info.cor), "underlay-opacity": 0.28, "underlay-padding": 6, "underlay-shape": "ellipse" },
  }));
  return [
    {
      selector: "node",
      style: {
        width: 20,
        height: 20,
        label: "",
        color: v("--fg"),
        "font-family": "Manrope, system-ui, sans-serif",
        "font-size": 11,
        "text-wrap": "ellipsis",
        "text-max-width": "110px",
        "text-valign": "bottom",
        "text-margin-y": 4,
        "text-background-color": v("--bg"),
        "text-background-opacity": 0.85,
        "text-background-padding": "2px",
        "border-width": 1.5,
        "border-color": v("--bg"),
        "overlay-opacity": 0,
      },
    },
    ...porTipo,
    { selector: "node[dist = 0]", style: { width: 46, height: 46, label: "data(rotulo)", "font-size": 13, "font-weight": 600, "border-width": 3, "border-color": v("--fg") } },
    { selector: "node[dist = 1]", style: { width: 26, height: 26, label: muitos ? "" : "data(rotulo)" } },
    { selector: "node[?sancionada]", style: { "border-width": 4, "border-color": v("--perigo"), "border-style": "double" } },
    { selector: "edge", style: { width: 1, "curve-style": "haystack", "haystack-radius": 0, "line-color": v("--borda-forte"), opacity: 0.45 } },
    { selector: "edge[relacao = 'votou_com']", style: { "line-style": "dashed", "line-dash-pattern": [4, 3] } },
    { selector: "edge[relacao = 'doou'], edge[relacao = 'enviou_emenda'], edge[relacao = 'recebeu']", style: { width: 1.6 } },
    { selector: ".dim", style: { opacity: 0.15 } },
    { selector: "node.dim", style: { opacity: 0.25 } },
    { selector: "edge.vizinha", style: { opacity: 1, width: 2.2, "curve-style": "straight", "line-style": "dashed", "line-dash-pattern": [7, 5], "line-color": v("--acento") } },
    { selector: "node.hover, node.vizinho", style: { label: "data(rotulo)", "z-index": 10 } },
    { selector: "node:selected", style: { label: "data(rotulo)", "border-width": 4, "border-color": v("--acento"), "z-index": 20 } },
  ] as unknown as StylesheetJson;
}

export function GrafoCanvas({ elementos, centro, selecionado, onSelecionar, cyRef }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const aoSelecionar = useRef(onSelecionar);
  const selecionadoRef = useRef(selecionado);
  useEffect(() => {
    aoSelecionar.current = onSelecionar;
    selecionadoRef.current = selecionado;
  });

  useEffect(() => {
    let cy: Core | null = null;
    let cancelado = false;
    let obs: MutationObserver | null = null;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const nNos = elementos.filter((e) => !("source" in e.data)).length;
    const muitos = nNos > 60;

    void Promise.all([import("cytoscape"), import("cytoscape-fcose")]).then(([{ default: cytoscape }, { default: fcose }]) => {
      if (cancelado || !container.current) return;
      if (!registrado) {
        cytoscape.use(fcose);
        registrado = true;
      }
      cy = cytoscape({
        container: container.current,
        elements: elementos as unknown as cytoscape.ElementDefinition[],
        style: estilo(muitos),
        // fcose: layout por forças (estilo Obsidian); determinístico com `randomize: false` + semente fixa do cytoscape
        layout: {
          name: "fcose",
          quality: "default",
          randomize: true,
          animate: false,
          fit: true,
          padding: 24,
          nodeRepulsion: () => (muitos ? 9000 : 6000),
          idealEdgeLength: () => (muitos ? 60 : 90),
          nodeSeparation: 60,
          packComponents: true,
          fixedNodeConstraint: [{ nodeId: centro, position: { x: 0, y: 0 } }],
        } as cytoscape.LayoutOptions,
        minZoom: 0.15,
        maxZoom: 3.5,
        wheelSensitivity: 0.25,
        boxSelectionEnabled: false,
        autounselectify: false,
      });
      cyRef.current = cy;
      if (process.env.NEXT_PUBLIC_E2E === "1") (window as unknown as { __raioXCy?: Core }).__raioXCy = cy;

      cy.on("tap", "node", (e) => aoSelecionar.current(e.target.id() as string));
      cy.on("tap", (e) => {
        if (e.target === cy) aoSelecionar.current(null);
      });
      cy.on("mouseover", "node", (e) => {
        e.target.addClass("hover");
        container.current?.style.setProperty("cursor", "pointer");
      });
      cy.on("mouseout", "node", (e) => {
        e.target.removeClass("hover");
        container.current?.style.removeProperty("cursor");
      });
      cy.on("select unselect", () => {
        if (!cy) return;
        cy.elements().removeClass("dim vizinho vizinha");
        const sel = cy.$("node:selected");
        if (sel.nonempty()) {
          const vizinhanca = sel.closedNeighborhood();
          cy.elements().not(vizinhanca).addClass("dim");
          vizinhanca.nodes().not(sel).addClass("vizinho");
          sel.connectedEdges().addClass("vizinha");
        }
      });
      if (selecionadoRef.current) cy.getElementById(selecionadoRef.current).select();

      const restila = () => cy?.style(estilo(muitos));
      obs = new MutationObserver(restila);
      obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
      mq.addEventListener("change", restila);
    });

    return () => {
      cancelado = true;
      obs?.disconnect();
      cy?.destroy();
      cyRef.current = null;
      delete (window as unknown as { __raioXCy?: Core }).__raioXCy;
    };
    // `centro` identifica o grafo; elementos mudam junto com ele
  }, [elementos, centro, cyRef]);

  // arestas do nó selecionado "correm" (dash animado, ~24 fps). Desligado com prefers-reduced-motion.
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
        cy.animate({ center: { eles: no }, duration: 200 });
      }
    }
  }, [selecionado, cyRef]);

  return <div ref={container} className="grafo-canvas" />;
}
