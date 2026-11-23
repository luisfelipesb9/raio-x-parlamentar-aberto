"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { movimentoReduzido } from "@/lib/movimento";

/**
 * Revela o bloco quando ele entra na tela. O conteúdo é visível por padrão (SSR, sem JS, reduced-motion):
 * só o que está abaixo da dobra ganha a classe `revela` depois da hidratação. Manipula o DOM direto (sem estado).
 */
export function Revela({ children, id, className = "", rotulo }: { children: ReactNode; id?: string; className?: string; rotulo?: string }) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || movimentoReduzido()) return;
    if (el.getBoundingClientRect().top < window.innerHeight * 0.92) return; // já está à vista
    el.classList.add("revela");
    const io = new IntersectionObserver(
      ([e]) => {
        if (e?.isIntersecting) {
          el.classList.add("visivel");
          io.disconnect();
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      el.classList.remove("revela", "visivel");
    };
  }, []);

  return (
    <section ref={ref} id={id} className={className} aria-labelledby={rotulo}>
      {children}
    </section>
  );
}
