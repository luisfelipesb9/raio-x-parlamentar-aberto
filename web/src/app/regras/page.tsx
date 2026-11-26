import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CONTEUDO } from "@/content/conteudo";
import { PaginaIndiceRegras, RESPOSTA_INDICE_REGRAS, metadadosDe } from "@/content/paginas";

export const metadata: Metadata = metadadosDe({ titulo: "Regras do sistema", descricao: RESPOSTA_INDICE_REGRAS, caminho: "/regras" });

export default function Regras() {
  if (CONTEUDO.regras.length === 0) notFound();
  return <PaginaIndiceRegras conteudo={CONTEUDO} />;
}
