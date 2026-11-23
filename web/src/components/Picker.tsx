"use client";

import { useEffect, useState } from "react";
import type { PaginaDeputados } from "@/types/contracts";
import { useApi } from "@/lib/useApi";
import { Carregando, ErroApi, Vazio } from "./Estados";
import { Foto } from "./Foto";

/** Busca um deputado pelo nome e devolve o id escolhido (usado em grafo, perguntar e comparar). */
export function PickerDeputado({ rotulo = "Nome do deputado", onEscolher, excluirId }: { rotulo?: string; onEscolher: (id: string, nome: string) => void; excluirId?: string }) {
  const [q, setQ] = useState("");
  const [qDeb, setQDeb] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setQDeb(q.trim()), 250);
    return () => clearTimeout(t);
  }, [q]);

  const { estado, recarregar } = useApi<PaginaDeputados>(qDeb.length >= 2 ? "/deputados" : null, { q: qDeb, page_size: 8 });

  return (
    <div className="picker">
      <label className="campo">
        <span className="campo-rotulo">{rotulo}</span>
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Digite ao menos 2 letras" autoComplete="off" />
      </label>
      <div aria-live="polite">
        {estado.status === "carregando" && <Carregando texto="Buscando…" />}
        {estado.status === "erro" && <ErroApi erro={estado.erro} onTentarDeNovo={recarregar} />}
        {estado.status === "ok" && estado.data.items.length === 0 && <Vazio titulo="Nenhum deputado encontrado" />}
        {estado.status === "ok" && estado.data.items.length > 0 && (
          <ul className="picker-lista" aria-label="Resultados da busca">
            {estado.data.items
              .filter((d) => d.id !== excluirId)
              .map((d) => (
                <li key={d.id}>
                  <button type="button" onClick={() => onEscolher(d.id, d.nome)}>
                    <Foto src={d.foto} nome={d.nome} tamanho={36} />
                    <span>
                      {d.nome}
                      <small>{[d.partido, d.uf].filter(Boolean).join(" · ")}</small>
                    </span>
                  </button>
                </li>
              ))}
          </ul>
        )}
      </div>
    </div>
  );
}
