"use client";

import { useState } from "react";
import { iniciais } from "@/lib/formato";

/** Foto oficial (Câmara). Se não carregar, mostra as iniciais: nunca um ícone quebrado. */
export function Foto({ src, nome, tamanho = 64, descrever = false }: { src: string | null; nome: string; tamanho?: number; descrever?: boolean }) {
  const [falhou, setFalhou] = useState(false);
  const estilo = { width: tamanho, height: tamanho } as const;
  if (!src || falhou) {
    return (
      <span className="foto foto-iniciais" style={estilo} aria-hidden="true">
        {iniciais(nome)}
      </span>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- fotos oficiais pequenas de domínio externo; sem otimizador
    <img
      className="foto"
      src={src}
      alt={descrever ? `Foto oficial de ${nome}` : ""}
      width={tamanho}
      height={tamanho}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      style={estilo}
      onError={() => setFalhou(true)}
    />
  );
}
