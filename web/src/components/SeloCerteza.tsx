import type { Nivel } from "@/types/contracts";
import { NIVEIS } from "@/lib/nivel";

/** Semáforo de certeza: texto + quantidade de barras + estilo. Nunca só cor. */
export function SeloCerteza({ nivel, mostrarExplicacao = false }: { nivel: Nivel; mostrarExplicacao?: boolean }) {
  const info = NIVEIS[nivel];
  return (
    <span className={`selo selo-${nivel}`} title={info.explicacao}>
      <span className="selo-barras" aria-hidden="true">
        {[1, 2, 3, 4].map((i) => (
          <i key={i} className={i <= info.barras ? "on" : ""} style={{ height: `${6 + i * 3}px` }} />
        ))}
      </span>
      <span className="selo-texto">{info.rotulo}</span>
      {mostrarExplicacao && <span className="visually-hidden">. {info.explicacao}</span>}
    </span>
  );
}
