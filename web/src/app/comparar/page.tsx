import type { Metadata } from "next";
import { canonical } from "@/lib/seo";
import { Suspense } from "react";
import { Comparar } from "@/components/Comparar";
import { Carregando } from "@/components/Estados";

export const metadata: Metadata = {
  title: "Comparar deputados",
  description: "Dois deputados federais lado a lado, com os mesmos critérios, números e fontes oficiais. Comparar não é acusar.",
  alternates: canonical("/comparar"),
};

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
