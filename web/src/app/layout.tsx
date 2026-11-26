import type { Metadata, Viewport } from "next";
import { Manrope } from "next/font/google";
import { CONTEUDO } from "@/content/conteudo";
import { linksSaibaMais } from "@/content/rotas";
import { Efeitos } from "@/components/Efeitos";
import { JsonLd } from "@/components/JsonLd";
import { Logo } from "@/components/Logo";
import { Nav, PausaToggle, TemaToggle } from "@/components/Nav";
import { TLink, TransicaoProvider } from "@/components/Transicao";
import { organizacaoLd, siteLd } from "@/lib/jsonld";
import { DESCRICAO_PADRAO, NOME_SITE, SITE_URL, permiteIndexar } from "@/lib/seo";
import { CONTRACT_VERSION } from "@/types/contracts";
import "./globals.css";
import "./ux.css";

// Manrope variável (200–800): única família da identidade (ver DESIGN.md)
const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope", display: "swap" });

// Códigos de verificação dos buscadores vêm do ambiente (opcionais; nenhum valor fica no repositório).
const verificacao: NonNullable<Metadata["verification"]> = {};
if (process.env.GOOGLE_SITE_VERIFICATION) verificacao.google = process.env.GOOGLE_SITE_VERIFICATION;
if (process.env.BING_SITE_VERIFICATION) verificacao.other = { "msvalidate.01": process.env.BING_SITE_VERIFICATION };

// Sem `alternates.canonical` aqui: cada página declara o seu (um canonical fixo no layout apontaria tudo para a mesma URL).
export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: NOME_SITE,
  title: { default: NOME_SITE, template: `%s · ${NOME_SITE}` },
  description: DESCRICAO_PADRAO,
  openGraph: { type: "website", locale: "pt_BR", siteName: NOME_SITE },
  twitter: { card: "summary_large_image" },
  // index/follow só com site público de fato; localhost e deploy de pré-visualização saem com noindex
  robots: permiteIndexar(SITE_URL, process.env.VERCEL_ENV) ? { index: true, follow: true } : { index: false, follow: false },
  verification: verificacao,
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "light",
  themeColor: "#eef3f4",
};

// Aplica o tema salvo antes da primeira pintura (evita piscar). Texto estático, sem dado dinâmico.
const SCRIPT_TEMA = `try{var t=localStorage.getItem("tema");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t;if(localStorage.getItem("animacoes")==="pausadas")document.documentElement.dataset.animacoes="pausadas"}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={manrope.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      <body>
        <JsonLd data={organizacaoLd()} />
        <JsonLd data={siteLd()} />
        <TransicaoProvider>
          <a className="pular" href="#conteudo">
            Pular para o conteúdo
          </a>
          <header className="topo">
            <div className="container topo-in">
              <TLink href="/" className="marca" aria-label="Raio-X Parlamentar, página inicial">
                <Logo />
                <span className="marca-nome">
                  Raio-X <span>Parlamentar</span>
                </span>
              </TLink>
              <Nav />
              <span className="topo-controles">
                <PausaToggle />
                <TemaToggle />
              </span>
            </div>
          </header>
          <main id="conteudo" className="container">
            {children}
          </main>
          <Efeitos />
        <footer className="rodape">
          <div className="container">
            <p>
              Projeto acadêmico de Sistemas Especialistas (BSI/Unimontes). Usa só dados públicos abertos, principalmente da Câmara dos
              Deputados. Não substitui a consulta aos documentos oficiais e não é acusação contra ninguém.
            </p>
            <nav aria-label="Saiba mais" className="rodape-meta">
              Saiba mais:{" "}
              {linksSaibaMais(CONTEUDO).map((l, i) => (
                <span key={l.href}>
                  {i > 0 && " · "}
                  <TLink href={l.href}>{l.texto}</TLink>
                </span>
              ))}
            </nav>
            <p className="rodape-meta">
              <TLink href="/fontes">Fontes e método</TLink> · Contratos de dados v{CONTRACT_VERSION}
            </p>
          </div>
        </footer>
        </TransicaoProvider>
      </body>
    </html>
  );
}
