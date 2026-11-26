import { ImageResponse } from "next/og";
import type { DeputadoResumo } from "@/types/contracts";
import { ID_SEGURO } from "@/lib/seo";
import { servidorGetOuNull } from "@/lib/server-api";

export const alt = "Ficha do deputado no Raio-X Parlamentar";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// A rota é dinâmica (o id vem da URL): o cache fica por conta destes cabeçalhos e do cache da própria leitura da API.
const CACHE_NORMAL = "public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400";
const CACHE_CURTO = "public, max-age=60, s-maxage=60"; // API fora do ar: não prender a imagem genérica por muito tempo

const TEXTO = "Dados públicos explicados, com fonte e nível de certeza";

/** Tamanho da fonte do nome conforme o comprimento, para nomes longos não estourarem a imagem. */
function tamanhoDoNome(nome: string): number {
  if (nome.length <= 18) return 96;
  if (nome.length <= 28) return 76;
  return 60;
}

export default async function Imagem({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let perfil: DeputadoResumo | null = null;
  let cache = CACHE_NORMAL;
  if (ID_SEGURO.test(id)) {
    try {
      perfil = await servidorGetOuNull<DeputadoResumo>(`/deputados/${id}`);
    } catch {
      perfil = null; // API fora do ar: cai na imagem genérica do site, nunca em erro
      cache = CACHE_CURTO;
    }
  } // id inválido: imagem genérica, sem consultar a API

  const nome = perfil?.nome ?? "Raio-X Parlamentar";
  const partidoUf = perfil ? [perfil.partido, perfil.uf].filter(Boolean).join(" - ") : "";

  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", background: "#070b0f", color: "#e8f1f4", position: "relative", padding: 72, flexDirection: "column", justifyContent: "flex-end" }}>
        <svg width="1200" height="630" viewBox="0 0 1200 630" style={{ position: "absolute", left: 0, top: 0 }}>
          <rect x="0" y="0" width="1200" height="630" fill="#070b0f" />
          <rect x="1090" y="0" width="6" height="630" fill="#5fe3f5" fillOpacity="0.55" />
          <rect x="950" y="0" width="140" height="630" fill="#5fe3f5" fillOpacity="0.07" />
        </svg>
        <div style={{ display: "flex", fontSize: 26, letterSpacing: 6, color: "#5fe3f5", marginBottom: 22 }}>
          {perfil ? "FICHA DO DEPUTADO FEDERAL" : "DADOS PÚBLICOS, SEM JURIDIQUÊS"}
        </div>
        <div style={{ display: "flex", fontSize: tamanhoDoNome(nome), lineHeight: 1.05, letterSpacing: -2, maxWidth: 960 }}>{nome}</div>
        {partidoUf && <div style={{ display: "flex", fontSize: 44, color: "#9db0b8", marginTop: 14 }}>{partidoUf}</div>}
        <div style={{ display: "flex", fontSize: 28, color: "#9db0b8", marginTop: 34, maxWidth: 860 }}>{TEXTO}</div>
        {perfil && <div style={{ display: "flex", fontSize: 24, letterSpacing: 4, color: "#5fe3f5", marginTop: 26 }}>RAIO-X PARLAMENTAR</div>}
      </div>
    ),
    { ...size, headers: { "Cache-Control": cache } },
  );
}
