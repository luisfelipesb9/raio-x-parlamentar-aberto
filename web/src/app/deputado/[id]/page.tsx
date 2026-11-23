import type { Metadata } from "next";
import { Ficha } from "@/components/Ficha";

export const metadata: Metadata = { title: "Ficha do deputado" };

export default async function PaginaFicha({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="pagina">
      <Ficha id={id} />
    </div>
  );
}
