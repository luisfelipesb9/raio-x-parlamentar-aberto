# Briefs de conteúdo

Estado em 2026-11-26. Cada arquivo orienta quem vai escrever o texto final. O texto final não pode sair daqui sem passar por `../checklist-etica.md`.

## Índice

| Arquivo | Página que gera | URL sugerida | Tipo |
|---|---|---|---|
| `01-metodo.md` | Como o sistema chega às conclusões (pilar) | `/metodo` | Pilar |
| `_regra.md` | Modelo de página de regra (vale para R01 a R09) | `/regras/[id]` | Regra |
| `regras-notas.md` | Notas específicas de R01, R02, R03, R04, R05, R06 e R06b, R07, R08, R09 | `/regras/r01` ... `/regras/r09` | Regra |
| `_glossario-termo.md` | Modelo de página de termo + lista dos termos | `/glossario/[termo]` | Glossário |
| `faq.md` | Perguntas frequentes | `/faq` | FAQ |
| `estudantes-sistemas-especialistas.md` | Para estudantes de Sistemas Especialistas | `/estudantes` | Pilar para público técnico |
| `dados-e-api.md` | Dados e API | `/dados-e-api` | Documentação |

Também precisa de página índice `/regras` (lista de R01 a R09 com a pergunta que cada uma responde e o nível de certeza padrão). Não tem brief próprio: use o quadro "Resumo das regras" de `regras-notas.md`.

Páginas que já existem no site e **não** precisam de brief aqui: `/`, `/deputado/[id]`, `/perguntar`, `/comparar`, `/grafo`, `/fontes`, `/glossario` (a lista atual de termos vira a base dos termos individuais).

## Regras que valem para todos os briefs

1. **Escopo declarado em toda página:** "A base pública cobre 20 deputados de Minas Gerais, votações de 04/02/2025 a 27/03/2025, despesas da cota de 2024 e a eleição de 2022." Se isso mudar, atualizar em todas. Fonte: README e relatório.
2. **Primeira frase sob cada H2 = resposta autônoma**, copiável sem o contexto.
3. **Dado com fonte e data.** Número do próprio projeto cita o arquivo (relatório, verificação) e a data da coleta. Número de terceiros só entra depois de abrir a fonte original. Os números aprovados para uso estão na seção "Números que podem ser usados" abaixo.
4. **Sem nome de deputado nos exemplos de achado.** Use a base fictícia da demonstração (`make demo`) ou números agregados. A tabela de comparação externa tem nomes de deputados reais: **não copiar**.
5. **Sem marketês.** Não usar "líder", "completo", "inovador", "revolucionário", "o melhor".
6. **Sem ferramentas de IA como autoras ou assistentes** em texto, créditos, schema ou metadados.
7. **Data visível** de publicação e de última revisão; data de coleta dos dados quando a página usa número.
8. **Links só para URLs verificadas** (listas em cada brief). Link marcado "a confirmar" não entra no texto final até alguém abrir.
9. **Autor no schema:** os autores do projeto no relatório são Luis e Pedro Rodrigues (Unimontes). Confirmar com eles o nome completo e se querem aparecer como `Person` ou só como `Organization`. Não inventar sobrenome.

## Aviso padrão de não acusação (usar nas páginas de regra, no FAQ e em qualquer página que mencione achado)

> Isto não é acusação; é o que os dados públicos mostram. Um achado é uma pista para quem quiser investigar, não uma conclusão sobre a conduta de alguém. Processo sem condenação definitiva não é culpa. Confira sempre na fonte oficial indicada. Para corrigir um dado, veja a política de uso e correção.

Origem do texto: README e `docs/politica-de-uso-e-correcao.md`.

## Números que podem ser usados (todos do repositório; citar o arquivo)

| Número | Onde está |
|---|---|
| 9 regras e uma variante (R01 a R09 e R06b); 2 guardrails (R02, R08) | `docs/relatorio/relatorio.md` |
| 20 deputados de MG na amostra; 40 findings na amostra | relatório, seção 8 |
| Votações de 04/02 a 27/03/2025; despesas CEAP de 2024; eleição de 2022 | relatório, seção 8 |
| R01 CF 0,95, penalidade x0,7 com menos de 30 votações; exemplo 0,665; mínimo 10 votações; limiar 0,7 | `knowledge/rules/R01_governismo.yaml`, relatório 3.4 |
| R04 CF 0,5; z maior que 3,5; mínimo 5 deputados | `R04_outlier_ceap.yaml` |
| R07 CF 0,6; razão mínima 3; penalidades 0,8 e 0,7 | `R07_concentracao_emendas.yaml` |
| Níveis: alta a partir de 0,7; média a partir de 0,4; indício a partir de 0,2; inconclusivo abaixo de 0,2 | relatório 3.4 |
| 145 votações no bruto, 24 nominais, 22 com orientação Sim/Não; 44 conferências, 0 divergência (2026-11-26) | `docs/relatorio/verificacao.md` |
| R02 removeu 121 votações simbólicas na amostra | relatório, seção 8 |
| Comparação R01 x Radar do Congresso: mesma classificação em 13 de 14; diferença média 12,6 pontos; consulta de 2026-11-25 | `docs/relatorio/comparacao-externa.md` |
| 472 testes Python, 50 unitários e 45 e2e no web | relatório, seção 8 (conferir a contagem antes de publicar) |

**Não usar:** "2024" como ano das votações (são de 2025; o próprio `comparacao-externa.md` registra esse erro de texto); qualquer percentual de apoio da Câmara ao governo que não tenha sido aberto na fonte; "R06 dispara" (com dados reais o QSA vem mascarado e só a R06b é alcançável).

## Estado do site que afeta os briefs (da leitura de `web/`)

- Não há `sitemap`, `robots` nem `llms.txt` em `web/` (busca por esses nomes, 2026-11-26). Isso é assunto da auditoria técnica, fase 2; os briefs não dependem dele para serem escritos, mas **a publicação depende**.
- Site em produção segundo `docs/HANDOFF.md`: https://raio-x-web-delta.vercel.app. A API tem `/saude` e documentação em `/docs`.
- A conferência de que o conteúdo aparece no HTML sem executar JavaScript **não foi feita** (sem Bash). Fica para a auditoria.
