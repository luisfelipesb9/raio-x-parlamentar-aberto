/** Fábrica das rotas de texto (método, para estudantes, dados, FAQ): cada `page.tsx` só reexporta o resultado. */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CONTEUDO } from "./conteudo";
import { NOMES, PaginaFaq, PaginaTexto, metadadosDe } from "./paginas";
import { ROTA_DA_PAGINA } from "./rotas";
import type { ArquivoPagina } from "./tipos";

const NAO_ENCONTRADA: Metadata = { title: "Página não encontrada", robots: { index: false } };

export function rotaDeTexto(arquivo: ArquivoPagina) {
  const caminho = ROTA_DA_PAGINA[arquivo];
  return {
    generateMetadata(): Metadata {
      const p = CONTEUDO.paginas[arquivo];
      return p ? metadadosDe({ titulo: p.titulo, descricao: p.descricao, caminho }) : NAO_ENCONTRADA;
    },
    Pagina() {
      const p = CONTEUDO.paginas[arquivo];
      if (!p) notFound();
      return arquivo === "faq" ? <PaginaFaq pagina={p} conteudo={CONTEUDO} /> : <PaginaTexto pagina={p} caminho={caminho} nome={NOMES[arquivo]} conteudo={CONTEUDO} />;
    },
  };
}
