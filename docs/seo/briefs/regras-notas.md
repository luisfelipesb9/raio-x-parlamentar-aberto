# Notas específicas por regra

Usar junto com `_regra.md`. Valores conferidos nos arquivos de `knowledge/rules/` e no relatório em 2026-11-26. Reconferir antes de publicar.

## Resumo das regras (base da página índice `/regras`)

| Regra | Pergunta em linguagem simples | Tipo | CF base | Fonte dos dados |
|---|---|---|---|---|
| R01 | O deputado costuma votar com o governo? | inferência | 0,95 | Câmara (votações nominais e orientação) |
| R02 | Votação simbólica entra na conta de votos? (não) | guardrail | n/a | Regimento Interno da Câmara |
| R03 | A cota pagou empresa punida na data do gasto? | inferência | 0,9 | CEAP (Câmara) + CEIS/CNEP (CGU) |
| R04 | Algum gasto da cota está muito fora do padrão dos colegas? | inferência | 0,5 | CEAP |
| R05 | Quanto o deputado propõe e relata, em medida simples? | inferência (medida) | 0,8 | Câmara (proposições) |
| R06 | Doador da campanha é sócio de empresa paga pela cota? (identidade confirmada) | inferência | 0,85 | CEAP + TSE + Receita (QSA) |
| R06b | O mesmo, com identidade ainda não confirmada | inferência | 0,85 x 0,4 = 0,34 | idem |
| R07 | As emendas foram para onde o deputado tem mais votos? | inferência | 0,6 | CGU (emendas) + TSE (votos por município) |
| R08 | Processo sem condenação definitiva e falta de dado viram culpa? (não) | guardrail | n/a | CF/88, art. 5º, LVII |
| R09 | Os sinais justificam atenção de quem fiscaliza? | inferência composta | 0,8 x CF do sub-objetivo | R03, R04, R06, R06b |

---

## R01 Taxa de governismo
- **URL:** `/regras/r01`. **Prompts:** P06, P07, P10, P11. **Termos:** governismo, orientação do governo, votação nominal, votação simbólica.
- **Parâmetros (YAML):** mínimo 10 votações; limiar 0,7; CF 0,95; penalidade x0,7 se menos de 30 votações (exemplo trabalhado: 0,95 x 0,7 = 0,665, nível "média").
- **Texto da conclusão no sistema:** "Votou junto com o governo em X% das N votações nominais em que o governo orientou."
- **Dados da amostra (relatório, 2026-11-26):** votações de 04/02 a 27/03/2025; no bruto 145 votações, 24 nominais, 22 com orientação Sim/Não; 14 findings de R01 na amostra, CF 0,665.
- **Comparação externa (`comparacao-externa.md`, consulta de 2026-11-25):** mesma classificação do Radar do Congresso em 13 de 14 deputados; diferença média de 12,6 pontos; a taxa do projeto foi maior em 13 de 14. Escrever que isso vem de "um período curto e de critérios possivelmente diferentes (hipótese não verificada)". Não copiar a tabela com nomes.
- **Especificidades da página:** explicar que abstenção e obstrução ficam fora; que o presidente da Casa conduz a sessão e não vota (informação de reportagem do Congresso em Foco; abrir a matéria antes de citar); que a mesma taxa muda com o período. Mostrar o que acontece com menos de 10 votações (sem alerta; "mostra que o mínimo evita taxas extremas", do `comparacao-externa.md`).
- **Fontes oficiais:** https://dadosabertos.camara.leg.br/ ; guia da Câmara sobre votação https://www2.camara.leg.br/comunicacao/assessoria-de-imprensa/guia-para-jornalistas/votacao
- **Fonte metodológica:** Basômetro (Estadão). Não linkar o painel (não verificado).
- **Não afirmar:** que alto governismo é bom ou ruim; que o deputado "é da base"; qualquer motivo do voto.
- **Links internos:** R02 (por que simbólica fica fora), `/comparar`, `/deputado/[id]`.

