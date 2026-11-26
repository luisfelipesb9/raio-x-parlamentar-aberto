import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Busca } from "@/components/Busca";
import { Carregando } from "@/components/Estados";
import { AvisoNaoAcusacao } from "@/components/Aviso";
import { HeroScan } from "@/components/HeroScan";
import { Numeros } from "@/components/Numeros";
import { Ticker } from "@/components/Ticker";
import type { CoberturaResposta } from "@/types/contracts";
import { JsonLd } from "@/components/JsonLd";
import { datasetLd } from "@/lib/jsonld";
import { canonical } from "@/lib/seo";
import { servidorGet } from "@/lib/server-api";

/** ISR de uma hora (literal exigido pelo Next; igualdade com REVALIDAR_SEGUNDOS é checada em isr-literal.test.ts). */
export const revalidate = 3600;

export const metadata: Metadata = { alternates: canonical("/") };

/** Contagens do servidor para o bloco "Veja a lista". Sem API (build no CI, falha passageira) volta `null`, sem erro. */
async function contagens(): Promise<{ deputados: number; alertas: number; atualizadoEm: string | null } | null> {
  try {
    const c = await servidorGet<CoberturaResposta>("/cobertura");
    const datas = c.fontes.map((f) => f.coletado_em_max).filter((d): d is string => !!d);
    return { deputados: c.n_deputados, alertas: c.n_findings, atualizadoEm: datas.length ? datas.sort().at(-1)! : null };
  } catch {
    return null;
  }
}

const inteiro = new Intl.NumberFormat("pt-BR");

export default async function Inicio() {
  const total = await contagens();
  return (
    <div className="pagina">
      <JsonLd data={datasetLd({ atualizadoEm: total?.atualizadoEm })} />
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
      <section className="secao" aria-labelledby="h-lista">
        <h2 id="h-lista">Veja todos os deputados</h2>
        <p>
          {total ? (
            <>
              A base reúne <strong>{inteiro.format(total.deputados)}</strong> deputados federais e{" "}
              <strong>{inteiro.format(total.alertas)}</strong> {total.alertas === 1 ? "alerta (um padrão" : "alertas (padrões"} nos dados públicos, não
              acusações), cada um com nível de certeza e fonte oficial.{" "}
            </>
          ) : (
            <>Navegue pela lista completa de deputados federais, por estado. </>
          )}
          <Link href="/deputados">Abrir a lista de deputados por estado</Link>.
        </p>
      </section>
      <Suspense fallback={<Carregando />}>
        <Busca />
      </Suspense>
    </div>
  );
}
