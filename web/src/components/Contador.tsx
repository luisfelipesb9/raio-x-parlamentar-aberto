"use client";

import { useEffect, useRef } from "react";
import { movimentoReduzido } from "@/lib/movimento";

const fmt = new Intl.NumberFormat("pt-BR");

/**
 * Número que conta de 0 ao valor quando entra na tela. O texto final já vem no HTML (SSR, leitor de tela e
 * prefers-reduced-motion veem o valor direto). A animação mexe só no DOM, sem estado React.
 */
export function Contador({ valor, duracao = 1100 }: { valor: number; duracao?: number }) {
  const alvo = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = alvo.current;
    if (!el || movimentoReduzido()) return;
    let raf = 0;
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e?.isIntersecting) return;
        io.disconnect();
        const t0 = performance.now();
        const passo = (t: number) => {
          const p = Math.min(1, (t - t0) / duracao);
          const suave = 1 - Math.pow(1 - p, 4);
          el.textContent = fmt.format(Math.round(valor * suave));
          if (p < 1) raf = requestAnimationFrame(passo);
        };
        el.textContent = "0";
        raf = requestAnimationFrame(passo);
      },
      { threshold: 0.6 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
      el.textContent = fmt.format(valor);
    };
  }, [valor, duracao]);

  return (
    <>
      <span ref={alvo} aria-hidden="true">
        {fmt.format(valor)}
      </span>
      <span className="visually-hidden">{fmt.format(valor)}</span>
    </>
  );
}
