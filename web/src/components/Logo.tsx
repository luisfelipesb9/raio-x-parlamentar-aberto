/** Símbolo do Raio-X: hemiciclo em arcos dentro de um anel, cortado por uma linha de varredura. */
export function Logo({ tamanho = 28 }: { tamanho?: number }) {
  return (
    <svg className="logo" width={tamanho} height={tamanho} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <circle cx="16" cy="16" r="14.2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M7.5 20.5a8.5 8.5 0 0 1 17 0" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M11.2 20.5a4.8 4.8 0 0 1 9.6 0" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="16" cy="20.5" r="1.5" fill="currentColor" />
      <line className="logo-scan" x1="2" y1="13" x2="30" y2="13" stroke="var(--acento)" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
