import type { Metadata } from "next";
import { GLOSSARIO } from "@/lib/glossario";

export const metadata: Metadata = { title: "Glossário" };

export default function Glossario() {
  return (
    <div className="pagina pagina-estreita">
      <p className="eyebrow">Para não se perder nos termos</p>
      <h1>Glossário</h1>
      <p className="lead">Os termos que aparecem sublinhados nas fichas, explicados em poucas palavras.</p>
      <dl className="glossario">
        {GLOSSARIO.map((t) => (
          <div key={t.id} id={t.id} className="glossario-item">
            <dt>{t.termo}</dt>
            <dd>
              {t.definicao}
              {t.porQueImporta && <span className="glossario-importa"> {t.porQueImporta}</span>}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
