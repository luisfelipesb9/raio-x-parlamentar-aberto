import type { Metadata } from "next";
import { canonical } from "@/lib/seo";
import { Fontes } from "@/components/Fontes";

export const metadata: Metadata = {
  title: "Fontes e método",
  description: "De onde vêm os dados do Raio-X Parlamentar, quanto cobrem e como o sistema chega às conclusões.",
  alternates: canonical("/fontes"),
};

export default function PaginaFontes() {
  return (
    <div className="pagina pagina-estreita">
      <p className="eyebrow">Transparência do método</p>
      <h1>Fontes e método</h1>
      <p className="lead">
        De onde vêm os dados, o que a base cobre hoje e como o sistema chega a cada conclusão. Tudo aqui é conferível nos documentos oficiais.
      </p>
      <Fontes />
    </div>
  );
}
