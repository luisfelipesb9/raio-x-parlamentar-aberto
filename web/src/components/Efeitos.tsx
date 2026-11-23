"use client";

import { useEffect, useRef } from "react";
import { movimentoReduzido } from "@/lib/movimento";

/**
 * Efeitos de ponteiro, carregados só após a hidratação e só quando fazem sentido:
 * - holofote: elementos `.holo` recebem --mx/--my (luz que segue o ponteiro);
 * - magnético: `[data-magnetico]` se aproxima do ponteiro (≤ 6 px);
 * - cursor-halo: anel sutil que acompanha o ponteiro (só ponteiro fino). O cursor do sistema continua visível.
 * Nada disso roda com prefers-reduced-motion.
 */
export function Efeitos() {
  const halo = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (movimentoReduzido()) return;
    const fino = window.matchMedia("(pointer: fine)").matches;
    const el = halo.current;
    let raf = 0;
    let ultimo: PointerEvent | null = null;
    let magnetico: HTMLElement | null = null;

    const quadro = () => {
      raf = 0;
      const e = ultimo;
      if (!e) return;
      const alvo = e.target instanceof Element ? e.target : null;
      const holo = alvo?.closest<HTMLElement>(".holo");
      if (holo) {
        const r = holo.getBoundingClientRect();
        holo.style.setProperty("--mx", `${e.clientX - r.left}px`);
        holo.style.setProperty("--my", `${e.clientY - r.top}px`);
      }
      const mag = alvo?.closest<HTMLElement>("[data-magnetico]") ?? null;
      if (magnetico && magnetico !== mag) magnetico.style.transform = "";
      magnetico = mag;
      if (mag) {
        const r = mag.getBoundingClientRect();
        const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
        const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
        mag.style.transform = `translate(${(dx * 6).toFixed(1)}px, ${(dy * 4).toFixed(1)}px)`;
      }
      if (el && fino) {
        el.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0)`;
        const interativo = alvo?.closest("a, button, input, select, summary, [role='button']");
        el.classList.toggle("ativo", Boolean(interativo));
      }
    };
    const mover = (e: PointerEvent) => {
      if (e.pointerType === "touch" || movimentoReduzido()) return;
      ultimo = e;
      el?.classList.add("visivel");
      if (!raf) raf = requestAnimationFrame(quadro);
    };
    const sair = () => {
      el?.classList.remove("visivel");
      if (magnetico) magnetico.style.transform = "";
    };
    document.addEventListener("pointermove", mover, { passive: true });
    document.documentElement.addEventListener("pointerleave", sair);
    return () => {
      document.removeEventListener("pointermove", mover);
      document.documentElement.removeEventListener("pointerleave", sair);
      cancelAnimationFrame(raf);
    };
  }, []);

  return <div ref={halo} className="cursor-halo" aria-hidden="true" />;
}