## R02 Votação simbólica não gera voto individual (guardrail)
- **URL:** `/regras/r02`. **Prompts:** P08, P09. **Termos:** votação simbólica, votação nominal.
- **Tipo:** guardrail, prioridade 1. Não tem CF: ele remove `voto` e `votacao` de votações não nominais antes de qualquer regra.
- **Dado da amostra:** removeu 121 votações simbólicas (relatório, seção 8).
- **Especificidades:** a primeira frase explica o fenômeno ("na votação simbólica ninguém registra como cada deputado votou"); só depois dizer que o sistema se recusa a inventar voto. Explicar como o dado oficial permite distinguir.
- **Fonte oficial:** guia da Câmara https://www2.camara.leg.br/comunicacao/assessoria-de-imprensa/guia-para-jornalistas/votacao (resultado de busca de 2026-11-26; abrir antes de citar).
- **Número externo:** uma reportagem de 2026 diz que em 2025 a Câmara teve 420 votações simbólicas e 215 nominais. **Veio de um resumo de busca; não usar até abrir a fonte original.**
- **Não afirmar:** que a votação simbólica é "escondida" ou "irregular"; ela é a regra geral prevista no regimento, segundo a Mesa (resumo de busca; confirmar).
- **Links internos:** R01, glossário.

## R03 Pagou fornecedor com sanção vigente
- **URL:** `/regras/r03`. **Prompts:** P17, P18, P19, P28. **Termos:** CEAP, CEIS, CNEP, CNPJ, fornecedor.
- **Parâmetros:** CF 0,9; sem penalidades; condição: ao menos 1 despesa a um CNPJ cuja sanção CEIS ou CNEP estava vigente na data do gasto; estorno (valor negativo) não conta; só entra CNPJ com valor líquido positivo; casamento exato por CNPJ.
- **Dados da amostra:** 2 findings de R03; 254 vínculos despesa-sanção; 3.189 vínculos despesa-empresa (relatório).
- **Especificidades:** a ressalva principal é "não prova que o deputado sabia da sanção" e deve estar na primeira tela. Explicar que CEIS e CNEP não são listas equivalentes (resultado de busca de páginas do governo; abrir a página da CGU para confirmar). Dizer que a sanção precisa estar vigente **na data do gasto**.
- **Fontes oficiais:** Portal da Transparência da CGU (a página não abriu na leitura automática; confirmar o link do CEIS e do CNEP num navegador antes de publicar); CEAP em https://www.camara.leg.br/transparencia/gastos-parlamentares
- **Não afirmar:** nome de deputado ou de empresa em exemplo; que houve irregularidade; que a empresa "não prestou o serviço".
- **Links internos:** R09 (composição), R06 (outro cruzamento com fornecedor), `/dados-e-api` (como cruzar por CNPJ).

## R04 Gasto da cota fora do padrão
- **URL:** `/regras/r04`. **Prompts:** P01 a P05. **Termos:** CEAP, z-score robusto, mediana.
- **Parâmetros:** z robusto maior que 3,5 (z = 0,6745 x (v - mediana) / MAD) por categoria, ao menos 5 deputados na categoria; CF 0,5; penalidade x0,8 se z menor que 5. Texto: "Gastou R$ X em 'categoria', cerca de N vezes o que um deputado típico gasta."
- **Dados da amostra:** 5 findings, CF 0,4 (0,5 x 0,8).
- **Limitações a repetir:** gasto alto pode ter justificativa (estado distante, mandato mais longo); a conta não é normalizada por UF (relatório); amostra de 20 deputados de MG, então a "mediana" é a da amostra, não a nacional. **Esta última nuance deve ser dita com clareza.**
- **Especificidades:** a página responde ao prompt "quem gasta mais?" **explicando por que não há ranking**. Explicar que o limite mensal varia por UF (Ato da Mesa 43/2009, resultado de busca; confirmar no texto) e que o prazo de comprovação do deputado é de 90 dias (idem; confirmar).
- **Fontes oficiais:** https://www.camara.leg.br/transparencia/gastos-parlamentares (verificada em 2026-11-26) ; https://www2.camara.leg.br/legin/int/atomes/2009/atodamesa-43-21-maio-2009-588364-normaatualizada-cd-mesa.html (a abrir).
- **Fonte metodológica:** Operação Serenata de Amor (Rosie); linkar o repositório https://www.github.com/okfn-brasil/serenata-de-amor (verificado, 2026-11-26).
- **Não afirmar:** "gasto abusivo", "gastão", "fora da lei". Não comparar com média nacional.
- **Links internos:** R03, R09, glossário CEAP, `/deputado/[id]`.

