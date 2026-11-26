import { CONTEUDO } from "@/content/conteudo";
import { rotasDeConteudo } from "@/content/rotas";
import { GLOSSARIO } from "@/lib/glossario";
import { gerarLlmsTxt } from "@/lib/llms";

/** O texto só depende de SITE_URL (fixo no build): pode ser gerado uma vez. */
export const dynamic = "force-static";

export function GET(): Response {
  return new Response(gerarLlmsTxt(rotasDeConteudo(CONTEUDO, GLOSSARIO)), {
    headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=3600" },
  });
}
