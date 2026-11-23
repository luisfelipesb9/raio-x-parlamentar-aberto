"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { PaginaDeputados } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { Carregando, ErroApi, Vazio } from "./Estados";
import { DeputadoCard } from "./DeputadoCard";

const UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"];
// Sugestões (a API aceita qualquer sigla; o campo continua livre)
const PARTIDOS = ["AVANTE", "CIDADANIA", "MDB", "NOVO", "PCdoB", "PDT", "PL", "PODE", "PP", "PSB", "PSD", "PSDB", "PSOL", "PT", "PV", "REDE", "REPUBLICANOS", "SOLIDARIEDADE", "UNIÃO"];
const POR_PAGINA = 24;

export function Busca() {
  const router = useRouter();
  const sp = useSearchParams();
  const qUrl = sp.get("q") ?? "";
  const uf = sp.get("uf") ?? "";
  const partido = sp.get("partido") ?? "";
  const pagina = Math.max(1, Number(sp.get("page") ?? "1") || 1);

  const [q, setQ] = useState(qUrl);
  const [part, setPart] = useState(partido);
  const ultimaUrl = useRef(`${qUrl}|${partido}`);

  function navega(novo: Record<string, string | number>) {
    const p = new URLSearchParams(sp.toString());
    for (const [k, v] of Object.entries(novo)) {
      if (v === "" || v === 1) p.delete(k);
      else p.set(k, String(v));
    }
    router.replace(p.toString() ? `/?${p.toString()}` : "/", { scroll: false });
  }

  // texto digitado -> URL (com atraso, para não consultar a cada tecla)
  useEffect(() => {
    const alvo = `${q.trim()}|${part.trim()}`;
    if (alvo === ultimaUrl.current) return;
    const t = setTimeout(() => {
      if (document.documentElement.dataset.navegando) return; // o usuário já clicou num resultado
      ultimaUrl.current = alvo;
      navega({ q: q.trim(), partido: part.trim(), page: 1 });
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- navega depende só de sp, lido na hora do disparo
  }, [q, part]);

  const { estado, recarregar } = useApi<PaginaDeputados>("/deputados", { q: qUrl, uf, partido, page: pagina, page_size: POR_PAGINA });
  const filtrando = Boolean(qUrl || uf || partido);

  return (
    <div>
      <form className="filtros" role="search" aria-label="Buscar deputados" onSubmit={(e) => e.preventDefault()}>
        <label className="campo campo-grande">
          <span className="campo-rotulo">Buscar deputado por nome</span>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ex.: Ana, Silva, Tiririca…" autoComplete="off" />
        </label>
        <label className="campo">
          <span className="campo-rotulo">Estado (UF)</span>
          <select value={uf} onChange={(e) => navega({ uf: e.target.value, page: 1 })}>
            <option value="">Todos</option>
            {UFS.map((u) => (
              <option key={u}>{u}</option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span className="campo-rotulo">Partido (sigla)</span>
          <input list="lista-partidos" value={part} onChange={(e) => setPart(e.target.value)} placeholder="Todos" autoComplete="off" />
          <datalist id="lista-partidos">
            {PARTIDOS.map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
        </label>
        {filtrando && (
          <button
            type="button"
            className="btn btn-sec"
            onClick={() => {
              setQ("");
              setPart("");
              ultimaUrl.current = "|";
              router.replace("/", { scroll: false });
            }}
          >
            Limpar filtros
          </button>
        )}
      </form>

      <div aria-live="polite" className="resultado-resumo">
        {estado.status === "ok" && (
          <p>
            {estado.data.total === 0
              ? "Nenhum resultado"
              : `${estado.data.total.toLocaleString("pt-BR")} ${estado.data.total === 1 ? "deputado" : "deputados"}${filtrando ? " encontrados" : " no total"}`}
          </p>
        )}
      </div>

      {estado.status === "carregando" && <Carregando texto="Carregando deputados…" />}
      {estado.status === "erro" && <ErroApi erro={estado.erro} onTentarDeNovo={recarregar} />}
      {estado.status === "ok" && estado.data.items.length === 0 && (
        <Vazio titulo="Nenhum deputado encontrado">
          <p>Confira a grafia (a busca ignora acentos e maiúsculas) ou limpe os filtros.</p>
        </Vazio>
      )}
      {estado.status === "ok" && estado.data.items.length > 0 && (
        <>
          <ul className="grade-deps" aria-label="Deputados">
            {estado.data.items.map((d, i) => (
              <DeputadoCard key={d.id} d={d} indice={i} />
            ))}
          </ul>
          <Paginacao pagina={estado.data.page} total={estado.data.total} porPagina={estado.data.page_size} onIr={(p) => navega({ page: p })} />
        </>
      )}
    </div>
  );
}

function Paginacao({ pagina, total, porPagina, onIr }: { pagina: number; total: number; porPagina: number; onIr: (p: number) => void }) {
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  if (paginas <= 1) return null;
  return (
    <nav className="paginacao" aria-label="Paginação">
      <button type="button" className="btn btn-sec" disabled={pagina <= 1} onClick={() => onIr(pagina - 1)}>
        ← Anterior
      </button>
      <span>
        Página {pagina} de {paginas}
      </span>
      <button type="button" className="btn btn-sec" disabled={pagina >= paginas} onClick={() => onIr(pagina + 1)}>
        Próxima →
      </button>
    </nav>
  );
}
