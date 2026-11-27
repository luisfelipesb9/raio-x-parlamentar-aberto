"use client";

import type { PaginaDeputados } from "@/types/contracts";
import { OBJETIVOS } from "@/lib/formato";
import { RELACOES } from "@/lib/grafo";
import { NIVEIS } from "@/lib/nivel";
import { useApi } from "@/lib/useApi";
import { Contador } from "./Contador";

/** Tira de números. Só dado real (total vindo da API) ou fato estrutural do sistema, rotulado como tal. */
export function Numeros({ totalInicial = null }: { totalInicial?: number | null }) {
  const { estado } = useApi<PaginaDeputados>("/deputados", { page_size: 1 });
  // o total do servidor (ISR) já vem no HTML; o cliente só o atualiza quando a API responde
  const total = estado.status === "ok" ? estado.data.total : totalInicial;
  const itens: { valor: number | null; rotulo: string }[] = [
    { valor: total, rotulo: "deputados na base" },
    { valor: OBJETIVOS.length, rotulo: "perguntas que o sistema sabe responder" },
    { valor: RELACOES.length, rotulo: "tipos de relação no mapa" },
    { valor: Object.keys(NIVEIS).length, rotulo: "níveis de certeza, sempre em texto" },
  ];
  return (
    <ul className="numeros" aria-label="O sistema em números">
      {itens.map((i) => (
        <li key={i.rotulo}>
          <span className="numeros-valor">{i.valor !== null ? (
              <Contador valor={i.valor} />
            ) : estado.status === "erro" ? (
              <span className="numeros-indisp">indisponível</span>
            ) : (
              <span aria-hidden="true">—</span>
            )}</span>
          <span className="numeros-rotulo">{i.rotulo}</span>
        </li>
      ))}
    </ul>
  );
}
