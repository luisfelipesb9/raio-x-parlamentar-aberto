import type { Metadata } from "next";
import { Suspense } from "react";
import { Carregando } from "@/components/Estados";
import { GrafoPagina } from "@/components/GrafoPagina";
import { AvisoNaoAcusacao } from "@/components/Aviso";

export const metadata: Metadata = { title: "Mapa de relações" };

export default function PaginaGrafo() {
  return (
    <div className="pagina">
      <p className="eyebrow">Quem se liga a quem</p>
      <h1>Mapa de relações</h1>
      <AvisoNaoAcusacao compacto />
      <Suspense fallback={<Carregando />}>
        <GrafoPagina />
      </Suspense>
    </div>
  );
}
