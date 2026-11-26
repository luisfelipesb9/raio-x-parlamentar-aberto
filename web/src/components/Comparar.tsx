"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { ComparacaoResposta, Finding, PerfilDeputado, ResumoCategoria } from "@/types/contracts";
import { formataPercentual, rotuloCategoria } from "@/lib/formato";
import { formataCf } from "@/lib/nivel";
import { TIPOS_NO } from "@/lib/grafo";
import { useApi } from "@/lib/useApi";
import { AvisoNaoAcusacao } from "./Aviso";
import { Carregando, ErroApi } from "./Estados";
import { Foto } from "./Foto";
import { PickerDeputado } from "./Picker";
import { SeloCerteza } from "./SeloCerteza";
import { Termo } from "./Termo";

export function Comparar() {
  const router = useRouter();
  const sp = useSearchParams();
  const a = sp.get("a");
  const b = sp.get("b");
  const { estado, recarregar } = useApi<ComparacaoResposta>(a && b ? "/comparar" : null, { a: a ?? undefined, b: b ?? undefined });
  const perfilA = useApi<PerfilDeputado>(a && !b ? `/deputados/${encodeURIComponent(a)}` : null);

  if (!a) {
    return (
      <div className="pagina-estreita">
        <p className="lead">Escolha o primeiro deputado.</p>
        <PickerDeputado rotulo="Nome do primeiro deputado" onEscolher={(id) => router.push(`/comparar?a=${encodeURIComponent(id)}`)} />
      </div>
    );
  }
  if (!b) {
    return (
      <div className="pagina-estreita">
        {perfilA.estado.status === "ok" && (
          <p className="contexto">
            Primeiro: <strong>{perfilA.estado.data.nome}</strong> · <Link href="/comparar">trocar</Link>
          </p>
        )}
        <p className="lead">Agora escolha o segundo deputado.</p>
        <PickerDeputado rotulo="Nome do segundo deputado" excluirId={a} onEscolher={(id) => router.push(`/comparar?a=${encodeURIComponent(a)}&b=${encodeURIComponent(id)}`)} />
      </div>
    );
  }

  if (estado.status === "carregando" || estado.status === "ocioso") return <Carregando texto="Comparando…" />;
  if (estado.status === "erro")
    return <ErroApi erro={estado.erro} onTentarDeNovo={recarregar} voltar={{ href: "/comparar", texto: "Escolher outros deputados" }} />;
  const c = estado.data;

  return (
    <div>
      <AvisoNaoAcusacao compacto />
      <div className="comp-cabecas">
        <Cabeca p={c.a} />
        <Cabeca p={c.b} />
      </div>

      <section className="secao" aria-labelledby="h-afin">
        <h2 id="h-afin">Votam parecido?</h2>
        {c.afinidade_votos ? (
          <>
            <p className="afin-num">
              <strong>{formataPercentual(c.afinidade_votos.afinidade)}</strong>
              <span> de afinidade</span>
            </p>
            <p>
              Votaram igual em <strong>{c.afinidade_votos.n_iguais}</strong> de <strong>{c.afinidade_votos.n_votacoes_comuns}</strong>{" "}
              <Termo id="votacao-nominal">votações nominais</Termo> em que os dois participaram.{" "}
              <Termo id="cf">Nível de certeza (CF)</Termo> desta comparação: <strong>{formataCf(c.afinidade_votos.cf)}</strong>
              {c.afinidade_votos.n_votacoes_comuns < 30 ? " (baixo porque são poucas votações em comum)" : ""}.
            </p>
          </>
        ) : (
          <p className="nota">Não há votações nominais suficientes em comum para calcular a afinidade.</p>
        )}
      </section>

      <section className="secao" aria-labelledby="h-cat">
        <h2 id="h-cat">Alertas por área</h2>
        {c.categorias.length === 0 ? (
          <p className="nota">Nenhum dos dois tem alertas. A ausência de alerta não quer dizer que esteja tudo certo: pode faltar dado.</p>
        ) : (
          <table className="tabela-comp">
            <caption className="visually-hidden">Maior nível de certeza por área, para cada deputado</caption>
            <thead>
              <tr>
                <th scope="col">Área</th>
                <th scope="col">{c.a.nome}</th>
                <th scope="col">{c.b.nome}</th>
              </tr>
            </thead>
            <tbody>
              {c.categorias.map((cat) => (
                <tr key={cat.categoria}>
                  <th scope="row">{rotuloCategoria(cat.categoria)}</th>
                  <td><Celula r={cat.a} /></td>
                  <td><Celula r={cat.b} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <div className="comp-colunas">
        <ListaAlertas titulo={`Alertas de ${c.a.nome}`} id={c.a.id} lista={c.findings_a} />
        <ListaAlertas titulo={`Alertas de ${c.b.nome}`} id={c.b.id} lista={c.findings_b} />
      </div>

      <section className="secao" aria-labelledby="h-comum">
        <h2 id="h-comum">O que os dois têm em comum</h2>
        {c.em_comum.length === 0 ? (
          <p className="nota">Não há ligações em comum nos dados carregados (como partido ou fornecedores).</p>
        ) : (
          <ul className="comum">
            {c.em_comum.map((n) => (
              <li key={n.id}>
                <Link href={`/grafo?centro=${encodeURIComponent(n.id)}`}>{n.rotulo}</Link> <small>{TIPOS_NO[n.tipo]?.rotulo ?? n.tipo}</small>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Cabeca({ p }: { p: PerfilDeputado }) {
  return (
    <div className="comp-cabeca">
      <Foto src={p.foto} nome={p.nome} tamanho={72} descrever />
      <div>
        <h2>
          <Link href={`/deputado/${encodeURIComponent(p.id)}`}>{p.nome}</Link>
        </h2>
        <p className="ficha-meta">
          {[p.partido, p.uf].filter(Boolean).join(" · ")} · {p.n_findings} {p.n_findings === 1 ? "alerta" : "alertas"}
        </p>
      </div>
    </div>
  );
}

function Celula({ r }: { r: ResumoCategoria | null }) {
  if (!r) return <span className="nota">sem alerta</span>;
  return (
    <span className="celula">
      <SeloCerteza nivel={r.nivel_max} />
      <small>
        {r.n_findings} {r.n_findings === 1 ? "alerta" : "alertas"} · CF {formataCf(r.cf_max)}
      </small>
    </span>
  );
}

function ListaAlertas({ titulo, id, lista }: { titulo: string; id: string; lista: Finding[] }) {
  return (
    <section className="secao" aria-label={titulo}>
      <h3>{titulo}</h3>
      {lista.length === 0 ? (
        <p className="nota">Nenhum alerta.</p>
      ) : (
        <ul className="resumo-alertas">
          {lista.map((f) => (
            <li key={f.id}>
              <SeloCerteza nivel={f.nivel} />
              <span>
                {f.conclusao}{" "}
                <Link href={`/deputado/${encodeURIComponent(id)}#alerta-${encodeURIComponent(f.id)}`}>
                  Ver na ficha<span className="visually-hidden"> o alerta {f.regra}</span>
                </Link>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
