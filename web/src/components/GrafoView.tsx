"use client";

import type { Core } from "cytoscape";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Backlink, BacklinksResposta, GraphNode, GrafoResposta } from "@/types/contracts";
import { RELACOES, ROTULOS_FILTRO, TIPOS_NO, certezaDaAresta, distanciasDoCentro, rotuloRelacao, saiDoNo, separaLigacoes, valorDaAresta } from "@/lib/grafo";
import { agrupaFolhas, contagemVisivel, csvArestas, csvNos, elementosDoMapa, escalaDeTamanho, resumoOcultos, valoresPorNo } from "@/lib/grafo-mapa";
import { formataCf } from "@/lib/nivel";
import { formataReais } from "@/lib/formato";
import { useApi } from "@/lib/useApi";
import { Carregando, ErroApi } from "./Estados";
import { Forma, FormaGrupo } from "./FormaNo";
import { GrafoBusca } from "./GrafoBusca";
import { GrafoCanvas, type InfoHover, type PedidoFoco } from "./GrafoCanvas";
import { GrafoLegenda } from "./GrafoLegenda";
import { Termo } from "./Termo";

const MAX_BACKLINKS = 30;
/** Limite de nós da API (api/main.py: MAX_NOS_GRAFO). Aparece nos avisos para a pessoa saber o que esperar. */
const LIMITE_NOS = 300;

