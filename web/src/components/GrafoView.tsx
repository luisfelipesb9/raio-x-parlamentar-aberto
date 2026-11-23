"use client";

import type { Core } from "cytoscape";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import type { BacklinksResposta, GraphNode, GrafoResposta } from "@/types/contracts";
import { RELACOES, ROTULOS_FILTRO, TIPOS_NO, distanciasDoCentro, paraElementos, rotuloRelacao } from "@/lib/grafo";
import { formataReais, formataPercentual } from "@/lib/formato";
import { useApi } from "@/lib/useApi";
import { Carregando, ErroApi } from "./Estados";
import { GrafoCanvas } from "./GrafoCanvas";
import { Termo } from "./Termo";

const MAX_BACKLINKS = 30;

function Forma({ tipo }: { tipo: string }) {
  const info = TIPOS_NO[tipo];
  const cor = `var(${info?.cor ?? "--muted"})`;
  const props = { fill: cor, stroke: "var(--fg)", strokeWidth: 1 };
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" focusable="false">
      {info?.forma === "ellipse" && <circle cx="9" cy="9" r="7" {...props} />}
      {info?.forma === "hexagon" && <polygon points="9,2 15,5.5 15,12.5 9,16 3,12.5 3,5.5" {...props} />}
      {info?.forma === "rectangle" && <rect x="3" y="3" width="12" height="12" {...props} />}
      {info?.forma === "diamond" && <polygon points="9,1.5 16.5,9 9,16.5 1.5,9" {...props} />}
      {info?.forma === "triangle" && <polygon points="9,2 16,15 2,15" {...props} />}
      {info?.forma === "round-rectangle" && <rect x="2.5" y="4" width="13" height="10" rx="4" {...props} />}
    </svg>
  );
}

