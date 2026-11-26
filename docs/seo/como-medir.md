# Como medir a presença do projeto em respostas de IA e buscadores

Estado em 2026-11-26. Nenhum número foi medido até agora. Este documento diz como medir; ele **não promete resultado nem prazo**.

## O que existe

- `baseline.csv`: 30 prompts (os de `prompts.md`) x 5 motores (ChatGPT, Perplexity, Gemini, Claude, Google AI Overviews) = 150 linhas vazias para preencher à mão.
- Colunas: `prompt_id`, `prompt`, `motor`, `data`, `citou_o_projeto`, `fontes_citadas`, `posicao`, `observacao`.

## Passo a passo do baseline (antes de publicar qualquer página nova)

Tempo estimado: não medido. Cada linha exige abrir o motor, fazer a pergunta e ler a resposta; faça em blocos e por motor.

1. **Combine as condições uma vez e escreva-as no topo da planilha** (a primeira linha de `observacao` do primeiro registro pode guardar isso): conta com ou sem login, país e idioma do navegador, se o motor estava com busca na web ligada, modelo ou versão que o motor mostra. Use as mesmas condições em todas as rodadas. Resultado muda com a conta, a localização e o modo; sem padrão, não dá para comparar semanas.
2. **Abra uma conversa nova para cada prompt.** Uma conversa longa contamina a resposta seguinte.
3. **Cole o prompt exatamente como está no CSV.** Não reescreva.
4. **Registre a data** no formato AAAA-MM-DD.
5. **`citou_o_projeto`:** preencha com um destes valores fixos:
   - `link` = a resposta traz um link para o domínio do projeto;
   - `nome` = a resposta nomeia o Raio-X Parlamentar, mas sem link;
   - `nao` = nenhuma menção;
   - `erro` = menciona o projeto afirmando algo que o projeto não afirma (ver abaixo).
6. **`fontes_citadas`:** liste os domínios que a resposta cita ou linka, separados por ponto e vírgula (por exemplo `camara.leg.br;congressoemfoco.com.br`). Se o motor não mostra fontes, escreva `sem-fontes`. Esta coluna é a mais valiosa: ela alimenta o mapa de fontes (`fontes-ia.md`).
7. **`posicao`:** número de ordem em que o domínio do projeto aparece na lista de fontes do motor (1, 2, 3...). Vazio se não aparece. No Google AI Overviews, usar a ordem dos cartões de link; se o Overview não apareceu para o prompt, escrever `sem-overview` em `observacao`.
8. **`observacao`:** o que importa e não cabe nas outras colunas: concorrente nomeado, resposta recusada, resposta com ranking de pessoas, resposta sem fonte, motor sem resposta, mudança do formato.
9. **Salve uma captura de tela** de cada resposta em que o projeto aparece e de cada resposta marcada `erro`, numa pasta fora do repositório (as capturas não podem conter dados pessoais de quem mede, como nome de conta ou e-mail). A captura é a prova, a planilha é o índice.
10. **Não use conta de uma pessoa do projeto para perguntas sobre pessoas reais por nome.** Os 30 prompts não citam nome de deputado; mantenha assim.

## O que registrar toda semana depois que as páginas forem ao ar

Mesmo conjunto fixo de 30 prompts, mesmas condições, mesmo dia da semana. Registrar:

| O que | Onde | Para que serve |
|---|---|---|
| Nova rodada dos 30 prompts x 5 motores | `baseline.csv` (copiar com a data da rodada) | Ver a tendência por prompt e por motor |
| Páginas publicadas ou revisadas na semana, com data | `calendario.md` (coluna "Feito") | Cruzar publicação com mudança de citação |
| Lista de domínios que mais aparecem | planilha derivada de `fontes_citadas` | Atualizar `fontes-ia.md` |
| Respostas `erro` e respostas com ranking de pessoas | `observacao` + captura | Corrigir página ou pedir correção |
| Sinais de acesso (abaixo) | planilha à parte | Distinguir "não chegou" de "chegou e não citou" |
| Search Console: consultas e páginas com impressão | exportação semanal | Trocar as hipóteses de `prompts.md` por consultas reais |

## Sinais de acesso (antes da citação)

