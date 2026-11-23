"use client";

import { CHAVE_PAUSA, animacoesPausadas } from "@/lib/movimento";
import { TLink } from "./Transicao";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const ITENS = [
  { href: "/", texto: "Deputados" },
  { href: "/grafo", texto: "Mapa de relações" },
  { href: "/perguntar", texto: "Perguntar" },
  { href: "/comparar", texto: "Comparar" },
  { href: "/glossario", texto: "Glossário" },
];

function ativo(path: string, href: string): boolean {
  if (href === "/") return path === "/" || path.startsWith("/deputado");
  return path.startsWith(href);
}

export function Nav() {
  const path = usePathname();
  return (
    <nav aria-label="Principal" className="nav">
      <ul>
        {ITENS.map((i) => (
          <li key={i.href}>
            <TLink href={i.href} aria-current={ativo(path, i.href) ? "page" : undefined}>
              {i.texto}
            </TLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function TemaToggle() {
  const [tema, setTema] = useState<"claro" | "escuro" | null>(null);

  useEffect(() => {
    const atual = document.documentElement.dataset.theme;
    const sistema = window.matchMedia("(prefers-color-scheme: dark)").matches;
    // lê o estado do DOM (definido antes da pintura pelo script do layout)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTema(atual === "dark" || (atual !== "light" && sistema) ? "escuro" : "claro");
  }, []);

  function alterna() {
    const novo = tema === "escuro" ? "claro" : "escuro";
    document.documentElement.dataset.theme = novo === "escuro" ? "dark" : "light";
    try {
      localStorage.setItem("tema", novo === "escuro" ? "dark" : "light");
    } catch {
      /* armazenamento bloqueado: o tema vale só nesta visita */
    }
    setTema(novo);
  }

  return (
    <button type="button" className="btn btn-sec btn-mini" onClick={alterna} aria-pressed={tema === "escuro"} disabled={tema === null}>
      {tema === "escuro" ? "Tema claro" : "Tema escuro"}
    </button>
  );
}

/** WCAG 2.2.2: controle para pausar todos os efeitos em movimento, lembrado entre visitas. */
export function PausaToggle() {
  const [pausado, setPausado] = useState<boolean | null>(null);

  useEffect(() => {
    // lê o estado do DOM (definido antes da pintura pelo script do layout)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPausado(animacoesPausadas());
  }, []);

  function alterna() {
    const novo = !pausado;
    if (novo) document.documentElement.dataset.animacoes = "pausadas";
    else delete document.documentElement.dataset.animacoes;
    try {
      if (novo) localStorage.setItem(CHAVE_PAUSA, "pausadas");
      else localStorage.removeItem(CHAVE_PAUSA);
    } catch {
      /* armazenamento bloqueado: vale só nesta visita */
    }
    setPausado(novo);
  }

  return (
    <button type="button" className="btn btn-sec btn-mini" onClick={alterna} aria-pressed={pausado === true} disabled={pausado === null}>
      {pausado ? "Retomar animações" : "Pausar animações"}
    </button>
  );
}
