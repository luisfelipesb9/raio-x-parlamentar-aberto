"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { buscaTermo } from "@/lib/glossario";

const LARGURA_MAX = 320;
const MARGEM = 8;

type Pos = { top: number; left: number; largura: number };

function calculaPos(el: HTMLElement | null): Pos | null {
  if (!el) return null;
  const r = el.getBoundingClientRect();
  const vw = document.documentElement.clientWidth;
  const largura = Math.min(LARGURA_MAX, vw - 2 * MARGEM);
  const left = Math.max(MARGEM, Math.min(r.left, vw - largura - MARGEM));
  return { top: r.bottom + 6, left, largura };
}

/** Termo técnico com tooltip acessível (hover, foco e toque; Esc fecha). Definições vêm do glossário. */
export function Termo({ id, children }: { id: string; children: ReactNode }) {
  const termo = buscaTermo(id);
  const tipId = useId();
  const botao = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState<Pos | null>(null);
  // tipo do último ponteiro que tocou o botão: no toque o navegador emula mouseenter/focus antes do click,
  // e o click fecharia o que esses eventos acabaram de abrir. Só o click decide no toque.
  const viaPonteiro = useRef<string | null>(null);

  const aberto = pos !== null;

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: PointerEvent) => {
      if (!botao.current?.contains(e.target as Node)) setPos(null);
    };
    // o tooltip é fixed: acompanha o botão quando a página rola (ex.: foco por teclado rola até o termo)
    const reposiciona = () => setPos(calculaPos(botao.current));
    document.addEventListener("pointerdown", fora);
    window.addEventListener("scroll", reposiciona, { passive: true });
    window.addEventListener("resize", reposiciona);
    return () => {
      document.removeEventListener("pointerdown", fora);
      window.removeEventListener("scroll", reposiciona);
      window.removeEventListener("resize", reposiciona);
    };
  }, [aberto]);

  if (!termo) return <>{children}</>;

  function abre() {
    setPos(calculaPos(botao.current));
  }

  return (
    <>
      <button
        ref={botao}
        type="button"
        className="termo"
        aria-describedby={aberto ? tipId : undefined}
        onPointerDown={(e) => {
          viaPonteiro.current = e.pointerType;
        }}
        onPointerEnter={(e) => {
          if (e.pointerType === "mouse") abre();
        }}
        onPointerLeave={(e) => {
          if (e.pointerType === "mouse") setPos(null);
        }}
        onFocus={() => {
          if (viaPonteiro.current === null) abre(); // foco por teclado
        }}
        onBlur={() => {
          viaPonteiro.current = null;
          setPos(null);
        }}
        onClick={() => {
          if (viaPonteiro.current === "touch" || viaPonteiro.current === "pen") {
            if (aberto) setPos(null);
            else abre();
          } else abre(); // mouse/teclado: o hover/foco já abriu; clicar não deve fechar
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") setPos(null);
        }}
      >
        {children}
      </button>
      {pos &&
        // portal: ancestrais com backdrop-filter/transform virariam o referencial do position:fixed
        createPortal(
          <span role="tooltip" id={tipId} className="tooltip" style={{ top: pos.top, left: pos.left, width: pos.largura }}>
            <strong>{termo.termo}.</strong> {termo.definicao}
          </span>,
          document.body,
        )}
    </>
  );
}
