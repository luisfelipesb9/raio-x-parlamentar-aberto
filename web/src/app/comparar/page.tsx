import type { Metadata } from "next";
import { Suspense } from "react";
import { Comparar } from "@/components/Comparar";
import { Carregando } from "@/components/Estados";

export const metadata: Metadata = { title: "Comparar deputados" };

export default function PaginaComparar() {
  return (
    <div className="pagina">
      <p className="eyebrow">Lado a lado</p>
      <h1>Comparar dois deputados</h1>
      <Suspense fallback={<Carregando />}>
        <Comparar />
      </Suspense>
    </div>
  );
}
