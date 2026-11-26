"use client";

import { useMemo, useRef, useState, type FocusEvent, type KeyboardEvent, type MouseEvent } from "react";
import type { PassoProva } from "@/types/contracts";
import { achata, navega } from "@/lib/arvoreNav";
import { fraseDiagnostico } from "@/lib/diagnostico";
import { OBJETIVOS } from "@/lib/formato";
import { formataCf } from "@/lib/nivel";
import { montaArvore, type NoProva } from "@/lib/trilha";

const pergunta = (id: string) => OBJETIVOS.find((o) => o.id === id)?.pergunta ?? id.replaceAll("_", " ");

function notaLegivel(passo: PassoProva): string {
  if (passo.diagnostico) return fraseDiagnostico(passo.diagnostico);
  const f = passo.nota.match(/^finding (.+)$/);
  if (f) return `Gerou o alerta ${f[1]}.`;
  if (passo.nota === "condições não satisfeitas") return fraseDiagnostico(null);
  return passo.nota;
}

/**
 * Trilha da prova como árvore ARIA: um único item na ordem do Tab (tabindex gerenciado), setas para
 * percorrer, Home/End, seta direita/esquerda para abrir/fechar, Enter/espaço alternam.
 */
export function ArvoreProva({ trilha }: { trilha: readonly PassoProva[] }) {
  const arvore = useMemo(() => montaArvore(trilha), [trilha]);
  const itens = useMemo(() => achata(arvore), [arvore]);
  const [recolhidos, setRecolhidos] = useState<ReadonlySet<string>>(() => new Set());
  const [foco, setFoco] = useState("0");
  const raiz = useRef<HTMLUListElement>(null);

  const idDe = (alvo: EventTarget): string | null => (alvo as HTMLElement).closest<HTMLElement>('[role="treeitem"]')?.dataset.no ?? null;
  const foca = (id: string) => raiz.current?.querySelector<HTMLElement>(`[data-no="${id}"]`)?.focus();

  function aoTecla(e: KeyboardEvent<HTMLUListElement>) {
    const id = idDe(e.target);
    if (id === null || e.altKey || e.ctrlKey || e.metaKey) return;
    const m = navega(e.key, id, itens, recolhidos);
    if (!m) return;
    e.preventDefault();
    setRecolhidos(m.recolhidos);
    setFoco(m.foco);
    foca(m.foco); // todo destino já está na tela: abrir um nó só revela filhos, e fechar mantém o foco nele
  }

  function aoFocar(e: FocusEvent<HTMLUListElement>) {
    const id = idDe(e.target);
    if (id !== null) setFoco(id);
  }

  function aoClicar(e: MouseEvent<HTMLUListElement>) {
    if (!(e.target as HTMLElement).closest(".no-linha")) return;
    const id = idDe(e.target);
    if (id === null) return;
    const m = navega("Enter", id, itens, recolhidos);
    if (m) setRecolhidos(m.recolhidos);
  }

  return (
    <ul ref={raiz} className="arvore" role="tree" aria-label="Trilha da prova" onKeyDown={aoTecla} onFocus={aoFocar} onClick={aoClicar}>
      {arvore.map((n, i) => (
        <NoArvore key={i} no={n} id={`${i}`} nivel={1} foco={foco} recolhidos={recolhidos} />
      ))}
    </ul>
  );
}

function NoArvore({ no, id, nivel, foco, recolhidos }: { no: NoProva; id: string; nivel: number; foco: string; recolhidos: ReadonlySet<string> }) {
  const { passo } = no;
  const confirmado = passo.cf > 0;
  const temFilhos = no.filhos.length > 0;
  const aberto = temFilhos && !recolhidos.has(id);
  return (
    <li
      role="treeitem"
      data-no={id}
      tabIndex={id === foco ? 0 : -1}
      aria-level={nivel}
      aria-selected="false"
      aria-expanded={temFilhos ? aberto : undefined}
      className={`${confirmado ? "no-sim" : "no-nao"}${temFilhos ? " no-pai" : ""}`}
    >
      <div className="no-linha">
        {temFilhos && (
          <span className="no-seta" aria-hidden="true">
            {aberto ? "▾" : "▸"}
          </span>
        )}
        <span className="no-regra">{passo.regra ?? "—"}</span>
        <span className="no-obj">{pergunta(passo.objetivo)}</span>
        <span className="no-cf">
          Nível de certeza {formataCf(passo.cf)} · <strong>{confirmado ? "confirmado" : "não confirmado"}</strong>
        </span>
      </div>
      <p className="no-nota">{notaLegivel(passo)}</p>
      {aberto && (
        <ul role="group">
          {no.filhos.map((f, i) => (
            <NoArvore key={i} no={f} id={`${id}.${i}`} nivel={nivel + 1} foco={foco} recolhidos={recolhidos} />
          ))}
        </ul>
      )}
    </li>
  );
}
