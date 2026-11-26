# Grafo de relações: referências de design e técnicas

Escopo: Cytoscape 3.35.0 (MIT) + fcose 2.2.0, CSS puro, sem libs de UI. Identidade "raio-x" (tokens em `web/src/app/globals.css`).
Problemas-alvo: nuvem de ~300 folhas num hub, rótulos sobrepostos, tamanho sem significado, sem busca, legenda sem arestas, corte silencioso.
Esforço: P = horas, M = 1 a 2 dias, G = mais de 2 dias. Datas e versões consultadas em 2026-11-26.

## 0. KokonutUI: o que existe e o que aproveitar

- Licença: componentes gratuitos em MIT (LICENSE do repositório, "Copyright (c) 2025 kokonutUI"). A versão Pro é paga e os termos dela não estão publicados na página. Fonte: https://github.com/kokonut-labs/kokonutui e https://kokonutui.com
- Pré-requisitos: Tailwind v4, shadcn CLI, helper `cn`, `motion` e lucide-react (https://kokonutui.com/docs). Incompatível com a regra "sem libs de UI": usar só como inspiração de interação.
- Catálogo visto na home (https://kokonutui.com): Cards (Metric Card, Uptime Card, Notification Stack...), Navigation (Command Palette, Smooth Drawer, Stack Panel, Status Island, Tool Dock), Feedback (Inline Alert, Empty State), Backgrounds (Topo, Halftone, Rain Glass). Não há componentes chamados "spotlight" nem "border beam" no catálogo.
- Metric Card (https://kokonutui.com/docs/components/metric-card): gráfico focável com setas, Home/End, Esc, valor falado via `aria-valuetext`/`aria-live`, animações desligadas com `prefers-reduced-motion`. É o melhor modelo de acessibilidade do conjunto.

| Padrão | Como fazer em CSS puro |
|---|---|
| Painel de vidro (ficha do nó) | `background: var(--surface); backdrop-filter: blur(14px) saturate(1.15); border: 1px solid var(--border);` com `@supports not (backdrop-filter: blur(1px))` caindo para `--surface-solida`. |
| Spotlight no card | `radial-gradient(240px circle at var(--mx) var(--my), var(--brilho), transparent)` com `--mx/--my` atualizados em `pointermove`. Só em cards da legenda, nunca sobre o canvas. |
| Border beam | Borda com `conic-gradient` girando via `@property --ang`. Opcional, decorativo; desligar em `prefers-reduced-motion`. Suporte do `@property` não verificado. |
| Command palette | `<input role="combobox" aria-expanded aria-controls>` + `<ul role="listbox">` + `aria-activedescendant`; atalho `/`; Esc fecha. |
| Status island / alerta inline | Faixa fixa sobre o mapa com `role="status"`, usada no aviso de corte (padrão 8). |

## (a) 8 padrões priorizados

**1. Super-nó "+N" para folhas de um hub** (esforço M)
- Origem: agrupamento do Linkurious, que nasce recolhido, mostra um círculo com selo de contagem e abre com duplo clique (https://doc.linkurious.com/user-manual/latest/nodegrouping/); `addNodeGrouping` do Ogma (https://doc.linkurious.com/ogma/5.3/tutorials/transformations); agregar para não expor o "hairball" (https://cambridge-intelligence.com/how-to-fix-hairballs/).
- Resolve: nuvem de 300 folhas. O hub passa a ter poucos filhos agregados por tipo (ex.: "+212 empresas").
- Aplicar: antes de montar `elements`, folhas de grau 1 de um hub com mais de K vizinhos (K = 12) viram um nó `grupo:<hub>:<tipo>` com `data.n` e `data.membros`. Rótulo `"+" + n`, forma `round-rectangle`, borda tracejada `--borda-forte`. Clique abre os N maiores por valor em anel (`concentric`, ou `fcose` incremental) e deixa um nó "restantes". Não usar compostos do Cytoscape (ver tabela b).

**2. Profundidade progressiva ao redor do foco** (M)
- Origem: foco por graus do Kumu, com `+`/`-` e Esc (https://docs.kumu.io/guides/focus); profundidade do grafo local no Obsidian (https://obsidian.md/help/plugins/graph); expansão com limite de vizinhos no Neo4j Bloom (https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/bloom-scene-interactions/).
- Resolve: mapa que tenta mostrar tudo de uma vez.
- Aplicar: abrir em profundidade 1 com os top-N por valor; controle "Camadas: 1 | 2" e botão "ver mais vizinhos" com limite por clique. Cada expansão roda `cy.layout({name:'fcose', randomize:false, fit:false})` para preservar posições. Esc volta ao estado inicial.

**3. Rótulos por importância (zoom semântico)** (P)
- Origem: `font-cutoff` do Kumu, que esconde rótulos abaixo de um tamanho (https://docs.kumu.io/overview/advanced-editor-hub/settings-reference); limiar de desvanecer texto no Obsidian; regras de rótulo do Cambridge Intelligence: encurtar, tooltip para o completo, esconder o ilegível (https://cambridge-intelligence.com/10-rules-great-graph-design/).
- Resolve: rótulos sobrepostos e truncados.
- Aplicar: classes `r1` (deputado + top 12 por valor, sempre), `r2` (aparece com zoom >= 1,2), `r3` (só hover/seleção). No estilo: `min-zoomed-font-size: 9`, `text-wrap: ellipsis`, `text-max-width: 110px`, `text-outline-color` = cor de fundo do tema com `text-outline-width: 3` (halo), `z-index` maior para `r1`. Texto completo no painel lateral. Propriedades confirmadas em https://raw.githubusercontent.com/cytoscape/cytoscape.js/master/documentation/md/style.md

**4. Tamanho do nó = valor, com escala raiz e legenda de escala** (P)
- Origem: tamanho por propriedade em escala linear ou logarítmica no Linkurious (https://doc.linkurious.com/user-manual/3.1/node-size); "size by" do Kumu (https://docs.kumu.io/guides/decorate/data-driven-decorations); raio mín./máx. no Flourish (https://helpcenter.flourish.studio/hc/en-us/articles/8761553784719-Network-graph-an-overview).
- Resolve: tamanho sem significado.
- Aplicar: pré-calcular `data.tam = 14 + 30*sqrt((v-min)/(max-min))` (área proporcional ao valor; o `mapData` do Cytoscape é linear e deixa um outlier engolir o resto). Piso de 14 px para alvo de toque. Legenda mostra 3 círculos de referência com R$ formatado. Nós sem valor: tamanho fixo e fundo vazado.

**5. Legenda viva: nós, arestas e contagens como filtro** (M)
- Origem: painel de legenda do Neo4j Bloom, que lista categorias e tipos de relação, conta o que está visível e seleciona ao clicar (https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/legend-panel/); legenda ao lado do gráfico, com o mesmo fundo (Cambridge Intelligence, link do padrão 3).
- Resolve: legenda sem arestas.
- Aplicar: lista HTML com `<button aria-pressed>` por tipo de nó (forma + cor + "12 de 40 visíveis") e por tipo de aresta (amostra em SVG inline com o mesmo traço). Alternar aplica `.oculto {display:none}` aos elementos do tipo. Arestas: cor neutra, tipo = estilo de traço, certeza = traço sólido/tracejado/pontilhado (mesma regra "certeza nunca só cor" do projeto).

**6. Busca de nó com foco animado** (M)
- Origem: busca do Bloom (https://neo4j.com/docs/bloom-user-guide/current/bloom-tutorial/search-phrases-advanced/); modo "prompt" do Kumu, em que o usuário digita nomes para montar o mapa (página do foco); combobox de teclado inspirado na Command Palette do KokonutUI.
- Resolve: não dá para achar um sócio ou município específico.
- Aplicar: campo acima do mapa; filtra `cy.nodes()` por `label` sem acento (`normalize('NFD')`), mostra até 8 resultados com tipo e valor; ao escolher, `cy.animate({center:{eles:n}, zoom:1.6},{duration:260})`, classe `.achado` (halo `underlay`) e abre a ficha. Se o nó está dentro de um super-nó, expandir antes. Duração 0 com `prefers-reduced-motion`.

**7. Foco por vizinhança + ficha lateral de vidro** (M)
- Origem: foco do Kumu; Inspector do Bloom (duplo clique abre os detalhes); destaque que baixa a opacidade do resto da rede no Flourish; painel de conhecimento do Google, com nome, fatos e retorno de erro (https://support.google.com/knowledgepanel/answer/9787176).
- Resolve: ler as ligações de um nó no meio da malha.
- Aplicar: `mouseover`/`tap` em nó adiciona `.dim` a tudo que não está em `n.closedNeighborhood()` (`opacity: .15`, arestas `.08`) e `.vizinho` aos demais. Ficha em `<aside>` com o estilo de vidro da seção 0: nome, tipo, valor, certeza em texto, lista de ligações por sentido (as listas já existentes) e link da fonte oficial. Sem `tap`, o foco some no `mouseout`; com `tap`, trava até Esc.

**8. Aviso de corte com composição do que foi omitido** (P)
- Origem: limite de vizinhos por expansão do Bloom (link do padrão 2); "Dismiss" do Bloom, que diferencia ocultar de remover; princípio de revelar sob demanda (Cambridge Intelligence, regra 6).
- Resolve: mapa cortado sem dizer o quê.
- Aplicar: faixa `role="status"` no topo do canvas: "Mostrando 60 de 312 ligações. Fora do mapa: 190 empresas de menor valor, 40 proposições, 22 municípios." com chips por tipo e botão "ver todas em lista". A lista é uma `<table>` paginada, que também é a alternativa acessível ao canvas. O critério de corte (maior valor) vem escrito.

## (b) Extensões e técnicas do Cytoscape

| Item | Versão | Licença | Tamanho | Veredito |
|---|---|---|---|---|
| cytoscape | 3.35.0 | MIT | 441,9 kB min / 138,9 kB gzip (bundlephobia) | Base. |
| cytoscape-fcose | 2.2.0 | MIT | 121,6 kB min; 8,7 MB descompactado no npm (inclui dist). O gzip de 718 B da bundlephobia é implausível, descartado | Já em uso. Aceita compostos, layout incremental, `fixedNodeConstraint`. `packComponents` pede cytoscape-layout-utilities (1.1.1, MIT, 1,0 MB descompactado). |
| cytoscape-expand-collapse | 4.1.1 (28/08/2024) | MIT | 31,0 kB min / 8,9 kB gzip; 1,7 MB descompactado | Não. Exige nós compostos, o README diz que o repositório não é mais mantido, e o padrão 1 sai mais simples na camada de dados. |
| cytoscape-popper | 4.0.1 (20/08/2024) | MIT | 3,3 kB min / 1,3 kB gzip | Opcional. Não traz Popper nem Floating UI; exige `popperFactory` com lib externa. Sem ela, um `<aside>` posicionado com `node.renderedPosition()` basta. |
| cytoscape-node-html-label | 1.2.2 (27/01/2021) | MIT | 622 kB descompactado; min/gzip não obtidos | Não. Sem releases desde 2021 e cada rótulo vira DOM, caro com centenas de nós. |
| Layout `concentric` (nativo) | 3.35.0 | MIT | 0 | Sim para a expansão de grupo e para anel por tipo. `concentric(n)` devolve o valor que define o anel, `levelWidth` agrupa níveis, `minNodeSpacing` e `avoidOverlap` evitam colisão. |
| `min-zoomed-font-size`, `text-wrap: ellipsis`, `text-background-*`, `text-outline-*`, `underlay-*`, `z-index` (nativos) | 3.35.0 | MIT | 0 | Sim (padrões 3, 6, 7). Rótulos podem aparecer um pouco abaixo do limiar por otimização. |
| Zoom semântico | n/a | n/a | 0 | Técnica, não pacote: ouvir `zoom` com `debounce` e alternar classes `r2`/`r3`. |
| Overlay de vidro | n/a | n/a | 0 | CSS puro sobre o contêiner do canvas (seção 0). `backdrop-filter` só funciona sobre DOM, nunca dentro do canvas. |
| Arestas `haystack` | 3.35.0 | MIT | 0 | Opcional para centenas de arestas retas (mais rápidas, sem setas). Perde seta de direção, então só quando a direção for dada por outro canal. |

## (c) Paleta e codificação visual

Tokens já existentes, sem cor nova. Contraste calculado à mão (luminância WCAG 2.x, margem de erro de uns 0,1); conferir com uma ferramenta antes de fechar.

| Token | Claro (fundo `#eef3f4`) | Escuro (fundo `#070b0f`) |
|---|---|---|
| `--no-deputado` | `#006a7c` 5,6:1 | `#5fe3f5` 12,9:1 |
| `--no-partido` | `#a86b00` 3,9:1 | `#e8b84a` 10,7:1 |
| `--no-empresa` | `#8a2f9c` 6,3:1 | `#e08cff` 8,8:1 |
| `--no-municipio` | `#0b6fa0` 4,9:1 | `#6db6ff` 9,2:1 |
| `--no-proposicao` | `#b4452a` 4,9:1 | `#ff8f66` 8,8:1 |
| `--no-pessoa` | `#5a5f8a` 5,5:1 | `#aab4e0` 9,7:1 |
| Arestas `--borda-forte` | `#70858e` 3,5:1 | `#5b7580` 4,0:1 |
| Texto `--muted` | `#465b64` 6,4:1 (6,9 na superfície) | `#9db0b8` 8,8:1 (8,0 na superfície) |

Todas passam em 3:1 para objetos gráficos (WCAG 1.4.11, https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html). `--no-partido` claro (3,9:1) não passa em 4,5:1: usar só como preenchimento e borda, nunca como cor de texto. Rótulos usam `--fg` com halo da cor de fundo.

Regras:
- Forma duplica a cor: deputado `ellipse` com borda dupla, partido `hexagon`, empresa `round-rectangle`, município `diamond`, proposição `tag`, pessoa `ellipse` pequena. Motivo: no tema claro, deputado e município têm luminância quase igual (0,12 e 0,14) e matizes azulados; para daltônicos só a forma separa.
- Tamanho = valor (raiz quadrada); cor = tipo; traço da aresta = tipo de relação e certeza; espessura da aresta = valor, de 1 a 4 px. Cada canal codifica uma coisa só.
- Estados: normal, `.dim` (opacidade .15, decorativo), `.achado` e selecionado com anel `--acento` de 3 px. Anel de foco de teclado visível na legenda, na busca e na lista.
- Super-nó: fundo `--surface-2` (texto `--muted` 5,8:1 no claro, 7,5:1 no escuro), borda tracejada `--borda-forte` (3,1:1 e 4,0:1).
- Limitar a 6 matizes de nó; não usar vermelho/verde para "bom/ruim" (regra do Cambridge Intelligence). Esquema Okabe-Ito (referência de paleta segura, https://jfly.uni-koeln.de/color/) serve para novos tipos, não para trocar os atuais.
- Acessibilidade do canvas: o canvas não tem semântica. Oferecer a tabela do padrão 8, `aria-label` no contêiner e `aria-live` para "N resultados" na busca. Respeitar `prefers-reduced-motion`.

## (d) Não consegui verificar

- Behance: 403 em `behance.net/search/...`. Não vi nenhuma página do Behance.
- Dribbble: `dribbble.com/tags/network_graph` e `/search/network-graph` voltaram vazios. Só abri a coleção https://dribbble.com/andrewliebchen/collections/348712-Network (6 itens, títulos e autores; as imagens não foram analisadas). Não usei nenhum shot como fonte de padrão.
- Awwwards: abri https://www.awwwards.com/websites/data-visualization/ (32 sites listados, nenhum identificável como grafo de rede) e https://www.awwwards.com/inspiration/data-visualization-apiary-life (só tags: tema escuro, preto). Não encontrei vencedor de grafo; nada foi inferido.
- KokonutUI: páginas individuais de componentes não detalham interação (a de Command Palette só trouxe instalação); só Metric Card foi lido por inteiro. Termos da licença Pro e suporte a `@property`/`backdrop-filter` nos navegadores-alvo não verificados.
- npm.com devolve 403; versões e licenças vieram de registry.npmjs.org. A bundlephobia respondeu 429 para o node-html-label (min/gzip ausentes) e deu gzip implausível para o fcose.
- Obsidian: não há "tamanho por número de links" confirmado como recurso nativo (só pedidos no fórum e plugins). Linkurious: não achei legenda para nós agrupados. Ogma: licença comercial não conferida. Flourish: não achei busca de nó. Google: o layout detalhado do painel não está na página consultada.
- Valores de contraste foram calculados manualmente, sem ferramenta. Desempenho de rótulos com 300 nós não foi medido. O hex do Okabe-Ito não consta na página aberta.
