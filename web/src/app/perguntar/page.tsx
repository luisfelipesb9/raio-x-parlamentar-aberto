import type { Metadata } from "next";
import { Suspense } from "react";
import { Carregando } from "@/components/Estados";
import { Perguntar } from "@/components/Perguntar";

export const metadata: Metadata = { title: "Perguntar ao sistema" };

export default function PaginaPerguntar() {
  return (
    <div className="pagina pagina-estreita">
      <p className="eyebrow">Raciocínio do sistema, passo a passo</p>
      <h1>Perguntar ao sistema</h1>
      <p className="lead">
        Escolha uma pergunta. O sistema trabalha de trás para frente: parte da conclusão que você quer checar e procura, nos dados, o que a
        sustenta ou não.
      </p>
      <Suspense fallback={<Carregando />}>
        <Perguntar />
      </Suspense>
    </div>
  );
}
