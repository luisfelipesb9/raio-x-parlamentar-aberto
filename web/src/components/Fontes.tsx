"use client";

import Link from "next/link";
import type { CoberturaResposta } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { formataData, formataTeto, listaTipos, nivelMaximoR01, rotuloFonte } from "@/lib/verificacao";
import { AvisoNaoAcusacao } from "./Aviso";
import { Carregando, ErroApi } from "./Estados";
import { ResumoJanela } from "./PainelDados";
import { Termo } from "./Termo";

const fmtInt = new Intl.NumberFormat("pt-BR");

/** Página "Fontes e método": o que a base cobre (vindo da API) e como o sistema chega às conclusões. */
export function Fontes() {
  const { estado, recarregar } = useApi<CoberturaResposta>("/cobertura");
  return (
    <>
      <AvisoNaoAcusacao />

      <section className="bloco-pagina" aria-labelledby="h-cobertura">
        <h2 id="h-cobertura">O que a base tem hoje</h2>
        {(estado.status === "carregando" || estado.status === "ocioso") && <Carregando texto="Carregando a cobertura dos dados…" />}
        {estado.status === "erro" && <ErroApi erro={estado.erro} onTentarDeNovo={recarregar} voltar={{ href: "/", texto: "Voltar à busca" }} />}
        {estado.status === "ok" && <Cobertura c={estado.data} />}
      </section>

      <Metodo c={estado.status === "ok" ? estado.data : null} carregando={estado.status === "carregando" || estado.status === "ocioso"} />

      <section className="bloco-pagina" aria-labelledby="h-conferir">
        <h2 id="h-conferir">Como conferir por conta própria</h2>
        <ol className="passos-conferir">
          <li>
            Em cada alerta da ficha, abra <strong>Verificar na fonte</strong>: ali estão o link oficial, o identificador do registro e a data em
            que o dado foi coletado.
          </li>
          <li>
            Na ficha, o painel <strong>Dados e verificação</strong> mostra os números por trás de cada regra, para refazer a conta.
          </li>
          <li>
            Quem roda o projeto pode usar o comando <code>make verifica</code>. Ele recalcula, direto dos arquivos baixados e sem usar o motor
            de regras, o alinhamento com o governo e o total de gastos da cota de cada deputado, e compara com o que está no banco. O resultado
            fica no arquivo <code>docs/relatorio/verificacao.md</code>.
          </li>
        </ol>
      </section>
    </>
  );
}

function Cobertura({ c }: { c: CoberturaResposta }) {
  return (
    <>
      <p>
        A base atual tem <strong>{fmtInt.format(c.n_deputados)}</strong> {c.n_deputados === 1 ? "deputado" : "deputados"} e{" "}
        <strong>{fmtInt.format(c.n_findings)}</strong> {c.n_findings === 1 ? "alerta" : "alertas"} gerados pelo sistema. Não é a Câmara inteira:
        um deputado fora da base não aparece em nenhuma tela.
      </p>
      <ResumoJanela janela={c.janela_votos} />

      <table className="tabela-fontes">
        <caption>
          Fontes oficiais usadas. As datas são de quando o sistema coletou o dado (horário de Brasília), não de quando o fato aconteceu.
        </caption>
        <thead>
          <tr>
            <th scope="col">Fonte</th>
            <th scope="col">O que traz</th>
            <th scope="col">Registros</th>
            <th scope="col">Coletado de</th>
            <th scope="col">Coletado até</th>
          </tr>
        </thead>
        <tbody>
          {c.fontes.map((f) => (
            <tr key={f.fonte}>
              <th scope="row">{rotuloFonte(f.fonte)}</th>
              <td data-rotulo="O que traz">{listaTipos(f.tipos)}</td>
              <td data-rotulo="Registros">{fmtInt.format(f.n_fatos)}</td>
              <td data-rotulo="Coletado de">{formataData(f.coletado_em_min)}</td>
              <td data-rotulo="Coletado até">{formataData(f.coletado_em_max)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function Metodo({ c, carregando }: { c: CoberturaResposta | null; carregando: boolean }) {
  const nOrientadas = c?.janela_votos.n_votacoes_com_orientacao ?? null;
  const maximo = nOrientadas === null ? null : nivelMaximoR01(nOrientadas);
  const limitado = maximo !== null && maximo < 0.95;
  return (
    <section className="bloco-pagina" aria-labelledby="h-metodo">
      <h2 id="h-metodo">Como o sistema chega às conclusões</h2>
      <p>
        O sistema é um <em>sistema especialista</em>: uma base de regras escritas por pessoas (por exemplo, &ldquo;se o deputado votou com o governo em
        pelo menos 70% das votações em que o governo orientou, então o alinhamento é alto&rdquo;) aplicadas aos dados públicos. Ele não adivinha nem
        usa opinião: cada conclusão aponta a regra, os dados e o link da fonte.
      </p>
      <p>
        Cada conclusão sai com um <Termo id="cf">nível de certeza</Termo> de 0 a 1. Ele cai quando faltam dados, quando a amostra é pequena ou quando
        a identificação de uma pessoa ou empresa não é segura. <Termo id="guardrail">Travas de segurança</Termo> impedem conclusões que os dados não
        permitem (processo sem condenação definitiva não é culpa, votação simbólica não é voto individual).
      </p>
      <h3>Por que o nível de certeza tem um teto{maximo === null ? "" : ` (${formataTeto(maximo)} na regra de alinhamento)`}</h3>
      {maximo !== null && nOrientadas !== null ? (
        <p>
          A regra de alinhamento com o governo (R01) parte de 0,95. Com menos de 30 votações em que o governo orientou, ela reduz a certeza em 30%
          (fator 0,7). A janela atual tem <strong>{nOrientadas}</strong> dessas votações, então o <Termo id="nivel-certeza-maximo">nível de certeza máximo</Termo>{" "}
          é <strong>{formataTeto(maximo)}</strong>{limitado ? ": nenhum deputado passa disso, por mais claro que seja o padrão." : "."}{" "}
          {limitado && (
            <>
              Ampliar a janela de votação é possível: coletar mais votações nominais eleva o teto até 0,95, sem mudar nenhuma regra.
            </>
          )}
        </p>
      ) : carregando ? (
        <Carregando texto="Carregando a janela de votação…" />
      ) : (
        <p>Os números da janela atual não puderam ser carregados. Tente de novo em instantes.</p>
      )}
      <p>
        Para entender cada termo, veja o <Link href="/glossario">glossário</Link>.
      </p>
    </section>
  );
}
