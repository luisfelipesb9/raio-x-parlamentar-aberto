import type { MetadataRoute } from "next";
import { DESCRICAO_PADRAO, NOME_SITE } from "@/lib/seo";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: NOME_SITE,
    short_name: "Raio-X",
    description: DESCRICAO_PADRAO,
    lang: "pt-BR",
    start_url: "/",
    display: "standalone",
    background_color: "#eef3f4",
    theme_color: "#eef3f4",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
