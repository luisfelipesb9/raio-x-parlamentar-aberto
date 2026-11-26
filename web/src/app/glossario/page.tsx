import type { Metadata } from "next";
import Link from "next/link";
import { JsonLd } from "@/components/JsonLd";
import { termosLd } from "@/lib/jsonld";
import { canonical } from "@/lib/seo";
import { GLOSSARIO } from "@/lib/glossario";

export const metadata: Metadata = {
  title: "Glossário",
  description: "CEAP, votação nominal, emenda Pix, nível de certeza e outros termos das fichas dos deputados, explicados em palavras simples.",
  alternates: canonical("/glossario"),
};

export default function Glossario() {
  return (
    <div className="pagina pagina-estreita">
      <JsonLd data={termosLd(GLOSSARIO)} />
      <p className="eyebrow">Para não se perder nos termos</p>
      <h1>Glossário</h1>
      <p className="lead">Os termos que aparecem sublinhados nas fichas, explicados em poucas palavras.</p>
      <dl className="glossario">
        {GLOSSARIO.map((t) => (
          <div key={t.id} id={t.id} className="glossario-item">
            <dt>{t.termo}</dt>
            <dd>
              {t.definicao}
              {t.porQueImporta && <span className="glossario-importa"> {t.porQueImporta}</span>}{" "}
              <Link href={`/glossario/${t.id}`} aria-label={`Página do termo ${t.termo}`}>
                Página do termo
              </Link>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