/** Baixa um arquivo gerado no navegador (nada vai para a rede). */
function baixa(nome: string, href: string) {
  const a = document.createElement("a");
  a.href = href;
  a.download = nome;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function baixaTexto(nome: string, texto: string) {
  // BOM: o Excel abre o CSV em UTF-8 (acentos corretos)
  const url = URL.createObjectURL(new Blob(["﻿", texto], { type: "text/csv;charset=utf-8" }));
  baixa(nome, url);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function GrafoView({ centro }: { centro: string }) {
  const router = useRouter();
  const sp = useSearchParams();
  // Filtros ficam em estado local (resposta imediata) e são espelhados na URL (link compartilhável).
  const [profundidade, setProfundidade] = useState<1 | 2>(sp.get("profundidade") === "2" ? 2 : 1);
  const [ativas, setAtivas] = useState<Set<string>>(() => {
    const r = sp.get("relacoes");
    return new Set(r ? r.split(",").filter(Boolean) : RELACOES);
  });

  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [lista, setLista] = useState(false);
  const [expandidos, setExpandidos] = useState<ReadonlySet<string>>(new Set());
  const [tiposEscondidos, setTiposEscondidos] = useState<ReadonlySet<string>>(new Set());
  const [soVizinhos, setSoVizinhos] = useState(false);
  const [achado, setAchado] = useState<string | null>(null);
  const [foco, setFoco] = useState<PedidoFoco | null>(null);
  const [hover, setHover] = useState<InfoHover | null>(null);
  const [calculando, setCalculando] = useState(false);
  const cyRef = useRef<Core | null>(null);
  const painelRef = useRef<HTMLDivElement | null>(null);

  // Selecionar pela lista (ou pelo próprio painel) pode deixar o painel fora da tela: rola até ele.
  // Toque no mapa não rola, para não tirar o mapa da vista. O contador faz repetir o mesmo nó valer.
  const [pedidoRolagem, setPedidoRolagem] = useState(0);
  function selecionarEMostrar(id: string) {
    setSelecionado(id);
    setPedidoRolagem((n) => n + 1);
  }
  useEffect(() => {
    const painel = painelRef.current;
    if (pedidoRolagem === 0 || !painel) return;
    const cabecalho = Math.max(document.querySelector("header")?.getBoundingClientRect().bottom ?? 0, 0);
    const { top } = painel.getBoundingClientRect();
    if (top < cabecalho || top > window.innerHeight * 0.6) {
      window.scrollTo({ top: window.scrollY + top - cabecalho - 12 });
    }
  }, [pedidoRolagem]);

  const params = { centro, profundidade, relacoes: ativas.size === RELACOES.length ? undefined : [...ativas].join(",") };
  // sem nenhuma relação marcada não há o que consultar
  const { estado, recarregar } = useApi<GrafoResposta>(ativas.size === 0 ? null : "/grafo", params);

  // Mantém o mapa anterior na tela enquanto a nova consulta carrega: o canvas não é recriado, então zoom e posição ficam.
  const [exibido, setExibido] = useState<GrafoResposta | null>(null);
  if (estado.status === "ok" && estado.data !== exibido) setExibido(estado.data);
  const grafo = estado.status === "erro" || ativas.size === 0 ? null : exibido;
  const atualizando = estado.status === "carregando" && grafo !== null;

  function atualizaUrl(novo: { profundidade?: 1 | 2; relacoes?: Set<string> }) {
    const prof = novo.profundidade ?? profundidade;
    const rels = novo.relacoes ?? ativas;
    setProfundidade(prof);
    setAtivas(rels);
    setSelecionado(null);
    setAchado(null);
    const p = new URLSearchParams({ centro, profundidade: String(prof) });
    if (rels.size !== RELACOES.length) p.set("relacoes", [...rels].join(","));
    router.replace(`/grafo?${p.toString()}`, { scroll: false });
  }

  function alternaRelacao(r: string, marcada: boolean) {
    const novo = new Set(ativas);
    if (marcada) novo.add(r);
    else novo.delete(r);
    atualizaUrl({ relacoes: novo });
  }

  const elementos = useMemo(() => (grafo ? elementosDoMapa(grafo, { expandidos }) : []), [grafo, expandidos]);
  const gruposFechados = useMemo(() => (grafo ? agrupaFolhas(grafo, expandidos) : []), [grafo, expandidos]);
  const gruposPossiveis = useMemo(() => (grafo ? agrupaFolhas(grafo) : []), [grafo]);
  const podeRecolher = gruposPossiveis.some((g) => expandidos.has(g.id));
  const nosPorId = useMemo(() => new Map((grafo?.nodes ?? []).map((n) => [n.id, n])), [grafo]);
  const valores = useMemo(() => (grafo ? valoresPorNo(grafo) : new Map<string, number>()), [grafo]);
  const noCentro = nosPorId.get(centro);
  const noSel = selecionado ? nosPorId.get(selecionado) : undefined;

  const tiposPresentes = useMemo(() => {
    const t = new Set((grafo?.nodes ?? []).map((n) => n.tipo));
    return Object.keys(TIPOS_NO).filter((k) => t.has(k));
  }, [grafo]);
  const totaisPorTipo = useMemo(() => {
    const m = new Map<string, number>();
    for (const n of grafo?.nodes ?? []) m.set(n.tipo, (m.get(n.tipo) ?? 0) + 1);
    return m;
  }, [grafo]);
  const contagem = useMemo(() => contagemVisivel(elementos, tiposEscondidos), [elementos, tiposEscondidos]);
  const escala = useMemo(() => escalaDeTamanho(elementos), [elementos]);

  const nosOrdenados = useMemo(() => {
    if (!grafo) return [];
    const dist = distanciasDoCentro(grafo);
    const emGrupo = new Set(gruposFechados.flatMap((g) => g.membros));
    return [...grafo.nodes]
      .filter((n) => !emGrupo.has(n.id))
      .sort((a, b) => (dist.get(a.id) ?? 9) - (dist.get(b.id) ?? 9) || a.tipo.localeCompare(b.tipo) || a.rotulo.localeCompare(b.rotulo, "pt-BR"));
  }, [grafo, gruposFechados]);

  function abreGrupo(id: string) {
    setExpandidos((e) => new Set(e).add(id));
  }
  function abreTodosOsGrupos() {
    setExpandidos((e) => new Set([...e, ...gruposFechados.map((g) => g.id)]));
  }

  /** Busca: abre o grupo que guarda o nó, mostra o tipo se a legenda o escondeu, seleciona e centraliza. */
  function irParaNo(no: GraphNode) {
    const grupo = gruposFechados.find((g) => g.membros.includes(no.id));
    if (grupo) abreGrupo(grupo.id);
    if (tiposEscondidos.has(no.tipo)) {
      setTiposEscondidos((s) => {
        const novo = new Set(s);
        novo.delete(no.tipo);
        return novo;
      });
    }
    setSelecionado(no.id);
    setAchado(no.id);
    setFoco((f) => ({ id: no.id, n: (f?.n ?? 0) + 1 }));
  }

  function alternaTipo(tipo: string) {
    setTiposEscondidos((s) => {
      const novo = new Set(s);
      if (novo.has(tipo)) novo.delete(tipo);
      else novo.add(tipo);
      return novo;
    });
  }

  const slug = centro.replace(/[^a-z0-9]+/gi, "-");
  function baixaPng() {
    const cy = cyRef.current;
    if (!cy) return;
    const bg = getComputedStyle(document.documentElement).getPropertyValue("--surface-solida").trim() || "#ffffff";
    baixa(`raio-x-mapa-${slug}.png`, cy.png({ full: true, scale: 2, bg, output: "base64uri" }));
  }

  const ocultosTexto = grafo ? resumoOcultos(grafo.ocultos) : "";
  const fmt = new Intl.NumberFormat("pt-BR");

  return (
    <div
      className="grafo-pagina"
      onKeyDown={(e) => {
        // Esc em qualquer ponto do mapa tira a seleção e o destaque (na busca, o Esc limpa o campo)
        if (e.key === "Escape") {
          setSelecionado(null);
          setAchado(null);
        }
      }}
    >
      <div className="grafo-controles">
        <fieldset>
          <legend>
            <Termo id="saltos">Profundidade</Termo>
          </legend>
          <label className="opcao">
            <input type="radio" name="prof" checked={profundidade === 1} onChange={() => atualizaUrl({ profundidade: 1 })} />
            1 salto (ligações diretas)
          </label>
          <label className="opcao">
            <input type="radio" name="prof" checked={profundidade === 2} aria-describedby="aviso-prof2" onChange={() => atualizaUrl({ profundidade: 2 })} />
            2 saltos (ligações das ligações)
          </label>
          <p id="aviso-prof2" className="nota nota-curta">
            Com 2 saltos o mapa pode mostrar até {LIMITE_NOS} nós; o que passar disso fica de fora, e o aviso diz o quê.
          </p>
        </fieldset>
        <fieldset>
          <legend>Tipos de relação</legend>
          <div className="opcoes-grade">
            {RELACOES.map((r) => (
              <label key={r} className="opcao">
                <input type="checkbox" checked={ativas.has(r)} onChange={(e) => alternaRelacao(r, e.target.checked)} />
                {ROTULOS_FILTRO[r]}
              </label>
            ))}
          </div>
        </fieldset>
      </div>

      {ativas.size === 0 && (
        <p className="nota" role="status">
          Marque ao menos um tipo de relação para ver o mapa.
        </p>
      )}
      {estado.status === "carregando" && !grafo && <Carregando texto="Montando o mapa…" />}
      {estado.status === "erro" && (
        <ErroApi erro={estado.erro} onTentarDeNovo={recarregar} voltar={{ href: "/grafo", texto: "Escolher outro deputado" }} />
      )}

      {grafo && (
        <>
          <p className="grafo-resumo" data-testid="resumo-grafo">
            <strong>{noCentro?.rotulo ?? centro}</strong>: {grafo.nodes.length} <Termo id="mapa-relacoes">nós</Termo> · {grafo.edges.length} conexões · {grafo.profundidade}{" "}
            <Termo id="saltos">{grafo.profundidade === 1 ? "salto" : "saltos"}</Termo>
            {atualizando && <span className="nota"> · atualizando…</span>}
          </p>
          {grafo.truncado && (
            <p className="aviso-truncado" role="status">
              <strong>Mapa cortado.</strong> Mostrando {fmt.format(grafo.nodes.length)}
              {grafo.total_nos ? ` de ${fmt.format(grafo.total_nos)}` : ""} nós: o limite é de {LIMITE_NOS} nós para o mapa continuar legível.
              {ocultosTexto && <> Ocultos: {ocultosTexto}.</>} Ficaram os de maior valor, repartidos entre os tipos de relação. Reduza os saltos ou
              desmarque tipos de relação para ver o restante.
            </p>
          )}

          <div className="grafo-layout">
            <div className="grafo-palco">
              <GrafoBusca nos={grafo.nodes} valores={valores} onEscolher={irParaNo} onLimpar={() => setAchado(null)} />
              <div className="grafo-ferramentas" role="group" aria-label="Ferramentas do mapa">
                <button type="button" className="btn btn-sec btn-mini" onClick={() => cyRef.current?.zoom({ level: (cyRef.current?.zoom() ?? 1) * 1.3, renderedPosition: { x: (cyRef.current?.width() ?? 0) / 2, y: (cyRef.current?.height() ?? 0) / 2 } })}>
                  Aproximar
                </button>
                <button type="button" className="btn btn-sec btn-mini" onClick={() => cyRef.current?.zoom({ level: (cyRef.current?.zoom() ?? 1) / 1.3, renderedPosition: { x: (cyRef.current?.width() ?? 0) / 2, y: (cyRef.current?.height() ?? 0) / 2 } })}>
                  Afastar
                </button>
                <button type="button" className="btn btn-sec btn-mini" onClick={() => cyRef.current?.fit(undefined, 24)}>
                  Ajustar à tela
                </button>
                <button type="button" className="btn btn-sec btn-mini" aria-pressed={soVizinhos} onClick={() => setSoVizinhos((v) => !v)}>
                  Mostrar só vizinhos
                </button>
                {gruposFechados.length > 0 && (
                  <button type="button" className="btn btn-sec btn-mini" onClick={abreTodosOsGrupos}>
                    Abrir os grupos
                  </button>
                )}
                {podeRecolher && (
                  <button type="button" className="btn btn-sec btn-mini" onClick={() => setExpandidos(new Set())}>
                    Recolher
                  </button>
                )}
                <button type="button" className="btn btn-sec btn-mini" onClick={baixaPng}>
                  Baixar imagem (PNG)
                </button>
                <button type="button" className="btn btn-sec btn-mini" onClick={() => baixaTexto(`raio-x-nos-${slug}.csv`, csvNos(grafo))}>
                  Baixar nós (CSV)
                </button>
                <button type="button" className="btn btn-sec btn-mini" onClick={() => baixaTexto(`raio-x-conexoes-${slug}.csv`, csvArestas(grafo))}>
                  Baixar conexões (CSV)
                </button>
              </div>
              <div className="grafo-area">
                <div
                  className="grafo-moldura"
                  role="img"
                  aria-label={`Mapa de relações de ${noCentro?.rotulo ?? centro}: ${grafo.nodes.length} nós e ${grafo.edges.length} conexões. Para navegar por teclado ou leitor de tela, use o campo Buscar no mapa ou o botão Ver os nós como lista.`}
                >
                  <GrafoCanvas
                    elementos={elementos}
                    centro={centro}
                    selecionado={selecionado}
                    onSelecionar={setSelecionado}
                    onExpandirGrupo={abreGrupo}
                    onHover={setHover}
                    onCalculando={setCalculando}
                    tiposEscondidos={tiposEscondidos}
                    soVizinhos={soVizinhos}
                    achado={achado}
                    foco={foco}
                    cyRef={cyRef}
                  />
                </div>
                {calculando && (
                  <p className="grafo-calculando" role="status">
                    Calculando o mapa…
                  </p>
                )}
                {hover && !calculando && <CartaoDoNo info={hover} />}
              </div>
              <GrafoLegenda
                tipos={tiposPresentes}
                visiveis={contagem.tipos}
                totais={totaisPorTipo}
                escondidos={tiposEscondidos}
                onAlternar={alternaTipo}
                onLimpar={() => setTiposEscondidos(new Set())}
                familias={contagem.familias}
                escala={escala}
              />
              <p className="nota">
                Clique (ou toque) num nó para ver seus detalhes, ou num grupo (+N) para abrir. Esc tira a seleção. <Termo id="mapa-relacoes">O que é este mapa?</Termo>
              </p>
            </div>

            <div className="grafo-lateral" ref={painelRef}>
              {noSel ? (
                <PainelNo key={noSel.id} no={noSel} centro={centro} nosPorId={nosPorId} onSelecionar={selecionarEMostrar} onCentralizar={(id) => router.push(`/grafo?centro=${encodeURIComponent(id)}`)} />
              ) : (
                <p className="nota painel-vazio">Nenhum nó selecionado. Selecione um nó no mapa ou na lista para ver atributos e backlinks.</p>
              )}
            </div>
          </div>

          <div className="grafo-lista">
            <button type="button" className="btn btn-sec" aria-expanded={lista} aria-controls="lista-nos" onClick={() => setLista((l) => !l)}>
              {lista ? "Esconder a lista de nós" : "Ver os nós como lista"}
            </button>
            {lista && (
              <ul id="lista-nos" className="lista-nos" aria-label="Nós do grafo">
                {nosOrdenados.map((n) => (
                  <li key={n.id}>
                    <button type="button" aria-pressed={selecionado === n.id} onClick={() => selecionarEMostrar(n.id)}>
                      <Forma tipo={n.tipo} />
                      <span>{n.rotulo}</span>
                      <small>{TIPOS_NO[n.tipo]?.rotulo ?? n.tipo}</small>
                    </button>
                  </li>
                ))}
                {gruposFechados.map((g) => (
                  <li key={g.id}>
                    <button type="button" className="grupo-item" aria-expanded={false} onClick={() => abreGrupo(g.id)}>
                      <FormaGrupo />
                      <span>
                        +{g.membros.length} {(g.membros.length === 1 ? TIPOS_NO[g.tipo]?.rotulo : TIPOS_NO[g.tipo]?.plural)?.toLowerCase() ?? g.tipo} de {nosPorId.get(g.hub)?.rotulo ?? g.hub}
                      </span>
                      <small>abrir grupo</small>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {lista && podeRecolher && (
              <button type="button" className="btn btn-sec btn-mini" onClick={() => setExpandidos(new Set())}>
                Recolher os grupos
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

/** Cartão que acompanha o ponteiro sobre um nó: nome, tipo, R$ e certeza. Só aparência: tudo isto também está no painel. */
function CartaoDoNo({ info }: { info: InfoHover }) {
  const { data } = info;
  const tipo = data.grupo ? "Grupo de nós" : (TIPOS_NO[data.tipo]?.rotulo ?? data.tipo);
  return (
    <div className="grafo-cartao" aria-hidden="true" style={{ ["--x" as string]: `${info.x}px`, ["--y" as string]: `${info.y}px` }}>
      <strong>{data.rotulo}</strong>
      <span>{tipo}</span>
      {data.valor > 0 && <span>{formataReais(data.valor)} nas ligações do mapa</span>}
      <span>certeza (CF) {formataCf(data.cf)}</span>
      {data.sancionada && <span>sanção registrada</span>}
      {data.grupo && <span>clique para abrir</span>}
    </div>
  );
}

const ROTULOS_ATRIBUTO: Record<string, string> = { partido: "Partido", uf: "UF", n_findings: "Alertas", cf_max: "Maior certeza (CF)", nivel_max: "Nível mais alto", sigla: "Sigla", cnpj: "CNPJ", sancionada: "Sanção registrada", sancao_vigente: "Sanção vigente hoje" };

function textoAtributo(k: string, v: unknown): string | null {
  if (k === "foto" || k === "sancoes" || k === "findings") return null;
  if (typeof v === "boolean") return v ? "Sim" : "Não";
  if (typeof v === "number") return k === "cf_max" ? v.toFixed(2).replace(".", ",") : String(v);
  if (typeof v === "string") return v;
  return null;
}

function PainelNo({ no, centro, nosPorId, onSelecionar, onCentralizar }: { no: GraphNode; centro: string; nosPorId: Map<string, GraphNode>; onSelecionar: (id: string) => void; onCentralizar: (id: string) => void }) {
  const { estado, recarregar } = useApi<BacklinksResposta>(`/grafo/backlinks/${encodeURIComponent(no.id)}`);
  const sancoes =Array.isArray(no.atributos["sancoes"]) ? (no.atributos["sancoes"] as Record<string, unknown>[]) : [];
  const atributos = Object.entries(no.atributos)
    .map(([k, v]) => [k, textoAtributo(k, v)] as const)
    .filter((par): par is readonly [string, string] => par[1] !== null);
  const ehDeputado = no.tipo === "deputado";

  return (
    <aside className="painel-no" aria-label="Detalhes do nó selecionado">
      <p className="eyebrow">{TIPOS_NO[no.tipo]?.rotulo ?? no.tipo}</p>
      <h2>{no.rotulo}</h2>

      {atributos.length > 0 && (
        <dl className="atributos">
          {atributos.map(([k, v]) => (
            <div key={k}>
              <dt>{ROTULOS_ATRIBUTO[k] ?? k.replaceAll("_", " ")}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      )}
      {sancoes.length > 0 && (
        <div className="sancoes">
          <h3>
            Sanções registradas (<Termo id="ceis-cnep">CEIS/CNEP</Termo>)
          </h3>
          <ul>
            {sancoes.map((s, i) => (
              <li key={i}>
                {String(s["cadastro"] ?? "Cadastro")} · {String(s["orgao"] ?? "órgão não informado")} · {String(s["inicio"] ?? "?")} a {String(s["fim"] ?? "?")}
                {s["vigente"] === true ? " (vigente)" : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="acoes">
        {ehDeputado && (
          <Link className="btn btn-sec btn-mini" href={`/deputado/${encodeURIComponent(no.id.replace(/^deputado:/, ""))}`}>
            Abrir a ficha
          </Link>
        )}
        {no.id !== centro && (
          <button type="button" className="btn btn-sec btn-mini" onClick={() => onCentralizar(no.id)}>
            Centralizar o mapa aqui
          </button>
        )}
      </div>

      <h3>
        <Termo id="backlink">Backlinks</Termo>: todas as ligações deste nó
      </h3>
      {estado.status === "carregando" && <Carregando texto="Buscando ligações…" />}
      {estado.status === "erro" && <ErroApi erro={estado.erro} onTentarDeNovo={recarregar} />}
      {estado.status === "ok" && estado.data.total === 0 && <p className="nota">Este nó não tem ligações nos dados carregados.</p>}
      {estado.status === "ok" && estado.data.total > 0 && (
        <>
          <p className="nota">{estado.data.total} {estado.data.total === 1 ? "ligação" : "ligações"}.</p>
          {/* duas listas, cada uma com o seu limite: o que sai não fica escondido atrás do que chega */}
          {(() => {
            const { chegam, saem } = separaLigacoes(no.id, estado.data.backlinks);
            const comuns = { no, nosPorId, onSelecionar };
            return (
              <>
                <ListaLigacoes titulo="Chegam a este nó" curto="chegam" itens={chegam} {...comuns} />
                <ListaLigacoes titulo="Saem deste nó" curto="saem" itens={saem} {...comuns} />
              </>
            );
          })()}
        </>
      )}
    </aside>
  );
}

function ListaLigacoes({ titulo, curto, itens, no, nosPorId, onSelecionar }: { titulo: string; curto: string; itens: Backlink[]; no: GraphNode; nosPorId: Map<string, GraphNode>; onSelecionar: (id: string) => void }) {
  const [todos, setTodos] = useState(false);
  if (itens.length === 0) return null;
  return (
    <>
      <h4>
        {titulo} ({itens.length})
      </h4>
      <ul className="backlinks" aria-label={`Backlinks do nó: ${curto}`}>
        {(todos ? itens : itens.slice(0, MAX_BACKLINKS)).map((b, i) => {
          const valor = valorDaAresta(b.aresta.relacao, b.aresta.peso);
          const certeza = certezaDaAresta(b.aresta.cf);
          const outro = nosPorId.has(b.no.id) ? (
            <button type="button" className="link-botao" onClick={() => onSelecionar(b.no.id)}>
              {b.no.rotulo}
            </button>
          ) : (
            <Link href={`/grafo?centro=${encodeURIComponent(b.no.id)}`}>{b.no.rotulo}</Link>
          );
          return (
            <li key={`${b.no.id}-${b.aresta.relacao}-${i}`}>
              {saiDoNo(no.id, b.aresta) ? (
                <>
                  <span className="rel">
                    <em>{no.rotulo}</em> {rotuloRelacao(b.aresta.relacao)}
                  </span>{" "}
                  {outro}
                </>
              ) : (
                <>
                  {outro}{" "}
                  <span className="rel">
                    {rotuloRelacao(b.aresta.relacao)} <em>{no.rotulo}</em>
                  </span>
                </>
              )}
              {valor && <span className="rel-valor"> · {valor}</span>}
              {certeza && <span className="rel-tipo"> · {certeza}</span>}
              <span className="rel-tipo"> · {TIPOS_NO[b.no.tipo]?.rotulo ?? b.no.tipo}</span>
            </li>
          );
        })}
      </ul>
      {itens.length > MAX_BACKLINKS && (
        <button type="button" className="btn btn-sec btn-mini" onClick={() => setTodos((t) => !t)}>
          {todos ? "Mostrar menos" : `Mostrar todas as ${itens.length} que ${curto}`}
        </button>
      )}
    </>
  );
}
