import { TIPOS_NO } from "@/lib/grafo";

/** Forma do tipo de nó (a forma duplica a cor: tipos distinguíveis sem depender dela). */
export function Forma({ tipo, tamanho = 18 }: { tipo: string; tamanho?: number }) {
  const info = TIPOS_NO[tipo];
  const cor = `var(${info?.cor ?? "--muted"})`;
  const props = { fill: cor, stroke: "var(--fg)", strokeWidth: 1 };
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 18 18" aria-hidden="true" focusable="false">
      {info?.forma === "ellipse" && <circle cx="9" cy="9" r="7" {...props} />}
      {info?.forma === "hexagon" && <polygon points="9,2 15,5.5 15,12.5 9,16 3,12.5 3,5.5" {...props} />}
      {info?.forma === "rectangle" && <rect x="3" y="3" width="12" height="12" {...props} />}
      {info?.forma === "diamond" && <polygon points="9,1.5 16.5,9 9,16.5 1.5,9" {...props} />}
      {info?.forma === "triangle" && <polygon points="9,2 16,15 2,15" {...props} />}
      {info?.forma === "round-rectangle" && <rect x="2.5" y="4" width="13" height="10" rx="4" {...props} />}
      {!info && <circle cx="9" cy="9" r="6" fill="none" stroke="var(--borda-forte)" strokeWidth="2" strokeDasharray="3 2" />}
    </svg>
  );
}

/** Super-nó "+N": retângulo tracejado, como no mapa. */
export function FormaGrupo() {
  return (
    <svg width="22" height="18" viewBox="0 0 22 18" aria-hidden="true" focusable="false">
      <rect x="1.5" y="3.5" width="19" height="11" rx="4" fill="var(--surface-2)" stroke="var(--borda-forte)" strokeWidth="2" strokeDasharray="3 2" />
    </svg>
  );
}