## R05 Produção legislativa ponderada
- **URL:** `/regras/r05`. **Prompts:** nenhum direto; atende curiosidade sobre "quem produz mais". **Termos:** proposição, autoria, coautoria, relatoria.
- **Parâmetros:** pontuação de 0 a 40: 32 x (1 - e^(-iniciativa/25)) + 8 x (1 - e^(-relatorias/10,57)); iniciativa = autorias + 0,25 x coautorias; CF 0,8; x0,7 se menos de 5 proposições; média do partido só como contexto (mínimo 3 colegas). O objetivo se chama `pontuacao_producao_legislativa` (medida, não "produz bem ou mal").
- **Dados da amostra:** 10 findings; CF médio 0,584.
- **Especificidades:** a página deve destacar "mede quantidade ponderada, não qualidade nem aprovação" e "falta de dado não é produção zero". É a regra com **maior risco de virar ranking**: não publicar tabela ordenada nem comparação nominal.
- **Fonte metodológica:** Radar da República V2 (não verificado neste estudo).
- **Fonte oficial:** https://dadosabertos.camara.leg.br/
- **Não afirmar:** que a nota mede "desempenho" ou "competência"; que quem tem pontuação menor "trabalha menos".

## R06 e R06b Circuito doador-sócio-fornecedor
- **URL:** `/regras/r06` (uma página com duas seções). **Prompts:** P20, P29. **Termos:** doador, QSA, CPF mascarado, pseudonimização, indício.
- **Parâmetros:** R06 (identidade confirmada por CPF íntegro): CF 0,85. R06b (identidade não confirmada): 0,85 x 0,4 = 0,34, teto 0,4, nível "indício". Casamento por nome normalizado; dígitos visíveis incompatíveis descartam o caso; só doadores pessoa física da campanha ligada ao deputado.
- **Dados da amostra:** nenhum achado com 50 CNPJs consultados; 1 R06b surgiu com 300 (relatório). Com dados reais, o QSA vem mascarado (617 sócios mascarados, 96 sem CPF, 0 íntegros), então **o R06 confirmado não dispara**: dizer isso.
- **Especificidades:** o nome do sócio **não é exibido** enquanto a identidade não for confirmada (LGPD). A página explica o conceito, nunca mostra um caso real. Mencionar a pseudonimização (ADR-006; `docs/politica-de-uso-e-correcao.md`).
- **Fontes oficiais:** TSE https://dadosabertos.tse.jus.br/ (verificada); CEAP (Câmara); Receita Federal (QSA; link a confirmar).
- **Não afirmar:** "retorno de doação", "esquema", "laranja", "caixa dois". O YAML usa "padrão clássico de risco de retorno de doação e merece conferência"; na página, preferir "uma pista que pede conferência" e explicar que pode ser homônimo.
- **Links internos:** R03, R09, glossário (QSA, PEP).

