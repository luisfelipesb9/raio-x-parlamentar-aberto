import type { NoProva } from "./trilha";

/** Nó da árvore em forma plana: `id` é o caminho (ex.: "0.1.0"), em pré-ordem. */
export interface ItemArvore {
  id: string;
  pai: string | null;
  filhos: string[];
}

export function achata(raizes: readonly NoProva[]): ItemArvore[] {
  const saida: ItemArvore[] = [];
  const visita = (nos: readonly NoProva[], prefixo: string, pai: string | null) => {
    nos.forEach((no, i) => {
      const id = prefixo === "" ? `${i}` : `${prefixo}.${i}`;
      saida.push({ id, pai, filhos: no.filhos.map((_, j) => `${id}.${j}`) });
      visita(no.filhos, id, id);
    });
  };
  visita(raizes, "", null);
  return saida;
}

/** Ids dos nós que aparecem na tela (os descendentes de um nó recolhido ficam de fora). */
export function visiveis(itens: readonly ItemArvore[], recolhidos: ReadonlySet<string>): string[] {
  const porId = new Map(itens.map((i) => [i.id, i]));
  return itens
    .filter((item) => {
      for (let pai = item.pai; pai !== null; pai = porId.get(pai)?.pai ?? null) {
        if (recolhidos.has(pai)) return false;
      }
      return true;
    })
    .map((i) => i.id);
}

export interface Movimento {
  foco: string;
  recolhidos: Set<string>;
}

/**
 * Teclado do padrão ARIA "tree": setas, Home/End, abrir/fechar com setas, Enter e espaço.
 * Devolve o novo foco e o novo conjunto de recolhidos, ou `null` se a tecla não é da árvore.
 */
export function navega(tecla: string, atual: string, itens: readonly ItemArvore[], recolhidos: ReadonlySet<string>): Movimento | null {
  const item = itens.find((i) => i.id === atual);
  if (!item) return null;
  const lista = visiveis(itens, recolhidos);
  const pos = lista.indexOf(atual);
  const copia = () => new Set(recolhidos);
  const vai = (foco: string): Movimento => ({ foco, recolhidos: copia() });
  const temFilhos = item.filhos.length > 0;

  switch (tecla) {
    case "ArrowDown":
      return vai(lista[Math.min(pos + 1, lista.length - 1)] ?? atual);
    case "ArrowUp":
      return vai(lista[Math.max(pos - 1, 0)] ?? atual);
    case "Home":
      return vai(lista[0] ?? atual);
    case "End":
      return vai(lista[lista.length - 1] ?? atual);
    case "ArrowRight": {
      if (!temFilhos) return vai(atual);
      if (recolhidos.has(atual)) {
        const r = copia();
        r.delete(atual);
        return { foco: atual, recolhidos: r };
      }
      return vai(item.filhos[0]!);
    }
    case "ArrowLeft": {
      if (temFilhos && !recolhidos.has(atual)) {
        const r = copia();
        r.add(atual);
        return { foco: atual, recolhidos: r };
      }
      return vai(item.pai ?? atual);
    }
    case "Enter":
    case " ": {
      if (!temFilhos) return vai(atual);
      const r = copia();
      if (r.has(atual)) r.delete(atual);
      else r.add(atual);
      return { foco: atual, recolhidos: r };
    }
    default:
      return null;
  }
}