function valorDaAresta(relacao: string, peso: number): string | null {
  if (["recebeu", "doou", "enviou_emenda"].includes(relacao)) return formataReais(peso);
  if (relacao === "votou_com") return `${formataPercentual(peso)} dos votos iguais`;
  return null;
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
  const cyRef = useRef<Core | null>(null);

  const params = { centro, profundidade, relacoes: ativas.size === RELACOES.length ? undefined : [...ativas].join(",") };
  // sem nenhuma relação marcada não há o que consultar
  const { estado, recarregar } = useApi<GrafoResposta>(ativas.size === 0 ? null : "/grafo", params);

  function atualizaUrl(novo: { profundidade?: 1 | 2; relacoes?: Set<string> }) {
    const prof = novo.profundidade ?? profundidade;
    const rels = novo.relacoes ?? ativas;
    setProfundidade(prof);
    setAtivas(rels);
    setSelecionado(null);
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

  const grafo = estado.status === "ok" ? estado.data : null;
  const elementos = useMemo(() => (grafo ? paraElementos(grafo) : []), [grafo]);
  const nosPorId = useMemo(() => new Map((grafo?.nodes ?? []).map((n) => [n.id, n])), [grafo]);
  const noCentro = nosPorId.get(centro);
  const noSel = selecionado ? nosPorId.get(selecionado) : undefined;

  const tiposPresentes = useMemo(() => {
    const t = new Set((grafo?.nodes ?? []).map((n) => n.tipo));
    return Object.keys(TIPOS_NO).filter((k) => t.has(k));
  }, [grafo]);

  const nosOrdenados = useMemo(() => {
    if (!grafo) return [];
    const dist = distanciasDoCentro(grafo);
    return [...grafo.nodes].sort((a, b) => (dist.get(a.id) ?? 9) - (dist.get(b.id) ?? 9) || a.tipo.localeCompare(b.tipo) || a.rotulo.localeCompare(b.rotulo, "pt-BR"));
  }, [grafo]);

  return (
    <div className="grafo-pagina">
      <div className="grafo-controles">
        <fieldset>
          <legend>Profundidade</legend>
          <label className="opcao">
            <input type="radio" name="prof" checked={profundidade === 1} onChange={() => atualizaUrl({ profundidade: 1 })} />
            1 salto (ligações diretas)
          </label>
          <label className="opcao">
            <input type="radio" name="prof" checked={profundidade === 2} onChange={() => atualizaUrl({ profundidade: 2 })} />
            2 saltos (ligações das ligações)
          </label>
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
      {estado.status === "carregando" && <Carregando texto="Montando o mapa…" />}
      {estado.status === "erro" && (
        <ErroApi erro={estado.erro} onTentarDeNovo={recarregar} voltar={{ href: "/grafo", texto: "Escolher outro deputado" }} />
      )}

      {grafo && (
        <>
          <p className="grafo-resumo" data-testid="resumo-grafo">
            <strong>{noCentro?.rotulo ?? centro}</strong>: {grafo.nodes.length} nós · {grafo.edges.length} conexões · {profundidade}{" "}
            {profundidade === 1 ? "salto" : "saltos"}
          </p>
          {grafo.truncado && (
            <p className="aviso-truncado" role="status">
              <strong>Mapa cortado.</strong> Há mais nós do que o limite de 300 para exibição, então o que você vê é parcial: foram mantidas
              primeiro as relações mais relevantes. Reduza a profundidade ou desmarque tipos de relação para ver o restante.
            </p>
          )}

          <div className="grafo-layout">
            <div className="grafo-palco">
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
              </div>
              <div
                className="grafo-moldura"
                role="img"
                aria-label={`Mapa de relações de ${noCentro?.rotulo ?? centro}: ${grafo.nodes.length} nós e ${grafo.edges.length} conexões. Para navegar por teclado ou leitor de tela, use o botão Ver os nós como lista.`}
              >
                <GrafoCanvas elementos={elementos} centro={centro} selecionado={selecionado} onSelecionar={setSelecionado} cyRef={cyRef} />
              </div>
              <ul className="legenda" aria-label="Legenda dos tipos de nó">
                {tiposPresentes.map((t) => (
                  <li key={t}>
                    <Forma tipo={t} /> {TIPOS_NO[t]?.rotulo}
                  </li>
                ))}
                <li>
                  <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" focusable="false">
                    <rect x="3" y="3" width="12" height="12" fill="var(--no-empresa)" stroke="var(--perigo)" strokeWidth="3" />
                  </svg>{" "}
                  Empresa com <Termo id="ceis-cnep">sanção</Termo>
                </li>
              </ul>
              <p className="nota">Clique (ou toque) num nó para ver seus detalhes. Linhas tracejadas = votos parecidos.</p>
            </div>

            <div className="grafo-lateral">
              {noSel ? (
                <PainelNo no={noSel} centro={centro} nosPorId={nosPorId} onSelecionar={setSelecionado} onCentralizar={(id) => router.push(`/grafo?centro=${encodeURIComponent(id)}`)} />
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
                    <button type="button" aria-pressed={selecionado === n.id} onClick={() => setSelecionado(n.id)}>
                      <Forma tipo={n.tipo} />
                      <span>{n.rotulo}</span>
                      <small>{TIPOS_NO[n.tipo]?.rotulo ?? n.tipo}</small>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
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
  const [todos, setTodos] = useState(false);
  const sancoes = Array.isArray(no.atributos["sancoes"]) ? (no.atributos["sancoes"] as Record<string, unknown>[]) : [];
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
        <Termo id="backlink">Backlinks</Termo>: quem aponta para este nó
      </h3>
      {estado.status === "carregando" && <Carregando texto="Buscando ligações…" />}
      {estado.status === "erro" && <ErroApi erro={estado.erro} onTentarDeNovo={recarregar} />}
      {estado.status === "ok" && estado.data.total === 0 && <p className="nota">Nada aponta para este nó nos dados carregados.</p>}
      {estado.status === "ok" && estado.data.total > 0 && (
        <>
          <p className="nota">{estado.data.total} {estado.data.total === 1 ? "ligação" : "ligações"}.</p>
          <ul className="backlinks" aria-label="Backlinks do nó">
            {(todos ? estado.data.backlinks : estado.data.backlinks.slice(0, MAX_BACKLINKS)).map((b, i) => {
              const noVisivel = nosPorId.has(b.no.id);
              const valor = valorDaAresta(b.aresta.relacao, b.aresta.peso);
              return (
                <li key={`${b.no.id}-${b.aresta.relacao}-${i}`}>
                  {noVisivel ? (
                    <button type="button" className="link-botao" onClick={() => onSelecionar(b.no.id)}>
                      {b.no.rotulo}
                    </button>
                  ) : (
                    <Link href={`/grafo?centro=${encodeURIComponent(b.no.id)}`}>{b.no.rotulo}</Link>
                  )}{" "}
                  <span className="rel">
                    {rotuloRelacao(b.aresta.relacao)}{" "}
                    <em>{no.rotulo}</em>
                  </span>
                  {valor && <span className="rel-valor"> · {valor}</span>}
                  <span className="rel-tipo"> · {TIPOS_NO[b.no.tipo]?.rotulo ?? b.no.tipo}</span>
                </li>
              );
            })}
          </ul>
          {estado.data.backlinks.length > MAX_BACKLINKS && (
            <button type="button" className="btn btn-sec btn-mini" onClick={() => setTodos((t) => !t)}>
              {todos ? "Mostrar menos" : `Mostrar todas as ${estado.data.backlinks.length}`}
            </button>
          )}
        </>
      )}
    </aside>
  );
}
