import type { PassoProva } from "@/types/contracts";

export interface NoProva {
  passo: PassoProva;
  filhos: NoProva[];
}

/**
 * A API devolve a trilha da prova regressiva em ordem de visita (pré-ordem) com `profundidade`.
 * Reconstrói a árvore: cada passo é filho do passo anterior mais raso que ele.
 */
export function montaArvore(trilha: readonly PassoProva[]): NoProva[] {
  const raizes: NoProva[] = [];
  const pilha: NoProva[] = [];
  for (const passo of trilha) {
    const no: NoProva = { passo, filhos: [] };
    while (pilha.length > 0 && pilha[pilha.length - 1]!.passo.profundidade >= passo.profundidade) pilha.pop();
    const pai = pilha[pilha.length - 1];
    if (pai) pai.filhos.push(no);
    else raizes.push(no);
    pilha.push(no);
  }
  return raizes;
}
