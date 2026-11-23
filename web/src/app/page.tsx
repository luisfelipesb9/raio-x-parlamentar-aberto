import { Suspense } from "react";
import { Busca } from "@/components/Busca";
import { Carregando } from "@/components/Estados";
import { AvisoNaoAcusacao } from "@/components/Aviso";
import { HeroScan } from "@/components/HeroScan";
import { Numeros } from "@/components/Numeros";
import { Ticker } from "@/components/Ticker";

export default function Inicio() {
  return (
    <div className="pagina">
      <section className="hero" aria-labelledby="titulo-hero">
        <div className="hero-texto">
          <p className="eyebrow">Dados públicos, sem juridiquês</p>
          <h1 id="titulo-hero">
            <span className="h1-forte">Raio-X</span> <span className="h1-leve">Parlamentar</span>
          </h1>
          <p className="lead">
            Procure um deputado federal e veja, em linguagem simples, como ele vota, quanto gasta e de onde vem o dinheiro. Cada conclusão
            mostra o quanto o sistema tem de certeza e de onde tirou a informação.
          </p>
        </div>
        <HeroScan />
      </section>
      <Numeros />
      <Ticker />
      <AvisoNaoAcusacao compacto />
      <Suspense fallback={<Carregando />}>
        <Busca />
      </Suspense>
    </div>
  );
}
