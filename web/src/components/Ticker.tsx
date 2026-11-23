import { GLOSSARIO } from "@/lib/glossario";

const FRASES = ["dado público", "fonte oficial", "nível de certeza", "isto não é acusação"];

/** Faixa de termos em movimento. Decorativa (o glossário tem o conteúdo); estática com prefers-reduced-motion. */
export function Ticker() {
  const itens = [...GLOSSARIO.map((t) => t.termo.split(" (")[0] ?? t.termo), ...FRASES];
  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker-trilho">
        {[0, 1].map((c) => (
          <ul key={c} className="ticker-lista">
            {itens.map((t) => (
              <li key={`${c}-${t}`}>{t}</li>
            ))}
          </ul>
        ))}
      </div>
    </div>
  );
}
