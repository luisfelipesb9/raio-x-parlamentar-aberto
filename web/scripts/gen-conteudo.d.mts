import type { Conteudo } from "../src/content/tipos";

export function parseYaml(texto: string): unknown;
export function gerarConteudo(opcoes: { dirConteudo: string; dirRegras: string }): Conteudo;
export function serializa(conteudo: Conteudo): string;
