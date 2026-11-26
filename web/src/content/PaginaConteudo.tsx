import Link from "next/link";
import type { ReactNode } from "react";
import { AvisoNaoAcusacao } from "@/components/Aviso";
import { JsonLd } from "@/components/JsonLd";
import "./conteudo.css";

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];

/** "2026-11-20" -> "20 de novembro de 2026" (sem fuso nem Intl: a saída é sempre a mesma). `null` se a data não existir. */
export function dataPorExtenso(iso: string): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return null;
  const [ano, mes, dia] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const d = new Date(Date.UTC(ano, mes - 1, dia));
  if (d.getUTCFullYear() !== ano || d.getUTCMonth() !== mes - 1 || d.getUTCDate() !== dia) return null;
  return `${dia} de ${MESES[mes - 1]} de ${ano}`;
}

export type Migalha = { nome: string; caminho: string };

type Props = {
  titulo: string;
  resposta: string;
  /** AAAA-MM-DD; sem data, a linha "Atualizado em" não aparece. */
  atualizado?: string;
  /** Do início até a página atual (a última não é link). */
  migalhas: Migalha[];
  jsonld: unknown[];
  vejaTambem?: Migalha[];
  children?: ReactNode;
};

/** Moldura comum das páginas de conteúdo: H1, resposta em destaque, data, breadcrumb, aviso e links internos. */
export function PaginaConteudo({ titulo, resposta, atualizado, migalhas, jsonld, vejaTambem = [], children }: Props) {
  const data = atualizado ? dataPorExtenso(atualizado) : null;
  return (
    <div className="pagina pagina-estreita">
      {jsonld.map((d, i) => (
        <JsonLd key={i} data={d} />
      ))}
      <nav aria-label="Você está em" className="migalhas">
        <ol>
          {migalhas.map((m, i) => (
            <li key={m.caminho}>{i === migalhas.length - 1 ? <span aria-current="page">{m.nome}</span> : <Link href={m.caminho}>{m.nome}</Link>}</li>
          ))}
        </ol>
      </nav>
      <h1>{titulo}</h1>
      <p className="resposta-destaque">{resposta}</p>
      {data && atualizado && (
        <p className="atualizado">
          Atualizado em <time dateTime={atualizado}>{data}</time>
        </p>
      )}
      <AvisoNaoAcusacao compacto />
      <div className="conteudo-corpo">{children}</div>
      {vejaTambem.length > 0 && (
        <nav aria-labelledby="veja-tambem" className="veja-tambem">
          <h2 id="veja-tambem">Veja também</h2>
          <ul>
            {vejaTambem.map((l) => (
              <li key={l.caminho}>
                <Link href={l.caminho}>{l.nome}</Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </div>
  );
}
