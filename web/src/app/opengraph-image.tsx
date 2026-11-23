import { ImageResponse } from "next/og";

export const alt = "Raio-X Parlamentar: o que é público sobre deputados federais, explicado em linguagem simples";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const LINHAS = [
  { r: 120, n: 12 },
  { r: 170, n: 17 },
  { r: 220, n: 22 },
  { r: 270, n: 27 },
];

export default function Imagem() {
  const cx = 880;
  const cy = 470;
  const pontos = LINHAS.flatMap(({ r, n }) =>
    Array.from({ length: n }, (_, i) => {
      const a = Math.PI * (1 - i / (n - 1));
      return { x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) };
    }),
  );
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", background: "#070b0f", color: "#e8f1f4", position: "relative", padding: 72, flexDirection: "column", justifyContent: "flex-end" }}>
        <svg width="1200" height="630" viewBox="0 0 1200 630" style={{ position: "absolute", left: 0, top: 0 }}>
          <rect x="0" y="0" width="1200" height="630" fill="#070b0f" />
          {pontos.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r={i % 7 === 0 ? 6 : 4} fill="#5fe3f5" fillOpacity={i % 7 === 0 ? 1 : 0.45} />
          ))}
          <rect x="840" y="0" width="6" height="630" fill="#5fe3f5" fillOpacity="0.55" />
          <rect x="700" y="0" width="140" height="630" fill="#5fe3f5" fillOpacity="0.07" />
        </svg>
        <div style={{ display: "flex", fontSize: 26, letterSpacing: 6, color: "#5fe3f5", marginBottom: 18 }}>DADOS PÚBLICOS, SEM JURIDIQUÊS</div>
        <div style={{ display: "flex", fontSize: 108, fontWeight: 800, lineHeight: 1, letterSpacing: -3 }}>Raio-X</div>
        <div style={{ display: "flex", fontSize: 108, fontWeight: 300, lineHeight: 1.05, letterSpacing: -3 }}>Parlamentar</div>
        <div style={{ display: "flex", fontSize: 28, color: "#9db0b8", marginTop: 28, maxWidth: 640 }}>Isto não é acusação; é o que os dados públicos mostram.</div>
      </div>
    ),
    size,
  );
}
