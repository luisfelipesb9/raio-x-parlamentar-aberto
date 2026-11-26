# Mapa de fontes do nicho

Estado em 2026-11-26. Todas as datas de acesso abaixo são desta data, salvo quando indicado.

## Aviso sobre o que este mapa mede (leia antes)

**Não foi possível medir citações reais de motores de IA.** A pesquisa foi feita com busca web comum e leitura direta de páginas. Isso mostra quais domínios existem, o que cada um cobre e quais aparecem para perguntas parecidas com as do público. **Não mostra** quais domínios ChatGPT, Perplexity, Gemini, Claude ou Google AI Overviews citam hoje. Quem cita quem só se descobre rodando os prompts à mão em cada motor (`como-medir.md`). Tudo o que está em "Hipótese" abaixo é inferência a verificar.

Convenção usada nas tabelas:
- **Verificado** = abri a página ou li o resultado de busca na data indicada e o fato está nela.
- **Parcial** = a página abriu, mas o conteúdo útil não carregou (página que depende de JavaScript) ou o resultado veio só em trecho de busca.
- **Não verificado** = tentei e falhou, ou não tentei.
- **Hipótese** = deduzido; não confirmado em fonte.

## 1. Fontes oficiais (de onde o dado nasce)

| Domínio / página | O que cobre | Situação da verificação | URL e data de acesso |
|---|---|---|---|
| Câmara dos Deputados, Dados Abertos | API com coleções de deputados, partidos, blocos, órgãos, frentes, eventos, proposições, votações; documentação em `/swagger/api.html`; tutoriais e FAQ | **Verificado.** A página inicial lista essas coleções e os caminhos de documentação. Não cita CEAP nem arquivos na própria página | https://dadosabertos.camara.leg.br/ (2026-11-26) |
| Câmara, Portal da Transparência: gastos parlamentares | Tabela comparativa da cota (CEAP) da 57ª legislatura (2026) com filtros por deputado, UF ou partido, legislatura (57 a 52), ano e mês; botão que baixa CSV; "busca detalhada" em `/cota-parlamentar/` | **Verificado.** A página não informa data nem periodicidade de atualização | https://www.camara.leg.br/transparencia/gastos-parlamentares (2026-11-26) |
| Câmara, guia para jornalistas: cota parlamentar | Regras e valores da cota | **Parcial** (apareceu em resultado de busca; não abri) | https://www2.camara.leg.br/comunicacao/assessoria-de-imprensa/guia-para-jornalistas/cota-parlamentar (2026-11-26) |
| Câmara, Ato da Mesa 43/2009 (texto atualizado) | Norma da cota; limites mensais por estado; prazo de comprovação | **Parcial** (resultado de busca; resumo do buscador diz limites por UF e 90 dias para comprovar; conferir no texto antes de citar) | https://www2.camara.leg.br/legin/int/atomes/2009/atodamesa-43-21-maio-2009-588364-normaatualizada-cd-mesa.html (2026-11-26) |
| Câmara, guia para jornalistas: votação | Explica tipos de votação (simbólica, nominal, secreta) | **Parcial** (resultado de busca; o resumo diz que na simbólica o voto individual não é registrado) | https://www2.camara.leg.br/comunicacao/assessoria-de-imprensa/guia-para-jornalistas/votacao (2026-11-26) |
| Câmara, dados de votações nominais | Relatórios de votações nominais | **Parcial** (resultado de busca) | https://www2.camara.leg.br/atividade-legislativa/plenario/relatorios-da-atividade-legislativa/dados-de-votacoes-nominais (2026-11-26) |
| TSE, Dados Abertos | Prestação de contas eleitorais, candidaturas e resultados (a página mostra o ciclo 2026) | **Verificado.** A página inicial não cita licença; o repositório registra CC BY na página de cada conjunto de 2022 (`DATA_LICENSES.md`) | https://dadosabertos.tse.jus.br/ (2026-11-26) |
| CGU, Portal da Transparência (CEIS, CNEP, emendas) | Cadastros de empresas punidas; emendas parlamentares | **Não verificado.** Duas tentativas de abrir `portaldatransparencia.gov.br/sancoes/consulta` e `/emendas` retornaram HTTP 405. Descrição de CEIS/CNEP veio de resultado de busca de páginas de governos e da CGU | tentativa em 2026-11-26 |
| Receita Federal (CNPJ, QSA) | Sócios e administradores | **Não verificado** neste estudo; o repositório documenta que o QSA vem com CPF mascarado | ver `docs/relatorio/relatorio.md` |

