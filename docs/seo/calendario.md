# Calendário de publicação: 8 semanas

Estado em 2026-11-26. Semana 1 começa na segunda-feira 2026-11-30 e a semana 8 termina em 2027-01-22. Qualidade acima de volume: uma ou duas peças por semana, cada uma revisada por pessoa antes de ir ao ar. Onde não há peça boa para publicar, a semana tem **atualização** de página existente, nunca texto de enchimento.

## Pré-requisitos (semana 0, até 2026-11-29). Sem isto, não publicar

1. **Auditoria técnica do site** (fase 2 do método; fora deste estudo). O que se sabe pela leitura de `web/`: não há `sitemap`, `robots` nem `llms.txt`; não foi checado se o texto aparece no HTML sem executar JavaScript. Publicar páginas que o robô não lê é escrever no vazio.
2. **Baseline** de `como-medir.md` rodado e salvo (30 prompts x 5 motores). Data da rodada: ______ (preencher).
3. **Fechar as pendências abertas** que travam links dos briefs: link do Portal da Transparência (CEIS, CNEP, emendas) aberto em navegador; endereço estável do repositório; nome dos autores no schema.
4. **Revisão de ética** (`checklist-etica.md`) nomeada: quem aprova cada página, com dois pares de olhos nas páginas de risco alto.
5. **Escolher a base de exemplos:** base fictícia da demonstração (`make demo`) para todas as capturas e exemplos.

## Rotina semanal (vale para todas as semanas)

| Dia | Tarefa |
|---|---|
| Segunda | Escolher a peça (ou a atualização) da semana; abrir todos os links que ela citará |
| Terça | Redigir a partir do brief; números conferidos contra `knowledge/rules/` e `docs/relatorio/` |
| Quarta | Revisão de fato (links, números) e revisão ética (`checklist-etica.md`); a segunda pessoa revisa as páginas de risco alto |
| Quinta | Publicar com data de publicação e de revisão visíveis; atualizar sitemap e llms.txt quando existirem; avisar os buscadores (Search Console, IndexNow) |
| Sexta | Registrar o que saiu e a data; rodada semanal de medição (`como-medir.md`); anotar erros de resposta de motor |

## Plano por semana

"Gancho de frescor" é o que dá motivo para a data de revisão da página mudar. Nenhum gancho abaixo promete atualização automática de dados: a coleta do projeto é manual (`make sample`), e a data de coleta deve aparecer em `/fontes`.

| Sem. | Datas | Publicação | Por que nesta ordem | Gancho de frescor | Prompts | Feito |
|---|---|---|---|---|---|---|
| 1 | 30/11 a 04/12 | (1) `/metodo` (pilar). (2) Termos `fator-de-certeza` e `votacao-simbolica` | O pilar dá contexto e confiança; os dois termos são pré-requisito de todas as regras | Data de coleta e escopo no topo; a verificação mais recente (44 conferências, 2026-11-26) com data | P05, P08, P23, P26 | ☐ |
| 2 | 07/12 a 11/12 | (1) `/regras/r02`. (2) `/regras/r01` | R01 é a regra com comparação externa e conferência bruto-banco-motor; R02 explica por que votação simbólica fica fora | Consulta comparativa com o Radar do Congresso datada (2026-11-25); refazer se a base for coletada de novo | P06 a P10 | ☐ |
| 3 | 14/12 a 18/12 | (1) `/regras/r04` com o termo `ceap`. (2) `/faq` | R04 responde "gasto alto é irregular?", que precisa de resposta cuidadosa; o FAQ consolida as perguntas de confiança já com duas regras no ar | Link para a tabela oficial da cota da Câmara com a data em que foi aberta | P01 a P05 | ☐ |
| 4 | 21/12 a 25/12 | `/regras/r03` com o termo `ceis-cnep` | Semana de festas: uma peça só. R03 tem CF alto (0,9) e ressalva forte; só publica com o link do Portal da Transparência confirmado | Data da consulta aos cadastros | P17 a P19, P28 | ☐ |
| 5 | 28/12 a 01/01 | **Sem página nova.** Atualização: `/fontes` com a data de coleta; revisão de `/metodo` e `/regras/r01` com o que a medição e os leitores mostraram | Virada de ano com pouco movimento; usar para corrigir e medir | O rodapé "última revisão" de três páginas | | ☐ |
| 6 | 04/01 a 08/01 | `/regras/r07` com o termo `emenda-pix` | Depende de fonte externa sobre emenda Pix já aberta e de revisão extra pelo risco médio (correlação, não causa) | Abrir os relatórios da Transparência Brasil e citar só números lidos neles | P12 a P16 | ☐ |
| 7 | 11/01 a 15/01 | (1) `/estudantes`. (2) `/dados-e-api` | Público técnico; `/dados-e-api` só depois de fechar com os autores os parâmetros e exemplos reais da API | Rodar `make verifica` e registrar data; exemplos `curl` testados na semana | P22 a P29 | ☐ |
| 8 | 18/01 a 22/01 | (1) `/regras/r08` com os termos `presuncao-de-inocencia` e `transito-em-julgado`. (2) Revisão de oito semanas | R08 é guardrail e deve chegar com a página de método já madura; a revisão fecha o ciclo | Resultado da oitava rodada de medição, copiado para o relatório | P21 | ☐ |

Total previsto: 11 peças novas (algumas com termos de glossário junto) e uma semana de atualização.

## Fica para depois das 8 semanas (decidir com a leitura da medição)

- `/regras/r05` (produção legislativa): risco de virar ranking; só publicar depois de decidir como mostrar sem ordenar.
- `/regras/r06` (doador-sócio-fornecedor), `/regras/r09` (merece atenção): alto risco de leitura como veredito; publicar só após revisão de ética por pessoa de fora da equipe e depois de o projeto ter lidado com correções reais nas outras páginas.
- Glossário restante (`qsa`, `pep`, `z-score-robusto`, `guardrail`, `trilha-de-prova`, `pseudonimizacao`, `encadeamento-*`, `lacuna-de-dado`) em lotes de dois por semana, junto de peças maiores.
- Páginas de comparação de ferramentas só com dado verificado de cada uma.

## Ganchos de data a avaliar (hipóteses, não medidas)

- A página de dados do TSE mostrava o ciclo de 2026 em 2026-11-26. O projeto usa a eleição de 2022. Uma nova legislatura começa em 2027; **a data de posse e o efeito disso na busca por "deputados" não foram verificados**. Se os autores quiserem cobrir o ciclo novo, é decisão de produto, não de conteúdo.
- O recesso do Congresso no fim do ano reduz votações novas; isso afeta o gancho de frescor da R01 (a janela de votações do projeto é de fev a mar de 2025 e não muda sozinha). **Datas do recesso não foram verificadas.**

## Critério de parada e ajuste

- Se uma página falhar na revisão ética, ela **não sai na semana**, e a semana vira atualização. Atrasar é aceitável; publicar com risco, não.
- Se duas rodadas de medição seguidas mostrarem `erro` de motor sobre o projeto, parar a publicação de páginas novas e corrigir as existentes.
- Revisar este calendário no fim da semana 4 com o que o baseline mostrou.
