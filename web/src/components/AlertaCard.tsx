"use client";

import { useId, useState } from "react";
import type { Explanation, Finding } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { formataCf } from "@/lib/nivel";
import { rotuloCategoria, rotuloEvidencia } from "@/lib/formato";
import { urlSegura } from "@/lib/url";
import { Carregando, ErroApi } from "./Estados";
import { SeloCerteza } from "./SeloCerteza";
import { Termo } from "./Termo";

const EVIDENCIAS_VISIVEIS = 5;

function Trilha({ finding, titulo }: { finding: Finding; titulo: string }) {
  const { estado, recarregar } = useApi<Explanation>(`/findings/${encodeURIComponent(finding.id)}/explicar`);
  const [todas, setTodas] = useState(false);

  if (estado.status === "carregando" || estado.status === "ocioso") return <Carregando texto="Buscando o passo a passo…" />;
  if (estado.status === "erro") return <ErroApi erro={estado.erro} onTentarDeNovo={recarregar} />;
  const ex = estado.data;
  const evid = todas ? finding.evidencias : finding.evidencias.slice(0, EVIDENCIAS_VISIVEIS);

  return (
    <div className="trilha-corpo">
      <h4>Passo a passo: como chegamos a esta conclusão</h4>
      <ol className="trilha-passos" aria-label={`Passos que levaram a: ${titulo}`}>
        {ex.como.map((p, i) => (
          <li key={i} className={p.resultado ? "passo-sim" : "passo-nao"}>
            <span className="passo-regra">{p.regra}</span>
            <div>
              <p className="passo-detalhe">{p.detalhe ?? (p.condicao === "guardrail" ? "Trava de segurança aplicada." : p.condicao)}</p>
              <p className="passo-cond">
                {p.condicao === "guardrail" ? "Trava de segurança" : p.condicao === "penalidade" ? "Redução da certeza" : "Condição"}
                {p.condicao !== "guardrail" && p.condicao !== "penalidade" && <code>{p.condicao}</code>}
                {" · "}
                <strong>{p.resultado ? "satisfeita" : "não satisfeita"}</strong>
              </p>
            </div>
          </li>
        ))}
      </ol>

      {finding.guardrails_aplicados.length > 0 && (
        <p className="trilha-guardrails">
          <strong>
            Travas de segurança (<Termo id="guardrail">guardrails</Termo>) aplicadas:
          </strong>{" "}
          {finding.guardrails_aplicados.join(", ")}. Elas impedem o sistema de concluir mais do que os dados permitem.
        </p>
      )}

      <h4>Por que isso importa</h4>
      <p>{ex.por_que}</p>

      <h4>Limitações</h4>
      {ex.limitacoes.length > 0 ? (
        <ul>
          {ex.limitacoes.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      ) : (
        <p>Nenhuma limitação específica registrada para esta regra.</p>
      )}

      <h4>Documentos oficiais ({finding.evidencias.length})</h4>
      {finding.evidencias.length === 0 ? (
        <p>Esta conclusão não tem documento individual associado.</p>
      ) : (
        <>
          <ul className="trilha-evidencias">
            {evid.map((e) => {
              const href = urlSegura(e.url);
              return (
              <li key={`${e.tipo}-${e.id_oficial}`}>
                {href ? (
                  <a href={href} target="_blank" rel="noopener noreferrer">
                    Abrir na fonte: {rotuloEvidencia(e.tipo).toLowerCase()} {e.id_oficial}
                    <span className="visually-hidden"> (abre em nova aba)</span>
                  </a>
                ) : (
                  <span>
                    {rotuloEvidencia(e.tipo)} {e.id_oficial} (sem link público)
                  </span>
                )}
                {e.descricao && <span className="evid-desc"> — {e.descricao}</span>}
              </li>
              );
            })}
          </ul>
          {finding.evidencias.length > EVIDENCIAS_VISIVEIS && (
            <button type="button" className="btn btn-sec btn-mini" onClick={() => setTodas((t) => !t)}>
              {todas ? "Mostrar menos" : `Mostrar todos os ${finding.evidencias.length}`}
            </button>
          )}
        </>
      )}
    </div>
  );
}

export function AlertaCard({ finding }: { finding: Finding }) {
  const [aberto, setAberto] = useState(false);
  const painelId = useId();
  const tituloId = useId();

  return (
    <article className="alerta holo luz" id={`alerta-${finding.id}`} aria-labelledby={tituloId}>
      <header className="alerta-topo">
        <span className="alerta-cat">
          {rotuloCategoria(finding.categoria)} · regra {finding.regra}
        </span>
        <SeloCerteza nivel={finding.nivel} />
      </header>
      <h3 id={tituloId} className="alerta-conclusao">
        {finding.conclusao}
      </h3>
      <p className="alerta-cf">
        <Termo id="cf">Nível de certeza (CF)</Termo>: <strong>{formataCf(finding.cf)}</strong> de 1,00
      </p>
      <p className="alerta-aviso">Isto não é acusação; é o que os dados públicos mostram.</p>
      <button type="button" className="btn" aria-expanded={aberto} aria-controls={painelId} onClick={() => setAberto((a) => !a)}>
        Como sabemos disso?
      </button>
      {aberto && (
        <section id={painelId} className="trilha" aria-label={`Como sabemos disso? Regra ${finding.regra}`}>
          <Trilha finding={finding} titulo={finding.conclusao} />
        </section>
      )}
    </article>
  );
}
