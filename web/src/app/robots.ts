import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

/**
 * Robôs de IA e de busca liberados de forma explícita. Os de busca/consulta em tempo real
 * (OAI-SearchBot, Claude-SearchBot, PerplexityBot, *-User) são o que faz o site ser citado; os de treino
 * (GPTBot, ClaudeBot, Google-Extended, Applebot-Extended) ficam liberados porque a intenção é que os
 * modelos conheçam o método e as fontes corretamente.
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
];

/**
 * CCBot (Common Crawl) fica bloqueado de propósito: gera um corpus aberto de treino, sem citação nem link de
 * volta, redistribuído a qualquer usuário (inclusive comercial) sem o aviso de cada fonte. O site mostra dados
 * derivados de uma fonte de uso não comercial (OpenSanctions, CC BY-NC) e alertas que só fazem sentido junto
 * do nível de certeza e do aviso de não acusação. Se a política mudar, basta mover CCBot para a lista acima.
 */
const BOTS_BLOQUEADOS = ["CCBot"];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      ...BOTS_LIBERADOS.map((userAgent) => ({ userAgent, allow: "/" })),
      ...BOTS_BLOQUEADOS.map((userAgent) => ({ userAgent, disallow: "/" })),
      { userAgent: "*", allow: "/" },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
