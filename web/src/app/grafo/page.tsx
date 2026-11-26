import type { Metadata } from "next";
import { canonical } from "@/lib/seo";
import { Suspense } from "react";
import { Carregando } from "@/components/Estados";
import { GrafoPagina } from "@/components/GrafoPagina";
import { AvisoNaoAcusacao } from "@/components/Aviso";

export const metadata: Metadata = {
  title: "Mapa de relações",
  description: "Quem se liga a quem nos dados públicos: empresas, municípios e emendas ligados a cada deputado, cada ligação com a fonte oficial.",
  alternates: canonical("/grafo"),
};

export default function PaginaGrafo() {
  return (
    <div className="pagina pagina-grafo">
      <p className="eyebrow">Quem se liga a quem</p>
      <h1>Mapa de relações</h1>
      <AvisoNaoAcusacao compacto />
      <Suspense fallback={<Carregando />}>
        <GrafoPagina />
      </Suspense>
    </div>
  );
}
