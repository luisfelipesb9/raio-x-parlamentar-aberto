/** Texto do /llms.txt (resumo do projeto para leitores automáticos). Links sempre absolutos. */
import { LICENCAS_DADOS_URL, REPO_URL } from "./jsonld";
import { urlAbsoluta } from "./seo";

export function gerarLlmsTxt(): string {
  const l = (nome: string, caminho: string, descricao: string) => `- [${nome}](${urlAbsoluta(caminho)}): ${descricao}`;
  return `${[
    "# Raio-X Parlamentar",
    "",
    "> Sistema de código aberto que reúne o que é público sobre deputados federais brasileiros (votações, gastos da cota parlamentar, emendas, candidaturas e cadastros oficiais) e explica, em linguagem simples, os padrões que aparecem nesses dados. Cada conclusão traz um nível de certeza e o link para a fonte oficial. É um projeto acadêmico de Sistemas Especialistas (BSI/Unimontes), feito só com dados públicos abertos.",
    "",
    "## Páginas principais",
    l("Início", "/", "busca de deputados por nome, partido ou estado"),
    l("Deputados", "/deputados", "lista de todos os deputados da base, cada um com sua ficha"),
    l("Mapa de relações", "/grafo", "quem se liga a quem nos dados públicos: empresas, municípios, emendas"),
    l("Perguntar ao sistema", "/perguntar", "o raciocínio do sistema passo a passo, da pergunta até as evidências"),
    l("Comparar deputados", "/comparar", "dois deputados lado a lado, com os mesmos critérios"),
    l("Glossário", "/glossario", "os termos técnicos (CEAP, votação nominal, emenda Pix, nível de certeza) em palavras simples"),
    l("Fontes e método", "/fontes", "de onde vêm os dados, quanto a base cobre e como o sistema chega a cada conclusão"),
    "",
    "Cada deputado tem uma ficha em um endereço do tipo /deputado/{número}, com os números e as fontes oficiais.",
    "",
    "## Metodologia e limites",
    "- Isto não é acusação. Um alerta indica um padrão nos dados públicos, nunca prova de irregularidade.",
    "- Processo sem condenação definitiva não é culpa. Votação simbólica não é voto individual.",
    "- Toda conclusão mostra o nível de certeza do sistema e o link para a fonte oficial, com a data da coleta.",
    "- A base cobre só o período e as fontes listadas na página de fontes; o que não está nela não deve ser deduzido.",
    "",
    "## Dados e licenças",
    `- [Licenças e termos dos dados](${LICENCAS_DADOS_URL}): condição de uso de cada fonte oficial e o que ainda falta confirmar`,
    "",
    "## Código",
    `- [Repositório](${REPO_URL}): código aberto, regras de inferência e documentação`,
    "",
    "## Opcional",
    l("Mapa do site (sitemap.xml)", "/sitemap.xml", "todas as páginas públicas, incluindo as fichas"),
  ].join("\n")}\n`;
}