**Hipótese:** os motores de IA devem tratar estas páginas oficiais como fonte primária para perguntas factuais ("o que é a cota parlamentar", "o que é votação simbólica"). O projeto **não deve tentar competir** nessas perguntas; deve linkar a elas e entrar com o que elas não têm (explicação de método, ressalvas, nível de certeza, cruzamento).

## 2. Projetos de transparência parecidos (concorrentes de atenção, e fontes metodológicas do projeto)

| Projeto | O que cobre | Situação da verificação | URL e data |
|---|---|---|---|
| Radar do Congresso (Congresso em Foco) | Índice de governismo por parlamentar e por partido, atualizado por votações. Reportagens de 2023 e 2024 citam média da Câmara de 72% de apoio ao governo e listas por deputado | **Parcial.** A página `radar.congressoemfoco.com.br/parlamentares/camara` abriu, mas só trouxe o título (depende de JavaScript). O que se sabe do método vem de reportagens do mesmo veículo, achadas por busca. O repositório registra que em 2026-11-25 a base exibida estava atualizada em 2026-10-02 (`comparacao-externa.md`) | https://radar.congressoemfoco.com.br/parlamentares/camara (2026-11-26); https://www.congressoemfoco.com.br/noticia/5508/governo-ou-oposicao-veja-o-alinhamento-de-cada-deputado-com-lula-nas-votacoes (resultado de busca, 2026-11-26) |
| Basômetro (Estadão) | Taxa de governismo; o método considera só votações com orientação do governo | **Parcial.** Busca retornou reportagens que citam a ferramenta, sem página atual do painel. O repositório registra "última atualização exibida: 20/01/2020" em 2026-11-25 | busca em 2026-11-26; `docs/relatorio/comparacao-externa.md` |
| Radar do Voto | Resultados eleitorais por município e emendas por cidade ("Radar das Emendas Federais"); parte exige cadastro; relatórios em PDF e planilha exigem conta; recursos avançados são pagos | **Verificado** (resumo da página inicial, sem abrir cada tela). Preços e planos mudam: não citar valores | https://radardovoto.com (2026-11-26) |
| Operação Serenata de Amor (Rosie e Jarbas) | Detecção de reembolsos suspeitos da cota, com painel Jarbas | **Verificado em parte.** O README no GitHub diz que Rosie e Jarbas recebem atualizações com menos frequência e descreve execução manual mensal da Rosie, sem data atual. O site citado é serenata.ai. O repositório do Raio-X registra o painel fora do ar (erro 522) em 2026-11-25 | https://www.github.com/okfn-brasil/serenata-de-amor (2026-11-26) |
| Querido Diário (Open Knowledge Brasil) | Busca em diários oficiais **municipais** | **Parcial.** Busca retornou descrição e cobertura com números divergentes entre fontes (12 capitais no lançamento; 350 cidades em resumo posterior); a página de documentação deu 404 ao abrir. Cobre município, não deputado federal | https://docs.queridodiario.ok.org.br/en/latest/what-is-it.html (404 em 2026-11-26); resultados de busca |
| Transparência Brasil | Levantamentos sobre emendas Pix (2023, 2024 e 2026 citados em imprensa e em PDFs da entidade) | **Parcial.** PDFs da entidade e reportagens apareceram em busca; não abri os relatórios. Antes de citar número, abrir o relatório original | https://www.transparencia.org.br/downloads/publicacoes/emendas_pix_2023.pdf e https://transparencia.org.br/downloads/publicacoes/emendaspix2024.pdf (resultados de busca, 2026-11-26) |
| Placar Congresso | Histórico de votos de parlamentares ligado à base da Câmara; criado por um deputado federal, segundo reportagem | **Parcial** (um resultado de busca, de veículo de imprensa). Autoria por parlamentar torna a fonte parcial; usar com cuidado | resultado de busca, 2026-11-26 |
| Parlametria, Radar Parlamentar, Radar da República, Elas no Congresso, Perfil Político | Citados no relatório como referência metodológica | **Não verificados neste estudo.** O status (ativo ou arquivado) vem do relatório do projeto, sem checagem nova | `docs/relatorio/relatorio.md` |

**Lacuna que aparece com mais clareza:** nenhum dos projetos acima, nas páginas que consegui ver, mostra num mesmo lugar votos, gastos, emendas, sanções e doações **com nível de certeza e trilha de explicação por conclusão**. Isto é o que o relatório do projeto afirma (seção 2) e **não foi verificado de forma independente aqui**: o que verifiquei foi só que as ferramentas acima, nas descrições que li, cobrem faixas separadas.

## 3. Imprensa que cobre o tema (fonte provável de citação, hipótese)

