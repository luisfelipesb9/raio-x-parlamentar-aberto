"use client";

import Link from "next/link";
import type { CoberturaResposta, JanelaVotos, MetricasDeputadoResposta } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { formataData, linhasMetricas, nomeRegra, periodoColeta, rotuloFonte } from "@/lib/verificacao";
import { Carregando, ErroApi } from "./Estados";
import { Termo } from "./Termo";

/** Quantas votações e de que período entraram na conta. As datas vêm da API, nunca fixas no código. */
export function ResumoJanela({ janela }: { janela: JanelaVotos }) {
  if (janela.n_votacoes === 0) return <p>A base ainda não tem votações carregadas.</p>;
  return (
    <p>
      A <Termo id="janela-votacao">janela de votação</Termo> vai de <strong>{formataData(janela.inicio)}</strong> a{" "}
      <strong>{formataData(janela.fim)}</strong>: {janela.n_votacoes} votações, das quais {janela.n_votacoes_nominais} nominais e{" "}
      {janela.n_votacoes_com_orientacao} com orientação do governo (as únicas que entram na conta do alinhamento).
    </p>
  );
}

/** Painel "Dados e verificação" da ficha: o que a base cobre, os números por trás de cada regra e de onde vem cada fonte. */
export function PainelDados({ deputadoId }: { deputadoId: string }) {
  const metricas = useApi<MetricasDeputadoResposta>(`/deputados/${encodeURIComponent(deputadoId)}/metricas`);
  const cobertura = useApi<CoberturaResposta>("/cobertura");

  return (
    <div className="painel-dados">
      <p>
        Aqui está o que o sistema tinha em mãos para este deputado e de onde veio cada dado, para você conferir por conta própria. A{" "}
        <Termo id="cobertura-dados">cobertura</Termo> pequena de uma fonte pode explicar a ausência de alertas.
      </p>

      {metricas.estado.status === "carregando" && <Carregando texto="Carregando os números da análise…" />}
      {metricas.estado.status === "erro" && <ErroApi erro={metricas.estado.erro} onTentarDeNovo={metricas.recarregar} />}
      {metricas.estado.status === "ok" && <BlocoVotos m={metricas.estado.data} />}
      {metricas.estado.status === "ok" && <BlocoMetricas m={metricas.estado.data} />}

      <h3 className="bloco-titulo">De onde vêm os dados</h3>
      {cobertura.estado.status === "carregando" && <Carregando texto="Carregando as fontes…" />}
      {cobertura.estado.status === "erro" && <ErroApi erro={cobertura.estado.erro} onTentarDeNovo={cobertura.recarregar} />}
      {cobertura.estado.status === "ok" && (
        <>
          <ul className="fontes-lista">
            {cobertura.estado.data.fontes.map((f) => (
              <li key={f.fonte}>
                <span>{rotuloFonte(f.fonte)}</span>
                <span className="fonte-data">coletado {periodoColeta(f.coletado_em_min, f.coletado_em_max)}</span>
              </li>
            ))}
          </ul>
          <p>
            <Link href="/fontes">Ver todas as fontes e como o sistema funciona</Link>
          </p>
        </>
      )}
    </div>
  );
}

function BlocoVotos({ m }: { m: MetricasDeputadoResposta }) {
  return (
    <>
      <h3 className="bloco-titulo">Votações usadas</h3>
      <ResumoJanela janela={m.janela_votos} />
      <p>
        Deste deputado há <strong>{m.n_votos}</strong> {m.n_votos === 1 ? "voto" : "votos"} em votação nominal; <strong>{m.n_votos_validos}</strong>{" "}
        {m.n_votos_validos === 1 ? "é" : "são"} <Termo id="votos-validos">{m.n_votos_validos === 1 ? "voto válido" : "votos válidos"}</Termo> para o cálculo
        do alinhamento com o governo.
      </p>
    </>
  );
}

function BlocoMetricas({ m }: { m: MetricasDeputadoResposta }) {
  const comNumeros = m.metricas_por_regra.filter((r) => Object.keys(r.valores).length > 0);
  return (
    <>
      <h3 className="bloco-titulo">Números por trás de cada regra</h3>
      {comNumeros.length === 0 ? (
        <p className="nota">Nenhuma regra gerou números para este deputado com os dados atuais. Isso não prova nada: pode faltar dado.</p>
      ) : (
        <div className="metricas-regras">
          {comNumeros.map((r) => (
            <section key={r.regra} className="metrica-regra" aria-label={`Números da regra ${r.regra}`}>
              <h4>
                {nomeRegra(r.regra)} <span className="metrica-id">regra {r.regra}</span>
              </h4>
              <dl className="metricas">
                {linhasMetricas(r.valores).map((l) => (
                  <div key={l.chave}>
                    <dt>{l.rotulo}</dt>
                    <dd>{l.valor}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      )}
    </>
  );
}
