/**
 * Markdown (subconjunto controlado) -> React, no servidor e sem `dangerouslySetInnerHTML`.
 * Aceita: títulos `##`/`###`, parágrafos, listas `-` e `1.`, bloco ```, **negrito**, *itálico*, `código` e [texto](link).
 * Qualquer outra coisa (HTML cru, tabelas, imagens) vira texto comum, que o React escapa. Só são emitidos os elementos
 * h2, h3, p, ul, ol, li, pre, code, strong, em e a. Link só se for interno (`/`, `#`) ou `https:`; os demais viram texto.
 */
import { Fragment, type ReactNode } from "react";

const LINK = /\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)/;
const NEGRITO = /\*\*(.+?)\*\*/;
const ITALICO = /\*(?!\s)(.+?)\*/;
const CODIGO = /`([^`]+)`/;
const PADROES = [LINK, NEGRITO, CODIGO, ITALICO] as const;

/** Destino aceito: caminho interno ou https. Devolve `null` para o resto (javascript:, data:, http:, //host...). */
function destinoSeguro(href: string): { href: string; externo: boolean } | null {
  if (href.startsWith("/") && !href.startsWith("//") && !href.includes("\\")) return { href, externo: false };
  if (href.startsWith("#")) return { href, externo: false };
  try {
    const u = new URL(href);
    return u.protocol === "https:" ? { href: u.href, externo: true } : null;
  } catch {
    return null;
  }
}

function emLinha(texto: string, chave = "i"): ReactNode[] {
  const saida: ReactNode[] = [];
  let resto = texto;
  let n = 0;
  while (resto.length > 0) {
    let melhor: { m: RegExpExecArray; padrao: RegExp } | null = null;
    for (const padrao of PADROES) {
      const m = padrao.exec(resto);
      if (m && (melhor === null || m.index < melhor.m.index)) melhor = { m, padrao };
    }
    if (melhor === null) {
      saida.push(resto);
      break;
    }
    const { m, padrao } = melhor;
    if (m.index > 0) saida.push(resto.slice(0, m.index));
    const k = `${chave}.${n++}`;
    const interno = m[1] ?? "";
    if (padrao === LINK) {
      const destino = destinoSeguro(m[2] ?? "");
      if (destino === null) saida.push(<Fragment key={k}>{emLinha(interno, k)}</Fragment>);
      else if (destino.externo)
        saida.push(
          <a key={k} href={destino.href} rel="noopener noreferrer" target="_blank">
            {emLinha(interno, k)}
          </a>,
        );
      else
        saida.push(
          <a key={k} href={destino.href}>
            {emLinha(interno, k)}
          </a>,
        );
    } else if (padrao === NEGRITO) saida.push(<strong key={k}>{emLinha(interno, k)}</strong>);
    else if (padrao === CODIGO) saida.push(<code key={k}>{interno}</code>);
    else saida.push(<em key={k}>{emLinha(interno, k)}</em>);
    resto = resto.slice(m.index + m[0].length);
  }
  return saida;
}

/** Âncora estável para um título: minúsculas, sem acento, hífens. */
export function ancora(titulo: string): string {
  return titulo
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

const ITEM_NAO_ORDENADO = /^[-*]\s+(.*)$/;
const ITEM_ORDENADO = /^\d+[.)]\s+(.*)$/;
const TITULO = /^(#{2,3})\s+(.*?)\s*#*\s*$/;

function iniciaBloco(linha: string): boolean {
  return TITULO.test(linha) || ITEM_NAO_ORDENADO.test(linha) || ITEM_ORDENADO.test(linha) || linha.startsWith("```");
}

export function markdownParaReact(md: string): ReactNode[] {
  const linhas = md.replace(/\r\n?/g, "\n").split("\n");
  const saida: ReactNode[] = [];
  let i = 0;
  while (i < linhas.length) {
    const linha = linhas[i] ?? "";
    const k = `b${saida.length}`;
    if (linha.trim() === "") {
      i++;
    } else if (linha.startsWith("```")) {
      const codigo: string[] = [];
      i++;
      while (i < linhas.length && !(linhas[i] ?? "").startsWith("```")) codigo.push(linhas[i++] ?? "");
      i++;
      saida.push(
        <pre key={k}>
          <code>{codigo.join("\n")}</code>
        </pre>,
      );
    } else if (TITULO.test(linha)) {
      const m = TITULO.exec(linha)!;
      const texto = m[2] ?? "";
      const id = ancora(texto) || undefined;
      saida.push(
        m[1]!.length === 2 ? (
          <h2 key={k} id={id}>
            {emLinha(texto, k)}
          </h2>
        ) : (
          <h3 key={k} id={id}>
            {emLinha(texto, k)}
          </h3>
        ),
      );
      i++;
    } else if (ITEM_NAO_ORDENADO.test(linha) || ITEM_ORDENADO.test(linha)) {
      const ordenada = ITEM_ORDENADO.test(linha);
      const padrao = ordenada ? ITEM_ORDENADO : ITEM_NAO_ORDENADO;
      const itens: string[] = [];
      while (i < linhas.length) {
        const atual = linhas[i] ?? "";
        const m = padrao.exec(atual);
        if (m) {
          itens.push(m[1] ?? "");
          i++;
        } else if (/^\s+\S/.test(atual) && itens.length > 0) {
          itens[itens.length - 1] += ` ${atual.trim()}`;
          i++;
        } else break;
      }
      const lis = itens.map((t, n) => <li key={n}>{emLinha(t, `${k}.${n}`)}</li>);
      saida.push(ordenada ? <ol key={k}>{lis}</ol> : <ul key={k}>{lis}</ul>);
    } else {
      const par: string[] = [];
      while (i < linhas.length && (linhas[i] ?? "").trim() !== "" && (par.length === 0 || !iniciaBloco(linhas[i] ?? ""))) {
        par.push((linhas[i++] ?? "").trim());
      }
      saida.push(<p key={k}>{emLinha(par.join(" "), k)}</p>);
    }
  }
  return saida;
}

/** O texto sem marcação (para JSON-LD e resumos): links viram o texto, listas viram frases corridas. */
export function markdownParaTexto(md: string): string {
  return md
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/\[([^\]]+)\]\((?:[^()\s]|\([^()\s]*\))+\)/g, "$1")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(?!\s)(.+?)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^\s*(?:[-*]|\d+[.)])\s+/gm, "")
    .replace(/^#{2,3}\s+/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}

export type PerguntaFaq = { pergunta: string; resposta: string };

/** Cada `##` é uma pergunta; o texto até o próximo `##` é a resposta (em Markdown). Perguntas sem resposta são ignoradas. */
export function perguntasDoFaq(corpo: string): PerguntaFaq[] {
  const pares: PerguntaFaq[] = [];
  let atual: { pergunta: string; linhas: string[] } | null = null;
  const fecha = () => {
    if (!atual) return;
    const resposta = atual.linhas.join("\n").trim();
    if (resposta) pares.push({ pergunta: atual.pergunta, resposta });
  };
  let dentroDeCodigo = false;
  for (const linha of corpo.replace(/\r\n?/g, "\n").split("\n")) {
    if (linha.startsWith("```")) dentroDeCodigo = !dentroDeCodigo;
    const m = !dentroDeCodigo ? /^##\s+(.+?)\s*$/.exec(linha) : null;
    if (m) {
      fecha();
      atual = { pergunta: m[1] ?? "", linhas: [] };
    } else atual?.linhas.push(linha);
  }
  fecha();
  return pares;
}
