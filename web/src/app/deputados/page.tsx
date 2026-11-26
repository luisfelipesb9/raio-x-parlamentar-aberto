import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { AvisoNaoAcusacao } from "@/components/Aviso";
import type { DeputadoResumo } from "@/types/contracts";
import { agrupaPorUf } from "@/lib/deputados-lista";
import { canonical } from "@/lib/seo";
import { nomeDaUf } from "@/lib/ufs";
import { servidorTodosDeputados } from "@/lib/server-api";

/** ISR de uma hora (literal exigido pelo Next; igualdade com REVALIDAR_SEGUNDOS é checada em isr-literal.test.ts). */
export const revalidate = 3600;

const DESCRICAO =
  "Lista de todos os deputados federais da base do Raio-X Parlamentar, por estado, com link para a ficha de cada um em linguagem simples.";

export const metadata: Metadata = {
  title: "Deputados federais por estado",
  description: DESCRICAO,
  alternates: canonical("/deputados"),
  openGraph: { title: "Deputados federais por estado", description: DESCRICAO, url: canonical("/deputados").canonical, locale: "pt_BR" },
};

/**
 * Sem API (ou com lista vazia, banco ainda sem carga) não há o que listar: tratado como falha.
 * Em requisição, o erro sobe para o error.tsx (nada fica em cache). No `next build` (CI sem API),
 * `connection()` tira a página do pré-render: ela não quebra o build nem congela "0 deputados" por 1 h;
 * vira dinâmica nesse build. Com API e dados no build, sai estática com ISR.
 */
async function carrega(): Promise<DeputadoResumo[]> {
  try {
    const lista = await servidorTodosDeputados<DeputadoResumo>();
    if (lista.length === 0) throw new Error("A API devolveu a lista de deputados vazia");
    return lista;
  } catch (e) {
    await connection();
    throw e;
  }
}

/** Rótulo acessível do link do índice: contém a sigla visível (WCAG 2.5.3) e o nome por extenso. */
function rotuloUf(uf: string): string | undefined {
  const nome = nomeDaUf(uf);
  return nome ? `${nome} (${uf})` : undefined;
}

export default async function ListaDeputados() {
  const deputados = await carrega();
  const grupos = agrupaPorUf(deputados);

  return (
    <div className="pagina">
      <h1>Deputados federais</h1>
      <p className="lead">
        Todos os {deputados.length} deputados federais que estão na base, organizados por estado em ordem alfabética. Abra uma ficha para ver, em
        linguagem simples, como a pessoa vota, quanto gasta e de onde vem o dinheiro, sempre com o nível de certeza e o link para a fonte oficial.
      </p>
      <AvisoNaoAcusacao compacto />

      <nav aria-label="Ir para um estado" className="uf-indice">
        <ul className="acoes acoes-lista">
          {grupos.map((g) => (
            <li key={g.uf}>
              <a href={`#uf-${encodeURIComponent(g.uf)}`} aria-label={rotuloUf(g.uf)}>
                {g.uf}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {grupos.map((g) => (
        <section key={g.uf} id={`uf-${encodeURIComponent(g.uf)}`} aria-labelledby={`h-uf-${encodeURIComponent(g.uf)}`}>
          <h2 id={`h-uf-${encodeURIComponent(g.uf)}`}>
            {g.uf} <small>({g.deputados.length})</small>
          </h2>
          <ul className="grade-deps">
            {g.deputados.map((d) => (
              <li key={d.id} className="dep-card">
                <div className="dep-card-txt">
                  <Link className="dep-card-link" href={`/deputado/${encodeURIComponent(d.id)}`} prefetch={false}>
                    {d.nome}
                  </Link>
                  <span className="dep-card-meta">{d.partido ?? "Partido não informado"}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