## R07 Concentração eleitoral de emendas
- **URL:** `/regras/r07`. **Prompts:** P12 a P16. **Termos:** emenda parlamentar, emenda Pix, votos válidos, município.
- **Parâmetros:** razão mínima 3 entre a fatia de votos do deputado nos municípios que receberam suas emendas e a fatia nos demais municípios da UF; CF 0,6; penalidade x0,8 se há emendas Pix anteriores a 2027 (destino final não rastreável); x0,7 se menos de 3 municípios; ligação emenda-deputado por nome tem CF 0,8 (CF final médio 0,384 na amostra: 0,6 x 0,8 x 0,8).
- **Dados da amostra:** 9 findings; 2.083 emendas ligadas no escopo da amostra; no total global da CGU, 37.297 de 77.113 ligadas a um deputado (o restante é bancada, comissão ou autores de fora). Usar as duas métricas com a legenda, nunca uma só.
- **Limitações a repetir:** correlação não é causa; só a eleição mais recente (2022); municípios sem registro de votos ficam fora; se o resto do estado é 0%, a razão não é calculada.
- **Especificidades:** explicar emenda Pix em linguagem simples. Levantamentos de terceiros sobre falta de detalhamento (Transparência Brasil, 2023, 2024 e 2026) são pano de fundo: **abrir o relatório original antes de citar qualquer número**; os números vistos em resultados de busca (por exemplo, "78% dos parlamentares" em 2024, "R$ 1,5 bilhão sem detalhamento" em 2025) não foram verificados na fonte.
- **Fontes oficiais:** CGU (confirmar link em navegador); TSE (votos por município) https://dadosabertos.tse.jus.br/ ; Senado, guia de acompanhamento de emendas: https://www12.senado.leg.br/noticias/materias/2025/12/01/como-acompanhar-a-escolha-das-emendas-parlamentares (resultado de busca; abrir).
- **Fonte metodológica:** Radar do Voto https://radardovoto.com (verificado 2026-11-26).
- **Não afirmar:** que o deputado "compra votos" ou "direciona para se eleger"; nada sobre motivo.
- **Links internos:** glossário (emenda Pix), `/grafo`, `/deputado/[id]`.

## R08 Presunção de inocência e lacuna de dados (guardrail)
- **URL:** `/regras/r08`. **Prompts:** P21. **Termos:** presunção de inocência, trânsito em julgado, lacuna de dado.
- **Tipo:** guardrail, prioridade 2. Remove todo fato `processo` cujo `transitado_em_julgado` não seja verdadeiro e registra deputados sem nenhum dado, sem imputar valor.
- **Estado honesto:** **nenhum plugin produz `processo` ainda** (relatório; `docs/ROADMAP.md`), e R08 removeu 0 processos na amostra. A página deve dizer isso na primeira tela, para não sugerir que o sistema monitora processos.
- **Fonte:** CF/88, art. 5º, LVII; Elas no Congresso (projeto citado como inspiração; não verificado neste estudo).
- **Especificidades:** responder P21 ("como saber se é réu") dizendo que o sistema não tem essa fonte e que a consulta é no Judiciário. Link do Planalto para a Constituição: a confirmar.
- **Não afirmar:** que o sistema "garante" inocência ou "limpa" nome; que ausência de processo no sistema significa ausência de processo.

## R09 Merece atenção da fiscalização (composta)
- **URL:** `/regras/r09`. **Prompts:** P05, P19 (contexto). **Termos:** objetivo, sub-objetivo, encadeamento regressivo.
- **Parâmetros:** `requer: [risco_integridade]`, provado por R03, R04, R06 e R06b; CF 0,8 x CF do sub-objetivo; combinação MYCIN; só existe no encadeamento regressivo (tela Perguntar); `make infer` não a materializa.
- **Especificidades:** é a regra de maior risco de leitura como "veredito". A página abre com: "Esta regra reúne sinais já encontrados e diz se eles justificam que órgãos de controle e imprensa olhem com atenção. Não conclui que há irregularidade." Explicar com um exemplo da base fictícia, mostrando a árvore de prova.
- **Não afirmar:** "suspeito", "investigado", "alvo". Nunca em página pública mostrar o resultado da R09 de um deputado real num exemplo.
- **Links internos:** R03, R04, R06, `/perguntar`, `/estudantes` (encadeamento regressivo).
