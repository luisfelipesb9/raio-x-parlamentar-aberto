"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useId, useState } from "react";
import type { PerfilDeputado, PerguntarResposta } from "@/types/contracts";
import { OBJETIVOS } from "@/lib/formato";
import { formataCf, NIVEIS } from "@/lib/nivel";
import { montaArvore, type NoProva } from "@/lib/trilha";
import { useApi } from "@/lib/useApi";
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
          <select id={selectId} value={objetivo} onChange={(e) => setObjetivo(e.target.value)}>
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

      {resposta.estado.status === "carregando" && <Carregando texto="O sistema está raciocinando…" />}
      {resposta.estado.status === "erro" && <ErroApi erro={resposta.estado.erro} onTentarDeNovo={resposta.recarregar} />}
      {resposta.estado.status === "ok" && <Resultado r={resposta.estado.data} />}
    </div>
  );
}

function Resultado({ r }: { r: PerguntarResposta }) {
  const arvore = montaArvore(r.trilha);
  return (
    <section className="resposta" aria-label="Resposta do sistema">
      <p className="eyebrow">Resposta do sistema</p>
      <h2>{pergunta(r.objetivo)}</h2>
      <div className="resposta-cf">
        <div>
          <p className="resposta-cf-rotulo">
            <Termo id="cf">Fator de certeza (CF)</Termo>
          </p>
          <p className="resposta-cf-num">{formataCf(r.cf)}</p>
        </div>
        <div className="medidor" role="img" aria-label={`Fator de certeza ${formataCf(r.cf)} de 1,00`}>
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
        <p>Nenhuma regra se confirmou com os dados atuais.</p>
      )}
      <AvisoNaoAcusacao compacto />

      <p className="nota">
        <strong>Como ler o número:</strong> o <Termo id="cf">fator de certeza</Termo> mede o quanto o sistema confia na <em>evidência</em>, não
        o tamanho de um problema nem a resposta a um sim/não. Quando vários indícios apontam na mesma direção, as certezas se combinam
        (método do sistema MYCIN) e o resultado pode passar de 0,40 mesmo que cada indício, sozinho, seja de 0,40 ou menos.
      </p>

      <h3>Trilha da prova</h3>
      <p className="nota">
        O sistema parte da pergunta e procura quais regras poderiam responder; se uma regra depende de outra conclusão, ela vira um novo
        passo (<Termo id="guardrail">travas</Termo> incluídas). Cada linha mostra a certeza daquele passo.
      </p>
      <ul className="arvore" role="tree" aria-label="Trilha da prova">
        {arvore.map((n, i) => (
          <NoArvore key={i} no={n} nivel={1} />
        ))}
      </ul>
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

function notaLegivel(nota: string): string {
  const f = nota.match(/^finding (.+)$/);
  if (f) return `Gerou o alerta ${f[1]}.`;
  if (nota === "condições não satisfeitas") return "Os dados atuais não ativam esta regra (isso não prova que esteja tudo certo).";
  return nota;
}

function NoArvore({ no, nivel }: { no: NoProva; nivel: number }) {
  const { passo } = no;
  const confirmado = passo.cf > 0;
  return (
    <li role="treeitem" aria-level={nivel} aria-selected="false" aria-expanded={no.filhos.length > 0 ? true : undefined} className={confirmado ? "no-sim" : "no-nao"}>
      <div className="no-linha">
        <span className="no-regra">{passo.regra ?? "—"}</span>
        <span className="no-obj">{pergunta(passo.objetivo)}</span>
        <span className="no-cf">
          CF {formataCf(passo.cf)} · <strong>{confirmado ? "confirmado" : "não confirmado"}</strong>
        </span>
      </div>
      <p className="no-nota">{notaLegivel(passo.nota)}</p>
      {no.filhos.length > 0 && (
        <ul role="group">
          {no.filhos.map((f, i) => (
            <NoArvore key={i} no={f} nivel={nivel + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}
