// Gera src/types/contracts.ts a partir dos JSON Schemas em src/types/schemas/ (gerados pelo backend).
// Cada schema embute seus $defs; juntamos tudo e removemos declarações duplicadas por nome.
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "json-schema-to-typescript";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const dirSchemas = path.join(aqui, "../src/types/schemas");
const saida = path.join(aqui, "../src/types/contracts.ts");

const indice = JSON.parse(await readFile(path.join(dirSchemas, "index.json"), "utf8"));
const vistos = new Set();

// Remove `title` das propriedades (senão o gerador cria um alias por campo, ex.: `type Cf = number`).
// Mantém o título da raiz e das entradas de $defs: é o nome do tipo.
function limpaTitulos(no, ehNomeado = true) {
  if (Array.isArray(no)) return no.map((n) => limpaTitulos(n, false));
  if (no === null || typeof no !== "object") return no;
  const saida = {};
  for (const [k, v] of Object.entries(no)) {
    if (k === "title" && !ehNomeado) continue;
    if (k === "$defs") {
      saida[k] = Object.fromEntries(Object.entries(v).map(([n, d]) => [n, limpaTitulos(d, true)]));
    } else if (k === "properties") {
      saida[k] = Object.fromEntries(Object.entries(v).map(([n, d]) => [n, limpaTitulos(d, false)]));
    } else {
      saida[k] = limpaTitulos(v, false);
    }
  }
  return saida;
}
const blocos = [];

for (const nome of indice.schemas) {
  const schema = limpaTitulos(JSON.parse(await readFile(path.join(dirSchemas, `${nome}.json`), "utf8")));
  const ts = await compile(schema, nome, {
    bannerComment: "",
    unknownAny: true,
    additionalProperties: false,
    declareExternallyReferenced: true,
    format: true,
  });
  // separa por declaração de topo (com o JSDoc que a precede)
  const partes = ts.split(/\n(?=(?:\/\*\*[\s\S]*?\*\/\n)?export (?:interface|type) )/);
  for (const parte of partes) {
    const m = parte.match(/export (?:interface|type) (\w+)/);
    if (!m || vistos.has(m[1])) continue;
    vistos.add(m[1]);
    blocos.push(parte.trim());
  }
}

const cabecalho = `/* eslint-disable */
// ARQUIVO GERADO por \`pnpm gen:types\` a partir de src/types/schemas/*.json — não edite à mão.
export const CONTRACT_VERSION = ${JSON.stringify(indice.contract_version)} as const;

`;
await writeFile(saida, cabecalho + blocos.join("\n\n") + "\n");
console.log(`contracts.ts: ${blocos.length} tipos (contract_version ${indice.contract_version})`);
