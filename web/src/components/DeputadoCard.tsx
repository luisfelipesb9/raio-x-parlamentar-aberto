import type { DeputadoResumo } from "@/types/contracts";
import { Foto } from "./Foto";
import { TLink } from "./Transicao";

export function DeputadoCard({ d, indice = 0 }: { d: DeputadoResumo; indice?: number }) {
  return (
    <li className="dep-card holo luz" style={{ "--i": Math.min(indice, 10) } as React.CSSProperties}>
      <Foto src={d.foto} nome={d.nome} tamanho={56} />
      <div className="dep-card-txt">
        <TLink className="dep-card-link" href={`/deputado/${encodeURIComponent(d.id)}`}>
          {d.nome}
        </TLink>
        <span className="dep-card-meta">
          {[d.partido, d.uf].filter(Boolean).join(" · ") || "Partido não informado"}
        </span>
      </div>
    </li>
  );
}
