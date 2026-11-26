# Textos das páginas públicas de conteúdo

Revisão: 2026-11-26. Os textos finais das páginas de conteúdo do site. Eles partem dos briefs aprovados em `docs/seo/briefs/` e foram conferidos contra `knowledge/rules/`, `docs/relatorio/`, `docs/politica-de-uso-e-correcao.md`, `DATA_LICENSES.md`, `docs/licencas/atribuicao.md` e `docs/adr/`. Antes de publicar, cada página passa por `docs/seo/checklist-etica.md`.

O glossário por termo não está aqui: ele será gerado a partir de `docs/glossario.md`.

## Arquivos

| Arquivo | Página | `slug` |
|---|---|---|
| `metodo.md` | `/metodo` | `metodo` |
| `para-estudantes.md` | `/para-estudantes` | `para-estudantes` |
| `dados-e-api.md` | `/dados-e-api` | `dados-e-api` |
| `faq.md` | `/faq` | `faq` |
| `regras/R01.md` ... `regras/R09.md` e `regras/R06b.md` | `/regras/R01` ... `/regras/R09` e `/regras/R06b` | `R01` ... `R09`, `R06b` |

O brief sugeria `/estudantes` para a página de estudantes. O `slug` aqui é `para-estudantes`, conforme o nome do arquivo pedido; a rota final é decisão de quem gera as páginas. A página índice `/regras` não tem arquivo próprio: use o quadro "Resumo das regras" de `docs/seo/briefs/regras-notas.md`. O brief previa R06 e R06b na mesma página; aqui são dois arquivos.

## Contrato de formato

Cada arquivo é Markdown com frontmatter YAML entre `---`:

```
---
slug: metodo
titulo: "..."
descricao: "..."
resposta: "..."
atualizado: 2026-11-26
---
```

- `slug`: igual ao nome do arquivo sem `.md`. Nas regras mantém a caixa do nome do arquivo (`R01`, `R06b`).
- `titulo`: até 70 caracteres.
- `descricao`: até 160 caracteres, uma frase.
- `resposta`: a primeira frase citável, resposta autônoma e factual à pergunta da página, até 240 caracteres.
- `atualizado`: data de revisão no formato AAAA-MM-DD.
- Só nas regras, o campo extra `regra`, com o id (`R01`).

Corpo:

- só `##` e `###`; nunca `#`, porque o título vem do frontmatter;
- parágrafos, listas com `-` e `1.`, **negrito**, *itálico* e links;
- sem tabelas, sem HTML, sem imagens e sem blocos de código, exceto em `dados-e-api.md`, que tem um bloco com exemplos de requisição GET;
- a primeira frase de cada `##` responde à pergunta do título dele;
- links externos são `https` absolutos para fontes oficiais; links internos são caminhos como `/glossario#ceap`, `/deputados`, `/regras/R01` e `/metodo`;
- os parágrafos antes do primeiro `##` são a introdução: o aviso de não acusação e o escopo da base. Eles não são uma pergunta.

No `faq.md`, cada `##` é uma pergunta e o texto até o próximo `##` é a resposta (um a três parágrafos).

## Âncoras do glossário usadas

Os textos apontam para âncoras em `/glossario#...` (por exemplo `ceap`, `fator-de-certeza`, `votacao-simbolica`, `guardrail`, `qsa`, `emenda-pix`). Quem gera as páginas deve conferir se cada âncora existe. O glossário atual (`docs/glossario.md`) tem só dez termos; os demais termos citados (por exemplo `mediana`, `z-score-robusto`, `trânsito em julgado`) ainda precisam de entrada.

## Regras de conteúdo seguidas

- Nenhum nome de deputado real; exemplos só com a base fictícia da demonstração (`make demo`, ids 9900001 em diante, nomes com "(demo)").
- Números só do repositório; nenhum número de terceiros sem fonte aberta.
- O aviso de não acusação aparece no topo de cada página, e a política de correção é citada.
