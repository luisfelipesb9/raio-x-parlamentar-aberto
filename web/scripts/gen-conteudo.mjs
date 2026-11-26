// Gera src/content/gerado/conteudo.json a partir de ../docs/conteudo/**/*.md e ../knowledge/rules/R*.yaml.
// Node puro, sem dependências: o YAML das regras e o frontmatter usam um subconjunto pequeno e controlado,
// lido por um parser mínimo (abaixo). Construção fora do subconjunto é erro explícito, nunca leitura errada.
// Determinístico: mesma entrada, mesmo texto (nada de data de geração). Uso: `pnpm gen:conteudo`.
import { existsSync, readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.join(aqui, "../..");
const SAIDA = path.join(aqui, "../src/content/gerado/conteudo.json");

// ---------- YAML mínimo ----------

function erro(msg, linha) {
  return new Error(`YAML: ${msg}${linha ? ` (linha: ${linha})` : ""}`);
}

/** Tira o comentário `# ...` do fim da linha (só fora de aspas; as aspas só abrem no começo de um valor). */
function semComentario(linha) {
  let aspas = null;
  let anterior = " ";
  for (let i = 0; i < linha.length; i++) {
    const c = linha[i];
    if (aspas) {
      if (c === "\\" && aspas === '"') i++;
      else if (c === aspas) aspas = null;
    } else if ((c === '"' || c === "'") && /[\s:,[{-]/.test(anterior)) aspas = c;
    else if (c === "#" && /\s/.test(anterior)) return linha.slice(0, i).trimEnd();
    if (!aspas && c !== " ") anterior = c;
    else if (!aspas) anterior = " ";
  }
  return linha.trimEnd();
}

// O motor lê as regras com yaml.safe_load (PyYAML). Para o gerador nunca ler diferente, só aceita sem aspas as formas
// que os dois leem igual: true, false, null, ~, inteiros e decimais simples. O resto que o PyYAML interpretaria
// (yes/no/on/off/y/n, True/Null, .5, 1_000, +3, 1e3, 0x1F, .inf...) é erro: exige aspas.
const AMBIGUO_BOOLEANO = /^(yes|no|on|off|y|n|true|false|null)$/i;
const AMBIGUO_NUMERICO = /^(?:[-+]?(?:\d[\d_]*)?(?:\.\d*)?(?:[eE][-+]?\d+)?|0[xXoObB][\da-fA-F_]+|[-+]?\.(?:inf|nan))$/i;

function tipado(bruto) {
  const s = bruto.trim();
  if (s === "" || s === "null" || s === "~") return null;
  if (s === "true") return true;
  if (s === "false") return false;
  if (/^-?\d+$/.test(s)) return Number(s);
  if (/^-?\d+\.\d+$/.test(s)) return Number(s);
  if (AMBIGUO_BOOLEANO.test(s) || (/\d|inf|nan/i.test(s) && AMBIGUO_NUMERICO.test(s))) {
    throw erro(`valor sem aspas "${s}" seria lido de outro jeito pelo PyYAML; coloque entre aspas`, s);
  }
  return s;
}

/** Valor em linha: escalar, "aspas", 'aspas', {mapa} ou [lista]. Devolve [valor, próxima posição]. */
function valorEmLinha(s, pos, dentroDeFluxo) {
  while (s[pos] === " ") pos++;
  const c = s[pos];
  if (c === '"' || c === "'") {
    let out = "";
    let i = pos + 1;
    for (; i < s.length; i++) {
      if (c === '"' && s[i] === "\\") {
        const prox = s[++i];
        out += prox === "n" ? "\n" : prox === "t" ? "\t" : prox;
      } else if (s[i] === c) {
        if (c === "'" && s[i + 1] === "'") {
          out += "'";
          i++;
        } else break;
      } else out += s[i];
    }
    if (i >= s.length) throw erro("aspas sem fechar", s);
    return [out, i + 1];
  }
  if (c === "{") {
    const mapa = {};
    pos++;
    for (;;) {
      while (s[pos] === " ") pos++;
      if (s[pos] === "}") return [mapa, pos + 1];
      const m = /^([A-Za-z0-9_]+)\s*:\s*/.exec(s.slice(pos));
      if (!m) throw erro("chave inválida no mapa em linha", s);
      const [v, p] = valorEmLinha(s, pos + m[0].length, true);
      mapa[m[1]] = v;
      pos = p;
      while (s[pos] === " ") pos++;
      if (s[pos] === ",") pos++;
      else if (s[pos] !== "}") throw erro("esperava , ou } no mapa em linha", s);
    }
  }
  if (c === "[") {
    const lista = [];
    pos++;
    for (;;) {
      while (s[pos] === " ") pos++;
      if (s[pos] === "]") return [lista, pos + 1];
      const [v, p] = valorEmLinha(s, pos, true);
      lista.push(v);
      pos = p;
      while (s[pos] === " ") pos++;
      if (s[pos] === ",") pos++;
      else if (s[pos] !== "]") throw erro("esperava , ou ] na lista em linha", s);
    }
  }
  if (c === "|" || c === ">") throw erro("bloco multilinha (| ou >) não suportado", s);
  let fim = pos;
  while (fim < s.length && !(dentroDeFluxo && /[,}\]]/.test(s[fim]))) fim++;
  return [tipado(s.slice(pos, fim)), fim];
}

function valorCompleto(s) {
  const [v, p] = valorEmLinha(s, 0, false);
  if (s.slice(p).trim() !== "") throw erro("texto sobrando depois do valor", s);
  return v;
}

/** Lê o subconjunto de YAML usado em knowledge/rules e no frontmatter: mapas, listas, escalares, {..} e [..]. */
export function parseYaml(texto) {
  const linhas = texto
    .replace(/\r\n?/g, "\n")
    .split("\n")
    .map((l) => semComentario(l))
    .filter((l) => l.trim() !== "")
    .map((l) => ({ indent: l.length - l.trimStart().length, texto: l.trim() }));
  let i = 0;

  function bloco(indent) {
    return linhas[i].texto.startsWith("- ") || linhas[i].texto === "-" ? lista(indent) : mapa(indent);
  }

  function lista(indent) {
    const itens = [];
    while (i < linhas.length && linhas[i].indent === indent && (linhas[i].texto.startsWith("- ") || linhas[i].texto === "-")) {
      const resto = linhas[i].texto.slice(1).trim();
      if (resto === "") throw erro("item de lista em bloco aninhado não suportado", linhas[i].texto);
      if (/^[A-Za-z0-9_]+:(\s|$)/.test(resto)) throw erro("mapa dentro de item de lista (sem {}) não suportado", linhas[i].texto);
      itens.push(valorCompleto(resto));
      i++;
    }
    return itens;
  }

  function mapa(indent) {
    const out = {};
    while (i < linhas.length && linhas[i].indent === indent) {
      const l = linhas[i];
      const m = /^([A-Za-z0-9_]+):(?:\s+(.*))?$/.exec(l.texto);
      if (!m) throw erro("linha não reconhecida", l.texto);
      i++;
      if (m[2] !== undefined && m[2] !== "") out[m[1]] = valorCompleto(m[2]);
      else if (i < linhas.length && (linhas[i].indent > indent || (linhas[i].indent === indent && linhas[i].texto.startsWith("- ")))) {
        out[m[1]] = bloco(linhas[i].indent);
      } else out[m[1]] = null;
    }
    if (i < linhas.length && linhas[i].indent > indent) throw erro("indentação inesperada", linhas[i].texto);
    return out;
  }

  if (linhas.length === 0) return {};
  const raiz = bloco(linhas[0].indent);
  if (i < linhas.length) throw erro("indentação inesperada", linhas[i].texto);
  return raiz;
}

// ---------- Markdown com frontmatter ----------

const OBRIGATORIOS = ["slug", "titulo", "descricao", "resposta", "atualizado"];
const LIMITES = { titulo: 70, descricao: 160, resposta: 240 };

/** AAAA-MM-DD que existe no calendário (2026-02-31 não vale: o JavaScript a "corrigiria" em silêncio). */
function dataValida(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return false;
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return d.getUTCFullYear() === Number(m[1]) && d.getUTCMonth() === Number(m[2]) - 1 && d.getUTCDate() === Number(m[3]);
}

function lePagina(arquivoAbs, nome, avisos, ehRegra = false) {
  const bruto = readFileSync(arquivoAbs, "utf8").replace(/\r\n?/g, "\n");
  const m = /^---\n([\s\S]*?)\n---\n?([\s\S]*)$/.exec(bruto);
  if (!m) throw new Error(`${nome}.md: frontmatter (--- ... ---) ausente`);
  const fm = parseYaml(m[1]);
  for (const campo of OBRIGATORIOS) {
    if (fm[campo] === undefined || fm[campo] === null || String(fm[campo]).trim() === "") {
      throw new Error(`${nome}.md: campo obrigatório "${campo}" ausente no frontmatter`);
    }
  }
  if (!dataValida(String(fm.atualizado))) throw new Error(`${nome}.md: "atualizado" deve ser uma data real no formato AAAA-MM-DD`);
  if (String(fm.slug) !== nome) throw new Error(`${nome}.md: "slug" (${fm.slug}) deve ser igual ao nome do arquivo`);
  for (const [campo, max] of Object.entries(LIMITES)) {
    if (String(fm[campo]).length > max) avisos.push(`${nome}.md: "${campo}" tem ${String(fm[campo]).length} caracteres (limite ${max})`);
  }
  const pagina = {
    arquivo: nome,
    slug: String(fm.slug),
    titulo: String(fm.titulo),
    descricao: String(fm.descricao),
    resposta: String(fm.resposta),
    atualizado: String(fm.atualizado),
  };
  if (ehRegra) {
    if (fm.regra === undefined || fm.regra === null) throw new Error(`regras/${nome}.md: campo "regra" ausente no frontmatter`);
    if (String(fm.regra) !== nome) throw new Error(`regras/${nome}.md: "regra" (${fm.regra}) deve ser igual ao nome do arquivo`);
    pagina.regra = String(fm.regra);
  } else if (fm.regra !== undefined && fm.regra !== null) pagina.regra = String(fm.regra);
  pagina.corpo = m[2].trim();
  return pagina;
}

// ---------- Regras ----------

/** R01 < R02 < ... < R06 < R06b < R07 (número, depois sufixo). */
function chaveDeRegra(id) {
  const m = /^R(\d+)(.*)$/.exec(id);
  return m ? [Number(m[1]), m[2]] : [Infinity, id];
}
function comparaRegras(a, b) {
  const [na, sa] = chaveDeRegra(a);
  const [nb, sb] = chaveDeRegra(b);
  return na - nb || (sa < sb ? -1 : sa > sb ? 1 : 0);
}

function leRegra(arquivoAbs, texto) {
  const y = parseYaml(texto);
  for (const campo of ["id", "nome", "tipo", "categoria"]) {
    if (typeof y[campo] !== "string") throw new Error(`${path.basename(arquivoAbs)}: campo "${campo}" ausente`);
  }
  const parametros = y.parametros ?? {};
  for (const [k, v] of Object.entries(parametros)) {
    if (v === null || typeof v === "object") throw new Error(`${path.basename(arquivoAbs)}: parâmetro "${k}" deve ser texto, número ou booleano`);
  }
  const regra = {
    id: y.id,
    nome: y.nome,
    tipo: y.tipo,
    categoria: y.categoria,
    ...(y.conclui ? { conclui: y.conclui } : {}),
    ...(y.predicado ? { predicado: y.predicado } : {}),
    parametros,
    ...(y.se ? { se: y.se } : {}),
    ...(typeof y.cf === "number" ? { cf: y.cf } : {}),
    penalidades: (y.penalidades ?? []).map((p) => ({ se: String(p.se), fator: Number(p.fator), motivo: String(p.motivo) })),
    ...(y.por_que ? { porQue: y.por_que } : {}),
    limitacoes: (y.limitacoes ?? []).map(String),
    ...(y.fonte_metodologica ? { fonteMetodologica: y.fonte_metodologica } : {}),
    ...(typeof y.prioridade === "number" ? { prioridade: y.prioridade } : {}),
    requer: (y.requer ?? []).map(String),
    composta: !y.predicado && (y.requer ?? []).length > 0,
  };
  return regra;
}

// ---------- Geração ----------

const PAGINAS = ["dados-e-api", "faq", "metodo", "para-estudantes"];

function arquivosMd(dir) {
  return existsSync(dir)
    ? readdirSync(dir)
        .filter((f) => f.endsWith(".md"))
        .sort()
    : [];
}

export function gerarConteudo({ dirConteudo, dirRegras }) {
  const avisos = [];
  const paginas = {};
  for (const nome of PAGINAS) {
    const f = path.join(dirConteudo, `${nome}.md`);
    if (existsSync(f)) {
      paginas[nome] = lePagina(f, nome, avisos);
      if (nome === "faq") {
        const antes = paginas[nome].corpo.split(/^##\s/m)[0].trim();
        if (antes && !paginas[nome].corpo.startsWith("##")) avisos.push("faq.md: há texto antes da primeira pergunta (##); ele não aparece na página");
      }
    }
  }

  const textos = {};
  for (const f of arquivosMd(path.join(dirConteudo, "regras"))) {
    const nome = f.replace(/\.md$/, "");
    const pagina = lePagina(path.join(dirConteudo, "regras", f), nome, avisos, true);
    textos[String(pagina.regra)] = pagina;
  }

  const regras = [];
  if (existsSync(dirRegras)) {
    for (const f of readdirSync(dirRegras).sort()) {
      if (!/^R.*\.yaml$/.test(f)) continue;
      const abs = path.join(dirRegras, f);
      const regra = leRegra(abs, readFileSync(abs, "utf8"));
      regras.push({ ...regra, texto: textos[regra.id] ?? null });
    }
  }
  regras.sort((a, b) => comparaRegras(a.id, b.id));
  for (const nome of Object.keys(textos)) { // chaves = campo "regra:" (igual ao nome do arquivo)
    if (!regras.some((r) => r.id === nome)) avisos.push(`regras/${nome}.md: sem regra correspondente em knowledge/rules (ignorado)`);
  }
  for (const a of avisos) console.warn(`[gen-conteudo] aviso: ${a}`);
  return { paginas, regras };
}

export function serializa(conteudo) {
  return `${JSON.stringify(conteudo, null, 2)}\n`;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const conteudo = gerarConteudo({ dirConteudo: path.join(RAIZ, "docs/conteudo"), dirRegras: path.join(RAIZ, "knowledge/rules") });
  mkdirSync(path.dirname(SAIDA), { recursive: true });
  writeFileSync(SAIDA, serializa(conteudo));
  console.log(`[gen-conteudo] ${Object.keys(conteudo.paginas).length} páginas, ${conteudo.regras.length} regras -> ${path.relative(process.cwd(), SAIDA)}`);
}
