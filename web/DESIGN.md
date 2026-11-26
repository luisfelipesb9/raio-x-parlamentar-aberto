# DESIGN.md — Raio-X Parlamentar (Onda 5, identidade visual)

Contrato visual do `web/`. Fonte da verdade para tokens (`src/app/globals.css`) e componentes. Se algo aqui conflitar com um efeito, o efeito perde: a11y e as regras éticas vêm primeiro.

**Evidências usadas (honestas sobre o alcance).** Pesquisa via WebSearch, só trechos de resultado, sem abrir as páginas:
- Awwwards: "Missing" (SBS, SOTD 2019, paleta preta com acento teal, jornalismo investigativo), "Searching for Syria" (SOTD 2017) e "Dataveyes" (SOTD 2014) — *observado em resultado de busca*.
- Dribbble: coleções "Data Visualization" e "FUI" (interfaces futuristas); uma referência de HUD descreve linhas de varredura animadas, cartões translúcidos e bordas luminosas — *observado em resultado de busca*.
- Speckyboy, "x-ray effects in web design" (ver através das camadas da frente) — *observado*.
- Não abri Behance (a busca não devolveu páginas dele) nem capturei screenshots de nenhuma referência. O restante é *inferência* a partir do brief ("raio-x": varredura, camadas translúcidas, grão, luminescência).

**Keep** das referências: fundo escuro de alto contraste com um único acento luminoso; densidade de dado com respiro; camadas translúcidas; varredura como gesto de "análise em andamento".
**Change**: nada de HUD militar/sci-fi literal, nada de ciano neon saturado em tudo, nada de caveiras/alvos. O tema é jornalismo de dados, não ficção científica.
**Não copiar**: marcas, layouts exatos, ilustrações ou textos de nenhuma referência.

## 1. Visual Theme & Atmosphere
Conceito **"raio-x"**: o sistema ilumina o que já é público, em camadas. A pessoa vê *através* da superfície (política → dinheiro → relações). Três gestos recorrentes: **varredura** (uma linha de luz que passa sobre o conteúdo), **camadas translúcidas** (vidro fosco sobre grade), **luminescência contida** (brilho só no que importa: acento, nó selecionado, selo de certeza alta).
Dois modos com a mesma identidade. **O claro é o padrão**: o site abre claro mesmo com o sistema em modo escuro, e o escuro só entra por escolha explícita no botão de tema (gravada em `localStorage`). **Escuro = chapa de raio-x** (azul-quase-preto, acento ciano-gelo) e **claro = negatoscópio** (branco azulado, tinta quase preta, acento petróleo). O tom continua sóbrio: o efeito decora o dado, nunca o substitui. Grão de ruído sutil e grade técnica de fundo.

## 2. Color
Um único acento por modo. Certeza **nunca** depende de cor e **nunca** usa verde/vermelho (não sugerir inocência/culpa).

| token | escuro (chapa) | claro (negatoscópio) | uso |
|---|---|---|---|
| `--bg` | `#070b0f` | `#eef3f4` | fundo |
| `--surface` | `rgba(16,25,33,.64)` | `rgba(255,255,255,.72)` | vidro dos cartões |
| `--fg` | `#e8f1f4` | `#0b1a20` | texto |
| `--muted` | `#9db0b8` | `#465b64` | texto secundário (≥ 4,5:1) |
| `--border` | `rgba(150,215,230,.16)` | `rgba(11,26,32,.16)` | divisórias |
| `--acento` | `#5fe3f5` | `#006a7c` | **único acento**: foco, CTA, varredura, nó central |
| `--acento-fg` | `#04181d` | `#ffffff` | texto sobre acento |
| `--brilho` | `rgba(95,227,245,.35)` | `rgba(0,106,124,.18)` | glow (só decorativo) |
| `--aviso` | `#e8b84a` | `#7a5200` | "indício" e "mapa cortado" (âmbar, não é verde nem vermelho) |
| `--perigo` | `#ff8f66` | `#a5380f` | borda de empresa sancionada e erros (coral, sempre com texto) |

Semântica de certeza (texto + barras + estilo): **alta** = preenchido com acento; **média** = translúcido com borda do acento; **indício** = contorno âmbar; **inconclusivo** = tracejado cinza. Nós do grafo: forma distinta por tipo + cor (deputado = acento; partido âmbar; empresa magenta; município ciano-azulado; proposição coral; pessoa lilás-cinza).
Gradientes só como luz (radial glow, vinheta); nunca gradiente "de confiança" azul→roxo.

