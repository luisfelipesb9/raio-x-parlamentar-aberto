"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import type { PerfilDeputado, PerguntarResposta } from "@/types/contracts";
import { OBJETIVOS } from "@/lib/formato";
import { resumoDiagnosticos, type ProximoPasso } from "@/lib/diagnostico";
import { movimentoReduzido } from "@/lib/movimento";
import { formataCf, NIVEIS } from "@/lib/nivel";
import { useApi } from "@/lib/useApi";
import { ArvoreProva } from "./ArvoreProva";
import { AvisoNaoAcusacao } from "./Aviso";
import { Carregando, ErroApi } from "./Estados";
import { PickerDeputado } from "./Picker";
import { SeloCerteza } from "./SeloCerteza";
import { Termo } from "./Termo";

const pergunta = (id: string) => OBJETIVOS.find((o) => o.id === id)?.pergunta ?? id.replaceAll("_", " ");

export function Perguntar() {
  const router = useRouter();
  const sp = useSearchParams();
  const deputado = sp.get("deputado");
  const objetivoUrl = sp.get("objetivo");
  const [objetivo, setObjetivo] = useState(OBJETIVOS.some((o) => o.id === objetivoUrl) ? (objetivoUrl as string) : OBJETIVOS[0]!.id);
  const [feita, setFeita] = useState<string | null>(OBJETIVOS.some((o) => o.id === objetivoUrl) ? (objetivoUrl as string) : null);
  const selectId = useId();
  const selectRef = useRef<HTMLSelectElement>(null);
  /** Quantas vezes a pessoa apertou "Perguntar": só então a resposta recebe foco (nunca ao abrir a página). */
  const [pedido, setPedido] = useState(0);

  const perfil = useApi<PerfilDeputado>(deputado ? `/deputados/${encodeURIComponent(deputado)}` : null);
  const resposta = useApi<PerguntarResposta>(deputado && feita ? "/perguntar" : null, { deputado: deputado ?? undefined, objetivo: feita ?? undefined });

  if (!deputado) {
    return (
      <div className="pagina-estreita">
        <p className="lead">Primeiro, escolha de qual deputado você quer saber.</p>
        <PickerDeputado onEscolher={(id) => router.push(`/perguntar?deputado=${encodeURIComponent(id)}`)} />
      </div>
    );
  }

  function enviar(e: React.FormEvent) {
    e.preventDefault();
    setFeita(objetivo);
    setPedido((n) => n + 1);
    const p = new URLSearchParams(sp.toString());
    p.set("objetivo", objetivo);
    router.replace(`/perguntar?${p.toString()}`, { scroll: false });
  }

  return (
    <div>
      {perfil.estado.status === "erro" && <ErroApi erro={perfil.estado.erro} onTentarDeNovo={perfil.recarregar} voltar={{ href: "/perguntar", texto: "Escolher outro deputado" }} />}
      {perfil.estado.status === "ok" && (
        <p className="contexto">
          Deputado(a): <Link href={`/deputado/${encodeURIComponent(deputado)}`}><strong>{perfil.estado.data.nome}</strong></Link> ·{" "}
          <Link href="/perguntar">trocar</Link>
        </p>
      )}
      <form className="form-perguntar" onSubmit={enviar}>
        <div className="campo">
          <label className="campo-rotulo" htmlFor={selectId}>O que você quer saber?</label>
          <select id={selectId} ref={selectRef} value={objetivo} onChange={(e) => setObjetivo(e.target.value)}>
            {OBJETIVOS.map((o) => (
              <option key={o.id} value={o.id}>
                {o.pergunta}
              </option>
            ))}
          </select>
          <span className="campo-ajuda">{OBJETIVOS.find((o) => o.id === objetivo)?.ajuda}</span>
        </div>
        <button type="submit" className="btn">
          Perguntar
        </button>
      </form>

      <p className="visually-hidden" role="status" aria-live="polite" aria-atomic="true">
        {resposta.estado.status === "ok"
          ? `Resposta pronta: ${pergunta(resposta.estado.data.objetivo)} Nível de certeza ${formataCf(resposta.estado.data.cf)} de 1, ${NIVEIS[resposta.estado.data.nivel].rotulo}.`
          : ""}
      </p>
      {resposta.estado.status === "carregando" && <Carregando texto="O sistema está raciocinando…" />}
      {resposta.estado.status === "erro" && <ErroApi erro={resposta.estado.erro} onTentarDeNovo={resposta.recarregar} />}
      {resposta.estado.status === "ok" && <Resultado r={resposta.estado.data} pedido={pedido} aoPerguntarOutra={() => selectRef.current?.focus()} />}
    </div>
  );
}

