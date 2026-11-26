# Modelo de brief: página de termo do glossário

Uma página por termo em `/glossario/[termo]`. Hoje existe uma só página `/glossario` com 10 termos (`docs/glossario.md`, `web/src/lib/glossario.ts`); ela continua como índice e cada termo ganha URL própria.

- **Tipo:** glossário (uma definição por página)
- **Intenção:** descoberta ("o que é X")
- **Tamanho:** 150 a 300 palavras. Se passar disso, o conteúdo pertence a uma página de regra.

## Primeira frase citável

Uma definição, sem o termo repetido de forma circular: "[Termo] é [classe de coisa] que [diferença que importa]." Exemplo de forma: "Votação simbólica é a votação em que a Mesa proclama o resultado pela manifestação geral dos presentes, sem registrar o voto de cada deputado."

## Estrutura de H2 (fixa)

1. **O que é** (a definição; 1 a 2 frases)
2. **Por que importa para entender um deputado** (1 parágrafo; ligado a uma regra do projeto)
3. **Como o Raio-X trata isso** (qual regra usa o termo, em uma frase, com link)
4. **Onde ver o dado oficial** (link verificado)
5. **Erro comum** (um equívoco frequente; por exemplo, "gasto alto = irregular")
6. **Termos relacionados** (3 links internos)

## Schema.org

- `DefinedTerm` com `name`, `description` (igual à primeira frase), `inDefinedTermSet` apontando para o `DefinedTermSet` "Glossário do Raio-X Parlamentar" (URL `/glossario`), `url`.
- A página `/glossario` leva o `DefinedTermSet` com `hasDefinedTerm` listando todos.
- `BreadcrumbList` (Início > Glossário > Termo).
- Sem `FAQPage` nas páginas de termo (a pergunta já é o título).

## O que NÃO afirmar

- Definição jurídica como se fosse parecer. Se o termo é jurídico (trânsito em julgado, presunção de inocência), citar o dispositivo e dizer "em linguagem simples".
- Qualquer juízo sobre pessoas. Exemplos de termos são sempre impessoais.
- Valores de limite da cota ou de qualquer prazo sem a fonte aberta e a data.

## Aviso de não acusação

Só nos termos que tocam em achado (CEIS/CNEP, circuito doador-sócio, indício, presunção de inocência): uma linha com o aviso padrão.

## Lista de termos (prioridade de publicação)

| Slug | Termo | Definição-base (reaproveitar do glossário atual) | Regra ligada | Fonte oficial a linkar | Prompts |
|---|---|---|---|---|---|
| `fator-de-certeza` | Fator de certeza (CF) | Número de 0 a 1 que diz o quanto o sistema confia numa conclusão | todas | Shortliffe e Buchanan, 1975 (referência) | P23 |
| `votacao-simbolica` | Votação simbólica | Aprovada por acordo ou manifestação geral; não existe registro individual | R02 | guia da Câmara sobre votação | P08 |
| `votacao-nominal` | Votação nominal | Cada voto fica registrado com o nome do deputado | R01, R02 | dados de votações nominais da Câmara | P08, P09 |
| `governismo` | Taxa de governismo | Parte das votações nominais com orientação do governo em que o deputado votou como o líder do governo orientou | R01 | Câmara (votações) | P06 |
| `orientacao-do-governo` | Orientação do governo | Recomendação do líder do governo sobre como votar | R01 | Câmara (votações) | P06 |
| `ceap` | CEAP, cota parlamentar | Verba mensal para despesas do mandato (passagem, combustível, escritório) | R03, R04 | https://www.camara.leg.br/transparencia/gastos-parlamentares | P01, P02 |
| `emenda-parlamentar` | Emenda parlamentar | Parte do orçamento que o deputado indica para um destino | R07 | CGU (a confirmar) | P12 a P16 |
| `emenda-pix` | Emenda Pix (transferência especial) | Transferência direta a estados e municípios, com menor rastreabilidade | R07 | CGU e Senado (a abrir) | P12, P15 |
| `ceis-cnep` | CEIS e CNEP | Cadastros de empresas punidas e impedidas de contratar com o governo; **não são listas equivalentes** | R03 | Portal da Transparência (a confirmar em navegador) | P17, P18 |
| `qsa` | QSA | Quadro de sócios e administradores de uma empresa | R06 | Receita Federal (a confirmar) | P20 |
| `pep` | PEP | Pessoa politicamente exposta | (ficha) | CGU/OpenSanctions (ver `DATA_LICENSES.md`: uso não comercial) | |
| `z-score-robusto` | Z-score robusto | Medida de quão longe um valor está da mediana do grupo, usando um desvio que aguenta valores extremos | R04 | referência estatística a escolher | P05 |
| `presuncao-de-inocencia` | Presunção de inocência | Ninguém é culpado até o trânsito em julgado de condenação | R08 | Constituição, art. 5º, LVII (link a confirmar) | P21 |
| `transito-em-julgado` | Trânsito em julgado | Quando não cabe mais recurso | R08 | a escolher | P21 |
| `lacuna-de-dado` | Lacuna de dado | Falta de registro; não é o mesmo que zero | R05, R08 | | |
| `encadeamento-progressivo` e `encadeamento-regressivo` | Encadeamento progressivo e regressivo | Dos fatos às conclusões; ou de um objetivo aos fatos que o provam | motor | relatório, seção 3.3 | P24 |
| `guardrail` | Guardrail (regra de proteção) | Regra que impede o sistema de tirar uma conclusão indevida | R02, R08 | | P26 |
| `trilha-de-prova` | Trilha de prova | O caminho passo a passo da conclusão até a fonte | explicação | relatório, seção 3.5 | P26 |
| `pseudonimizacao` | Pseudonimização | Trocar um identificador (CPF) por um código sem a chave | LGPD | ADR-006 | P29 |

**Ordem de publicação:** fator de certeza, votação simbólica, CEAP, governismo, emenda Pix, CEIS/CNEP, presunção de inocência, depois os demais.
