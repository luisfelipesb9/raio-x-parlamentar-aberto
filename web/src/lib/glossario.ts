export interface Termo {
  id: string;
  termo: string;
  /** Texto curto para o tooltip e para a página do glossário. */
  definicao: string;
  /** Contexto extra, só na página do glossário. */
  porQueImporta?: string;
}

export const GLOSSARIO: readonly Termo[] = [
  {
    id: "ceap",
    termo: "CEAP (cota parlamentar)",
    definicao:
      "Verba mensal que cada deputado pode usar para despesas do mandato, como passagens, combustível e escritório.",
    porQueImporta:
      "É dinheiro público com nota fiscal: dá para ver com quem o deputado gastou e comparar com os colegas.",
  },
  {
    id: "votacao-nominal",
    termo: "Votação nominal",
    definicao: "Votação em que o voto de cada deputado fica registrado com o nome dele.",
    porQueImporta: "Só nela dá para dizer como cada deputado votou.",
  },
  {
    id: "votacao-simbolica",
    termo: "Votação simbólica",
    definicao: "Aprovada por acordo ou manifestação dos líderes: não existe registro do voto de cada deputado.",
    porQueImporta: "O sistema nunca atribui um voto individual a partir de votação simbólica.",
  },
  {
    id: "orientacao-governo",
    termo: "Orientação do governo",
    definicao: "Recomendação do líder do governo na Câmara sobre como os deputados devem votar.",
  },
  {
    id: "emenda",
    termo: "Emenda parlamentar",
    definicao: "Parte do orçamento federal que o deputado indica para um destino, como uma obra ou um município.",
  },
  {
    id: "emenda-pix",
    termo: "Emenda Pix",
    definicao:
      "Transferência especial que manda o dinheiro direto para estados e municípios, com menos rastreabilidade sobre o uso final.",
    porQueImporta: "Como é mais difícil acompanhar para onde o dinheiro foi, ela merece atenção extra da fiscalização.",
  },
  {
    id: "ceis-cnep",
    termo: "CEIS / CNEP",
    definicao: "Cadastros do governo federal de empresas punidas e impedidas de contratar com o poder público.",
  },
  {
    id: "pep",
    termo: "PEP (pessoa politicamente exposta)",
    definicao: "Quem ocupa ou ocupou cargo público relevante e, por isso, tem regras extras de transparência.",
  },
  {
    id: "qsa",
    termo: "QSA (quadro de sócios)",
    definicao: "Lista oficial dos sócios e administradores de uma empresa, registrada na Receita Federal.",
  },
  {
    id: "cf",
    termo: "Fator de certeza (CF)",
    definicao:
      "Número de 0 a 1 que diz o quanto o sistema confia numa conclusão. Perto de 1: base forte. Perto de 0: base fraca.",
    porQueImporta: "Mostra o tamanho da dúvida. Nenhuma conclusão do sistema é prova de culpa.",
  },
  {
    id: "guardrail",
    termo: "Guardrail (trava de segurança)",
    definicao:
      "Regra que impede o sistema de concluir demais, por exemplo: processo sem condenação definitiva não é culpa.",
  },
  {
    id: "backlink",
    termo: "Backlink",
    definicao: "Quem aponta para este item no mapa de relações, ou seja, todas as ligações que chegam até ele.",
  },
];

export function buscaTermo(id: string): Termo | undefined {
  return GLOSSARIO.find((t) => t.id === id);
}