| Veículo | O que apareceu | Situação |
|---|---|---|
| Congresso em Foco | Reportagens sobre ranking de gasto da cota em 2026, governismo por deputado em 2023 e 2024, uso da cota com empresas de parentes e de doadores | **Verificado em resultado de busca** (vários links, 2026-11-26). Abrir o artigo antes de citar |
| Metrópoles, Gazeta do Povo, Estadão, The Intercept Brasil, Itatiaia, Correio da Manhã, Istoé Dinheiro, SBT News | Pelo menos um resultado de busca cada, sobre cota, emendas Pix ou governismo | **Verificado em resultado de busca**, conteúdo não aberto |
| Agência Câmara e Agência Senado (notícias oficiais) | Matérias sobre emendas, votação simbólica e cota | **Verificado em resultado de busca** |

**Hipótese:** o jornalismo de dados e a imprensa política pesam na resposta de motores que mostram links (Perplexity, Google AI Overviews). **Não medido.**

## 4. Fontes de conceito para o cluster "sistema especialista"

| Fonte | Cobre | Situação |
|---|---|---|
| Shortliffe e Buchanan, 1975 (artigo do modelo de fatores de certeza); Buchanan e Shortliffe, 1984 (livro, capítulo 10 em PDF da Universidade Columbia) | Origem do fator de certeza | **Parcial.** Apareceram em busca (PDF do capítulo 10, artigo da Microsoft Research sobre o modelo). Citar a referência bibliográfica completa do relatório |
| Wikipedia (MYCIN) e material acadêmico em português (por exemplo, repositório da UFRGS) | Definições gerais | **Parcial** (resultado de busca). **Hipótese:** é onde motores buscam a definição |

**Lacuna provável (hipótese):** exemplo **trabalhado em português**, com código e regras abertas, de fator de certeza aplicado a dados públicos reais. O relatório tem o exemplo da R01 (0,95 x 0,7 = 0,665). Não verifiquei se outra fonte em português traz algo equivalente.

## 5. Onde o Raio-X pode ocupar espaço (lacunas)

Cada linha liga uma lacuna a um prompt de `prompts.md` e a um brief. "Tipo de evidência" diz se a lacuna foi vista nas fontes ou é palpite.

| Lacuna | Prompts | Página (brief) | Tipo de evidência |
|---|---|---|---|
| Explicar **como** se calcula um índice de governismo, com o limiar, o mínimo de votações e o que fica de fora | P06, P07, P10 | `briefs/regra-r01` (seção em `regras-notas.md`) | **Vista:** as reportagens e a página do Radar que consegui ler descrevem o resultado; o relatório do projeto traz o método próprio. Falta conferir se o Radar publica o método em outra página |
| Dizer que **votação simbólica não gera voto individual** e por que isso muda a conta | P08, P09 | R02 e glossário | **Vista:** o guia da Câmara existe (resumo de busca); explicação ligada ao cálculo de governismo não foi encontrada. Não afirmo que ninguém faz |
| Cruzar **despesa da cota com sanção vigente na data do gasto** | P18, P19, P28 | R03 | **Hipótese.** Reportagens do Congresso em Foco cruzam cota com empresas de parentes e doadores, mas não achei, em busca, cruzamento sistemático com CEIS/CNEP |
| Explicar **limites de emendas Pix** (destino não rastreável antes de 2027) junto da concentração eleitoral | P12 a P15 | R07 | **Vista em parte:** levantamentos da Transparência Brasil tratam da falta de detalhamento; a ligação com votação por município aparece no Radar do Voto (parte atrás de cadastro) |
| Aviso claro de **o que o sistema não afirma** (ressalva por regra) | todos de risco médio ou alto | todas as regras | **Hipótese**, mas coerente com a política do projeto |
| Exemplo em português de **sistema especialista com explicação**, código aberto | P22 a P26 | `/estudantes` | **Hipótese** |
| **Armadilhas de dado**: limite de requisições da API da Câmara (HTTP 429), id de despesa que se repete, CPF mascarado no QSA | P27 a P29 | `/dados-e-api` | **Vista no projeto** (`DATA_LICENSES.md`, relatório), **não verificada** em outras fontes |

## 6. O que falta para este mapa virar medição

1. Rodar os 30 prompts em 5 motores e anotar as fontes que cada resposta cita (`baseline.csv`). Só então dá para dizer "o motor X cita o domínio Y".
2. Abrir a página do Radar do Congresso num navegador e registrar o método e o período que ela declara.
3. Abrir o Portal da Transparência num navegador (a leitura automática falhou) e confirmar a descrição de CEIS, CNEP e emendas, a licença de cada conjunto e as URLs de download que o site vai citar.
5. Abrir os relatórios da Transparência Brasil antes de citar número de emendas Pix.
