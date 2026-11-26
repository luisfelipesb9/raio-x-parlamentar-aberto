import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CONTEUDO } from "@/content/conteudo";
import { PaginaRegra, metadadosDe } from "@/content/paginas";

/** Uma página por regra de knowledge/rules, gerada no build; id fora da lista dá 404. */
export const dynamicParams = false;

export function generateStaticParams(): { regra: string }[] {
  return CONTEUDO.regras.map((r) => ({ regra: r.id }));
}

type Props = { params: Promise<{ regra: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { regra: id } = await params;
  const r = CONTEUDO.regras.find((x) => x.id === id);
  if (!r) return { title: "Regra não encontrada", robots: { index: false } };
  return metadadosDe({
    titulo: r.texto?.titulo ?? `${r.id}: ${r.nome}`,
    descricao: r.texto?.descricao ?? r.porQue ?? r.nome,
    caminho: `/regras/${r.id}`,
  });
}

export default async function Regra({ params }: Props) {
  const { regra: id } = await params;
  const r = CONTEUDO.regras.find((x) => x.id === id);
  if (!r) notFound();
  return <PaginaRegra regra={r} conteudo={CONTEUDO} />;
}
