/** Preferência de movimento: do sistema (prefers-reduced-motion) OU escolhida no botão "Pausar animações" (WCAG 2.2.2). */
export const CHAVE_PAUSA = "animacoes";

export function animacoesPausadas(): boolean {
  return document.documentElement.dataset.animacoes === "pausadas";
}

export function movimentoReduzido(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches || animacoesPausadas();
}