function Resultado({ r, pedido, aoPerguntarOutra }: { r: PerguntarResposta; pedido: number; aoPerguntarOutra: () => void }) {
  const bloco = useRef<HTMLElement>(null);
  useEffect(() => {
    if (pedido === 0 || !bloco.current) return;
    bloco.current.focus({ preventScroll: true });
    bloco.current.scrollIntoView({ block: "start", behavior: movimentoReduzido() ? "auto" : "smooth" });
  }, [pedido]);
  const semConclusao = r.regras_usadas.length === 0 ? resumoDiagnosticos(r.trilha) : null;
  return (
    <section ref={bloco} tabIndex={-1} className="resposta" aria-label="Resposta do sistema">
      <p className="eyebrow">Resposta do sistema</p>
      <h2>{pergunta(r.objetivo)}</h2>
      <div className="resposta-cf">
        <div>
          <p className="resposta-cf-rotulo">
            <Termo id="cf">Nível de certeza (CF)</Termo>
          </p>
          <p className="resposta-cf-num">{formataCf(r.cf)}</p>
        </div>
        <div className="medidor" role="img" aria-label={`Nível de certeza ${formataCf(r.cf)} de 1,00`}>
          <span style={{ width: `${Math.max(0, Math.min(1, r.cf)) * 100}%` }} />
        </div>
        <SeloCerteza nivel={r.nivel} />
      </div>
      <p className="resposta-explica">{NIVEIS[r.nivel].explicacao}</p>
      {r.regras_usadas.length > 0 ? (
        <p>
          Regras que sustentam a resposta: <strong>{r.regras_usadas.join(", ")}</strong>.
        </p>
      ) : (
        <SemConclusao frases={semConclusao?.frases ?? []} proximos={semConclusao?.proximos ?? ["outra-pergunta", "cobertura"]} aoPerguntarOutra={aoPerguntarOutra} />
      )}
      <AvisoNaoAcusacao compacto />

      <p className="nota">
        <strong>Como ler o número:</strong> o <Termo id="cf">nível de certeza</Termo> (também chamado fator de certeza, CF) mede o quanto o sistema confia na <em>evidência</em>, não
        o tamanho de um problema nem a resposta a um sim/não. Quando vários indícios apontam na mesma direção, as certezas se combinam
        (método do sistema MYCIN) e o resultado pode passar de 0,40 mesmo que cada indício, sozinho, seja de 0,40 ou menos.
      </p>

      <h3>Trilha da prova</h3>
      <p className="nota">
        O sistema parte da pergunta e procura quais regras poderiam responder; se uma regra depende de outra conclusão, ela vira um novo
        passo (<Termo id="guardrail">travas</Termo> incluídas). Cada linha mostra a certeza daquele passo. Com o teclado, use as setas para percorrer a trilha e as setas direita e esquerda para abrir e fechar um passo.
      </p>
      <ArvoreProva trilha={r.trilha} />
      {r.trilha.filter((p) => p.cf > 0).length >= 2 && (
        <p className="nota">
          Mais de uma regra confirmou a conclusão. O sistema combina as certezas (como no sistema MYCIN), por isso o resultado final pode ser
          maior do que o de cada regra isolada.
        </p>
      )}

      {r.finding_ids.length > 0 && (
        <p>
          Alertas usados:{" "}
          {r.finding_ids.map((id, i) => (
            <span key={id}>
              {i > 0 && ", "}
              <Link href={`/deputado/${encodeURIComponent(r.deputado_id)}#alerta-${encodeURIComponent(id)}`}>{id}</Link>
            </span>
          ))}
        </p>
      )}
    </section>
  );
}

/** Quando nenhuma regra se confirmou: diz o motivo concreto e o que a pessoa pode fazer em seguida. */
function SemConclusao({ frases, proximos, aoPerguntarOutra }: { frases: string[]; proximos: ProximoPasso[]; aoPerguntarOutra: () => void }) {
  return (
    <div className="sem-conclusao">
      <h3>Por que o sistema não concluiu</h3>
      {frases.length > 0 ? (
        <ul>
          {frases.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      ) : (
        <p>Nenhuma regra se confirmou com os dados atuais.</p>
      )}
      <p className="sem-conclusao-rotulo">O que fazer agora:</p>
      <div className="acoes">
        {proximos.map((p) =>
          p === "cobertura" ? (
            <Link key={p} className="btn btn-sec" href="/fontes">
              Ver a cobertura dos dados
            </Link>
          ) : (
            <button key={p} type="button" className="btn btn-sec" onClick={aoPerguntarOutra}>
              Fazer outra pergunta
            </button>
          ),
        )}
      </div>
    </div>
  );
}
