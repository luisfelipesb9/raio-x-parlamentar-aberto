/**
 * Hemiciclo em raio-x: pontos em arcos (como as cadeiras do plenário) varridos por um feixe de luz.
 * SVG + CSS puros (sem JS, sem canvas). Os pontos acendem em sequência conforme o feixe passa (delay por posição x).
 * Tudo é decorativo (aria-hidden) e desligado por prefers-reduced-motion.
 */
const LINHAS = [
  { r: 74, n: 14 },
  { r: 104, n: 20 },
  { r: 134, n: 26 },
  { r: 164, n: 32 },
  { r: 194, n: 38 },
];
const CX = 220;
const CY = 232;
const PERIODO = 8; // s, igual ao CSS (--varredura)

const pontos = LINHAS.flatMap(({ r, n }, li) =>
  Array.from({ length: n }, (_, i) => {
    const ang = Math.PI * (1 - i / (n - 1));
    const x = CX + r * Math.cos(ang);
    const y = CY - r * Math.sin(ang);
    return { x, y, li, i, atraso: (x / 440) * PERIODO * 0.71 };
  }),
);

export function HeroScan() {
  return (
    <div className="hero-scan" aria-hidden="true">
      <svg viewBox="0 0 440 260" focusable="false">
        <defs>
          <linearGradient id="feixe" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stopColor="var(--acento)" stopOpacity="0" />
            <stop offset="0.85" stopColor="var(--acento)" stopOpacity="0.28" />
            <stop offset="1" stopColor="var(--acento)" stopOpacity="0.9" />
          </linearGradient>
          <clipPath id="recorte">
            <rect x="0" y="0" width="440" height="260" />
          </clipPath>
        </defs>
        {/* grade polar */}
        {LINHAS.map(({ r }) => (
          <path key={r} d={`M ${CX - r} ${CY} A ${r} ${r} 0 0 1 ${CX + r} ${CY}`} fill="none" stroke="var(--acento)" strokeOpacity="0.16" strokeWidth="1" />
        ))}
        <line x1="10" y1={CY} x2="430" y2={CY} stroke="var(--acento)" strokeOpacity="0.28" strokeWidth="1" />
        {Array.from({ length: 19 }, (_, k) => {
          const a = Math.PI * (k / 18);
          return <line key={k} x1={CX + 58 * Math.cos(a)} y1={CY - 58 * Math.sin(a)} x2={CX + 208 * Math.cos(a)} y2={CY - 208 * Math.sin(a)} stroke="var(--acento)" strokeOpacity={k % 3 === 0 ? 0.2 : 0.07} strokeWidth="1" />;
        })}
        {/* cadeiras */}
        <g>
          {pontos.map((p) => (
            <circle key={`${p.li}-${p.i}`} className="cadeira" cx={p.x.toFixed(1)} cy={p.y.toFixed(1)} r="3" style={{ animationDelay: `${p.atraso.toFixed(2)}s` }} />
          ))}
        </g>
        {/* feixe */}
        <g clipPath="url(#recorte)">
          <g className="feixe">
            <rect x="-90" y="0" width="90" height="260" fill="url(#feixe)" />
          </g>
        </g>
        {/* mira central */}
        <circle cx={CX} cy={CY} r="5" fill="var(--acento)" />
        <circle className="pulso" cx={CX} cy={CY} r="5" fill="none" stroke="var(--acento)" strokeWidth="1.5" />
        {/* marcas de registro */}
        {[
          [8, 8, 1, 1],
          [432, 8, -1, 1],
          [8, 252, 1, -1],
          [432, 252, -1, -1],
        ].map(([x, y, sx, sy]) => (
          <path key={`${x}-${y}`} d={`M ${x} ${(y ?? 0) + 14 * (sy ?? 1)} V ${y} H ${(x ?? 0) + 14 * (sx ?? 1)}`} fill="none" stroke="var(--acento)" strokeOpacity="0.55" strokeWidth="1.5" />
        ))}
      </svg>
    </div>
  );
}
