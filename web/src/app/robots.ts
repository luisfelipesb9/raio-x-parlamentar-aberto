import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

/**
 * Robôs de IA e de busca declarados de forma explícita. Os de busca/consulta em tempo real (OAI-SearchBot,
 * Claude-SearchBot, PerplexityBot, *-User) são o que faz o site ser citado; os de treino (GPTBot, ClaudeBot,
 * Google-Extended, Applebot-Extended, CCBot) ficam liberados porque a intenção é que os modelos conheçam o método e
 * as fontes corretamente. O robots.txt só diz quem pode ler; as condições de uso de cada fonte de dados estão em
 * DATA_LICENSES.md.
 */
const BOTS_LIBERADOS = [
  "GPTBot",
  "OAI-SearchBot",
  "ChatGPT-User",
  "ClaudeBot",
  "Claude-SearchBot",
  "Claude-User",
  "anthropic-ai",
  "PerplexityBot",
  "Perplexity-User",
  "Google-Extended",
  "Applebot-Extended",
  "meta-externalagent",
  "Amazonbot",
  "CCBot",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      ...BOTS_LIBERADOS.map((userAgent) => ({ userAgent, allow: "/" })),
      { userAgent: "*", allow: "/" },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
