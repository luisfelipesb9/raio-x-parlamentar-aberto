import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CONTEUDO } from "@/content/conteudo";
import { PaginaTermo, metadadosDe } from "@/content/paginas";
import { GLOSSARIO } from "@/lib/glossario";

/** Uma página por termo de lib/glossario.ts, gerada no build; termo fora da lista dá 404. */
export const dynamicParams = false;

export function generateStaticParams(): { termo: string }[] {
  return GLOSSARIO.map((t) => ({ termo: t.id }));
}

type Props = { params: Promise<{ termo: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { termo: id } = await params;
  const t = GLOSSARIO.find((x) => x.id === id);
  if (!t) return { title: "Termo não encontrado", robots: { index: false } };
  return metadadosDe({ titulo: t.termo, descricao: t.definicao, caminho: `/glossario/${t.id}` });
}

export default async function Termo({ params }: Props) {
  const { termo: id } = await params;
  const t = GLOSSARIO.find((x) => x.id === id);
  if (!t) notFound();
  return <PaginaTermo termo={t} conteudo={CONTEUDO} />;
}
