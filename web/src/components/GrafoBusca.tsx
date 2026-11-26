"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { GraphNode } from "@/types/contracts";
import { TIPOS_NO } from "@/lib/grafo";
import { buscaNos } from "@/lib/grafo-mapa";
import { formataReais } from "@/lib/formato";
import { Forma } from "./FormaNo";

interface Props {
  nos: readonly GraphNode[];
  valores: ReadonlyMap<string, number>;
  /** Escolheu um resultado (Enter ou clique). */
  onEscolher: (no: GraphNode) => void;
  /** Esc: limpou a busca. */
  onLimpar: () => void;
}

/** Campo "Buscar no mapa": combobox acessível (setas, Enter, Esc) com atalho `/`. */
export function GrafoBusca({ nos, valores, onEscolher, onLimpar }: Props) {
  const idBase = useId();
  const idLista = `${idBase}-lista`;
  const campo = useRef<HTMLInputElement>(null);
  const [texto, setTexto] = useState("");
  const [aberto, setAberto] = useState(false);
  const [ativo, setAtivo] = useState(0);

  const resultados = useMemo(() => buscaNos(nos, texto, 8, valores), [nos, texto, valores]);
  const mostra = aberto && texto.trim().length >= 2;

  // atalho "/": foca a busca, a menos que a pessoa já esteja digitando em outro campo
  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      const alvo = e.target as HTMLElement | null;
      if (alvo && (alvo.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(alvo.tagName))) return;
      e.preventDefault();
      campo.current?.focus();
    };
    document.addEventListener("keydown", aoTeclar);
    return () => document.removeEventListener("keydown", aoTeclar);
  }, []);

  function escolhe(no: GraphNode) {
    setTexto(no.rotulo);
    setAberto(false);
    onEscolher(no);
  }

  function aoTeclar(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (resultados.length === 0) return;
      e.preventDefault();
      setAberto(true);
      setAtivo((i) => (e.key === "ArrowDown" ? (i + 1) % resultados.length : (i - 1 + resultados.length) % resultados.length));
    } else if (e.key === "Enter") {
      const no = resultados[Math.min(ativo, resultados.length - 1)];
      if (mostra && no) {
        e.preventDefault();
        escolhe(no);
      }
    } else if (e.key === "Escape") {
      e.stopPropagation();
      setTexto("");
      setAberto(false);
      onLimpar();
    }
  }

  return (
    <div className="grafo-busca">
      <label htmlFor={`${idBase}-campo`}>
        Buscar no mapa <kbd aria-hidden="true">/</kbd>
      </label>
      <input
        ref={campo}
        id={`${idBase}-campo`}
        type="text"
        role="combobox"
        aria-expanded={mostra}
        aria-controls={idLista}
        aria-autocomplete="list"
        aria-activedescendant={mostra && resultados.length > 0 ? `${idBase}-op-${ativo}` : undefined}
        aria-describedby={`${idBase}-ajuda`}
        autoComplete="off"
        spellCheck={false}
        placeholder="Nome de empresa, pessoa, município…"
        value={texto}
        onChange={(e) => {
          setTexto(e.target.value);
          setAtivo(0);
          setAberto(true);
        }}
        onFocus={() => setAberto(true)}
        onBlur={() => setAberto(false)}
        onKeyDown={aoTeclar}
      />
      <p id={`${idBase}-ajuda`} className="visually-hidden">
        Digite ao menos 2 letras. Use as setas para escolher e Enter para ir até o nó. Esc limpa. A tecla barra leva a este campo.
      </p>
      <ul id={idLista} role="listbox" aria-label="Resultados da busca no mapa" className="grafo-busca-lista" hidden={!mostra}>
        {resultados.map((n, i) => {
          const valor = valores.get(n.id) ?? 0;
          return (
            <li
              key={n.id}
              id={`${idBase}-op-${i}`}
              role="option"
              aria-selected={i === ativo}
              // mouseDown (e não click): o campo perde o foco no blur antes do click e fecharia a lista
              onMouseDown={(e) => {
                e.preventDefault();
                escolhe(n);
              }}
            >
              <Forma tipo={n.tipo} />
              <span className="nome">{n.rotulo}</span>
              <small>
                {TIPOS_NO[n.tipo]?.rotulo ?? n.tipo}
                {valor > 0 ? ` · ${formataReais(valor)}` : ""}
              </small>
            </li>
          );
        })}
      </ul>
      <p className="visually-hidden" role="status" aria-live="polite">
        {texto.trim().length >= 2 ? (resultados.length === 0 ? "Nenhum resultado no mapa." : `${resultados.length} ${resultados.length === 1 ? "resultado" : "resultados"} no mapa.`) : ""}
      </p>
    </div>
  );
}