- **Logs de acesso do site e do provedor de hospedagem:** procurar pedidos de robôs de IA e de buscadores. Quais robôs e quais nomes de agente de usuário aparecem **deve ser confirmado na documentação de cada empresa**; o projeto não tem essa lista verificada. Hoje não se sabe quais logs a hospedagem do site oferece; verificar.
- **Search Console e Bing Webmaster Tools:** cadastrar o domínio; ver páginas indexadas, erros de rastreio e consultas. Ainda não existe cadastro verificado neste estudo (a confirmar com os autores).
- **Referência de tráfego:** se o site tiver analytics, observar visitas vindas de domínios dos próprios motores. **Hoje não foi verificado se há analytics no site** (nenhum foi visto na leitura de `web/`). Se não houver, escolher uma ferramenta que respeite privacidade e não use CPF nem dado pessoal.
- Sem acesso de robô, não há citação possível. Se o robô não chega, o problema é de acesso ou de indexação (auditoria técnica), não de texto.

## Métricas e o que cada uma significa

Definições vêm do método usado no projeto (referência: guia de mensuração do método).

| Métrica | Como calcular | O que quer dizer | O que NÃO quer dizer |
|---|---|---|---|
| Presença por citação (share of citation) | prompts em que o motor linka o domínio do projeto, dividido pelos 30 prompts | O motor usou uma página do projeto como fonte | Que a resposta está certa, nem que alguém clicou |
| Presença por menção (share of mention) | prompts em que o nome do projeto aparece, com ou sem link | O motor conhece e nomeia o projeto | Que ele recomenda o projeto |
| Presença no corpo da resposta (share of answer) | prompts em que o texto da resposta usa informação que só existe nas páginas do projeto e cita a origem | O conteúdo foi aproveitado | Que a ideia é exclusiva do projeto; confirme na fonte |
| Taxa por motor | as três acima, separadas por motor | Onde o conteúdo funciona e onde não | Que o motor "prefere" ou "penaliza" o projeto |
| Fontes mais citadas | contagem dos domínios em `fontes_citadas` | Quem domina o nicho e onde ficam as lacunas | Que esses domínios são melhores |
| Respostas `erro` | contagem | Risco para pessoas e para o projeto | Que o projeto causou o erro; mas exige resposta |

Fórmula básica, por motor e no total: **presença = prompts com o projeto citado / 30**. Para comparar com outro projeto, aplique a mesma conta às mesmas respostas (basta somar a coluna de fontes).

## O que olhar nas respostas além de "citou ou não"

- **O motor repete o aviso de não acusação?** Se um motor cita o projeto, a resposta mantém "indício, não acusação" e o nível de certeza? Anote em `observacao`.
- **O motor cria ranking de pessoas?** Anote qual e se citou o projeto como fonte do ranking. Isto exige correção: o projeto não faz ranking.
- **O motor atribui ao projeto um número que o projeto não publica?** Marcar `erro` e registrar o texto.
- **Prompts de risco alto (P03, P10, P16, P19, P20, P21):** leitura obrigatória por duas pessoas.

## Limites honestos

- **A resposta de um motor de IA muda de uma consulta para outra.** A mesma pergunta pode dar fontes diferentes em horas ou dias diferentes. Uma rodada é uma amostra, não um valor. Por isso o método usa a tendência de várias semanas.
- **30 prompts é um conjunto pequeno.** Diferenças de poucos prompts entre semanas podem ser ruído. Não comemorar nem lamentar uma rodada isolada.
- **Os prompts são hipóteses sintéticas** (`prompts.md`); a medição só diz algo sobre eles, não sobre o que as pessoas realmente digitam.
- **A mesma pergunta em contas, países ou modos diferentes pode dar respostas diferentes.** A comparação só vale com as mesmas condições.
- **Mudança de versão do motor altera tudo sem aviso.** Anote o modelo ou a versão exibida quando houver.
- **Citação não é correção nem confiança.** Um motor pode citar o projeto e resumir mal. Por isso existe a leitura de `erro`.
- **Correlação com publicação não prova causa.** Se a citação subir depois de uma página, pode ter sido outra coisa (reportagem, link de terceiro, mudança do motor).
- **Não há meta numérica, nem prazo prometido.** Não escrever "chegaremos a X%" em relatório, apresentação ou página. Prazo típico para primeiros sinais citado pelo método é de semanas, e é referência do método, **não medida deste projeto**.
- **O baseline automático** (rodar prompts por API de cada motor e guardar em tabela) é possível, mas depende de chaves, custos e termos de cada serviço; não foi avaliado. Comece à mão: a planilha basta para provar o conceito.
- **Ferramentas pagas de monitoramento de IA** existem; o método sugere só adotar quando a planilha manual deixar de bastar. Nenhuma foi avaliada neste estudo.

## Quando revisar este documento

Depois do primeiro baseline (o que for difícil de preencher vira ajuste de coluna) e ao fim das 8 semanas do `calendario.md`.
