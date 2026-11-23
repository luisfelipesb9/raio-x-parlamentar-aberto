"use client";

import Link from "next/link";
import { movimentoReduzido } from "@/lib/movimento";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, type ComponentProps, type MouseEvent } from "react";

type DocVT = Document & { startViewTransition?: (cb: () => Promise<void> | void) => unknown };
const Ctx = createContext<(href: string) => boolean>(() => false);

/**
 * Transições de página com a View Transitions API. O callback só resolve quando a rota mudou (ou após um
 * limite curto), então o navegador faz o cross-fade entre o antes e o depois. Sem suporte, ou com
 * prefers-reduced-motion, a navegação é a normal do Next.
 */
export function TransicaoProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const resolver = useRef<(() => void) | null>(null);

  useEffect(() => {
    resolver.current?.();
    resolver.current = null;
    delete document.documentElement.dataset.navegando; // rota trocou: libera efeitos que esperavam a navegação
  }, [path]);

  const navega = useCallback(
    (href: string): boolean => {
      const doc = document as DocVT;
      if (!doc.startViewTransition || movimentoReduzido()) return false;
      const destino = new URL(href, location.href);
      if (destino.origin !== location.origin || destino.pathname === location.pathname) return false;
      doc.startViewTransition(
        () =>
          new Promise<void>((resolve) => {
            resolver.current = resolve;
            router.push(href);
            setTimeout(resolve, 900);
          }),
      );
      return true;
    },
    [router],
  );

  return <Ctx.Provider value={navega}>{children}</Ctx.Provider>;
}

/** <Link> que usa a transição de página quando possível. */
export function TLink({ href, onClick, ...resto }: ComponentProps<typeof Link>) {
  const navega = useContext(Ctx);
  const alvo = typeof href === "string" ? href : (href.pathname ?? "");
  const aoClicar = useMemo(
    () => (e: MouseEvent<HTMLAnchorElement>) => {
      onClick?.(e);
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (typeof href !== "string") return;
      // sinaliza "navegando" para que atualizações de URL pendentes (ex.: debounce da busca) não desfaçam a navegação
      document.documentElement.dataset.navegando = "1";
      setTimeout(() => delete document.documentElement.dataset.navegando, 1500);
      if (navega(alvo)) e.preventDefault();
    },
    [onClick, navega, alvo, href],
  );
  return <Link href={href} onClick={aoClicar} {...resto} />;
}