## 3. Typography
**Manrope** variável (200–800), carregada via `next/font/google`, única família. Hierarquia por peso e tamanho, não por troca de fonte.
- Display/H1: 800 → 700, `clamp(2.25rem, 7vw, 4.25rem)`, tracking `-0.03em`, leading 1.02. Palavras de ênfase em 200 (extra-light) para contraste de peso.
- H2: 700, `clamp(1.5rem, 3.6vw, 2rem)`, `-0.02em`. H3: 650, 1.2rem.
- Corpo: 400, 1rem/1.6, tracking 0, `max-width: 68ch`.
- Eyebrow/rótulos: 600, 0.75rem, MAIÚSCULAS com `0.1em`.
- Números grandes: 200–300 (ExtraLight) com `font-variant-numeric: tabular-nums`, tracking `-0.04em`.
- Sem justify. Máximo 4 pesos em uso: 200, 400, 600, 800.

## 4. Spacing & Grid
Escala 4/8/12/16/24/32/48/72/112 px. Container `72rem`, gutter 16 px mobile e 24 px ≥ 48rem. Grid de 12 colunas no desktop só para hero e ficha (índice 13rem + conteúdo). Mobile 375 px: uma coluna, sem scroll horizontal, alvos ≥ 44 px. Fundo com grade técnica de 48 px (linhas de 1 px a 6% de opacidade) e marcas de registro nos cantos do hero.

## 5. Layout & Composition
- **Home**: hero a dois planos (texto à esquerda; scanner SVG à direita no desktop, atrás do texto no mobile), tira de números que contam, ticker de termos, busca em vidro, grade de cartões.
- **Ficha**: cabeçalho com foto em anel luminoso, índice sticky numerado, seções reveladas no scroll, cartões de alerta em vidro com borda luminosa.
- **Grafo**: moldura com grade e vinheta, painel lateral em vidro.
- **Perguntar / Comparar / Glossário**: colunas estreitas, o dado é o herói; varredura só no cabeçalho.
Assimetria controlada: texto alinhado à esquerda, elementos decorativos sangram para fora da coluna sem causar overflow (`overflow: clip` no contêiner).

## 6. Components
Logo/símbolo próprio (SVG: anel + crosshair + linha de varredura) com favicon (`icon.svg`) e imagem OG (`opengraph-image`). Botões (sólido com acento, secundário translúcido, mini). Cartão de deputado (vidro + holofote que segue o ponteiro). Cartão de alerta (vidro, borda luminosa em gradiente, selo). Selo de certeza (texto + 4 barras). Tooltip de termo. Ranking, árvore de prova, tabela de comparação. Contador animado. Ticker. Cursor-halo (só ponteiro fino). Estados: carregando (spinner + esqueleto), erro, vazio.

## 7. Motion & Interaction
Easing padrão `cubic-bezier(.23, 1, .32, 1)`; entradas 280–420 ms, microinterações 120–180 ms; só `transform` e `opacity`.
- Varredura do hero (loop 7 s), pulsos nos pontos de dado, rotação lenta do radar.
- Números contam de 0 ao valor em 1,1 s ao entrar na tela.
- Seções da ficha entram com fade + 12 px de subida (stagger 60 ms).
- Navegação com View Transitions API (cross-fade de 220 ms); sem suporte, navega normal.
- Hover magnético (≤ 6 px) em botões primários; holofote nos cartões; `:active` com `scale(.97)`.
- Grafo: brilho nos nós, arestas do nó selecionado "correm" (dash animado).
- **`prefers-reduced-motion: reduce` desliga TUDO**: varredura, contadores (mostram o valor final), reveal (conteúdo já visível), ticker (estático, quebra linha), magnético, cursor-halo, view transitions, dash do grafo.
- Efeitos pesados (cursor, magnético, animação de arestas) só carregam depois da hidratação e só com `pointer: fine` quando aplicável.

## 8. Voice & Brand
Português simples, direto, sem juridiquês e sem sensacionalismo. "Isto não é acusação; é o que os dados públicos mostram" aparece em toda tela com conclusão. Nunca "culpado", "suspeito" ou "esquema". Termos técnicos viram `<Termo>` com tooltip. Microcopy de botão é verbo: "Como sabemos disso?", "Perguntar", "Ver mapa de relações".

## 9. Anti-patterns
- Verde/vermelho para certeza; certeza só por cor.
- Gradiente azul→roxo, indigo `#6366f1`, neon em tudo, glow em texto corrido.
- Emoji como ícone; cartão arredondado com borda colorida só à esquerda.
- Número inventado: contadores só mostram dado real da API ou fato estrutural do sistema (rotulado).
- Efeito que impede leitura (varredura sobre parágrafo, ticker sem pausa, cursor que esconde o ponteiro).
- Animação sem `prefers-reduced-motion`; scroll horizontal em 375 px; LCP > 2,5 s.
