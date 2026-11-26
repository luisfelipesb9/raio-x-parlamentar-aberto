import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { cache } from "react";
import { Ficha } from "@/components/Ficha";
import type { Finding, GrafoResposta, PerfilDeputado } from "@/types/contracts";
import { descricaoFicha, tituloFicha } from "@/lib/ficha-seo";
import { idValido } from "@/lib/id-deputado";
import { canonical, NOME_SITE, urlAbsoluta } from "@/lib/seo";
import { servidorGet, servidorGetOuNull } from "@/lib/server-api";

/**
 * ISR: a ficha é gerada no servidor na primeira visita e reaproveitada por uma hora.
 * - `generateStaticParams` devolve `[]`: nenhuma ficha é gerada no `next build` (o build não depende da API,
 *   que no CI não existe), e `dynamicParams` (ligado por padrão) gera cada ficha sob demanda e a guarda em cache.
 * - O valor de `revalidate` precisa ser um literal para o Next o ler; o teste `isr-literal.test.ts` garante
 *   que ele é igual a `REVALIDAR_SEGUNDOS` (lib/seo.ts), que as chamadas à API também usam.
 */
export const revalidate = 3600;
export const dynamicParams = true;

export function generateStaticParams(): { id: string }[] {
  return [];
}

type Props = { params: Promise<{ id: string }> };

/** Perfil, alertas e mapa de profundidade 1. Memoizado por requisição (metadados e página dividem a mesma busca). */
const carrega = cache(async (id: string) => {
  // id fora do formato: 404 direto, sem ir à API e sem criar entrada de cache para lixo de URL
  if (!idValido(id)) return null;
  const caminho = `/deputados/${encodeURIComponent(id)}`;
  const [perfil, findings] = await Promise.all([servidorGetOuNull<PerfilDeputado>(caminho), servidorGetOuNull<Finding[]>(`${caminho}/findings`)]);
  if (perfil === null || findings === null) return null;
  // O mapa é opcional: se falhar, a ficha sai sem as listas de valores em vez de falhar inteira.
  const grafo = await servidorGet<GrafoResposta>("/grafo", { centro: `deputado:${id}`, profundidade: 1 }).catch(() => null);
  return { perfil, findings, grafo };
});

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const dados = await carrega(id);
  if (dados === null) return { title: "Deputado não encontrado", robots: { index: false } };
  const { perfil, findings } = dados;
  const titulo = tituloFicha(perfil);
  const descricao = descricaoFicha(findings);
  const caminho = `/deputado/${encodeURIComponent(perfil.id)}`;
  return {
    title: titulo,
    description: descricao,
    alternates: canonical(caminho),
    openGraph: { type: "profile", title: titulo, description: descricao, url: urlAbsoluta(caminho), siteName: NOME_SITE, locale: "pt_BR" },
  };
}

export default async function PaginaFicha({ params }: Props) {
  const { id } = await params;
  const dados = await carrega(id);
  if (dados === null) notFound();
  return (
    <div className="pagina">
      <Ficha perfil={dados.perfil} findings={dados.findings} grafo={dados.grafo} />
    </div>
  );
}
