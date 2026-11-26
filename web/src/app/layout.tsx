import type { Metadata, Viewport } from "next";
import { Manrope } from "next/font/google";
import { Efeitos } from "@/components/Efeitos";
import { Logo } from "@/components/Logo";
import { Nav, PausaToggle, TemaToggle } from "@/components/Nav";
import { TLink, TransicaoProvider } from "@/components/Transicao";
import { CONTRACT_VERSION } from "@/types/contracts";
import "./globals.css";

// Manrope variável (200–800): única família da identidade (ver DESIGN.md)
const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: { default: "Raio-X Parlamentar", template: "%s · Raio-X Parlamentar" },
  description: "Tudo o que é público sobre deputados federais, explicado em linguagem simples, com nível de certeza e link para a fonte oficial.",
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
            <p className="rodape-meta">Contratos de dados v{CONTRACT_VERSION}</p>
          </div>
        </footer>
        </TransicaoProvider>
      </body>
    </html>
  );
}
