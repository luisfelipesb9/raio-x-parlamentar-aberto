# Raio-X Parlamentar: um Sistema Especialista para documentar e explicar a atuação de deputados federais

Trabalho final da disciplina de Sistemas Especialistas, Bacharelado em Sistemas de Informação, Unimontes.
Autores: Luis (fundação e raciocínio) e Pedro Rodrigues (produto). Novembro de 2026.

## Resumo
O Raio-X Parlamentar reúne dados públicos sobre deputados federais (votos, projetos, gastos da cota parlamentar,
emendas, financiamento eleitoral, empresas e sanções) e aplica uma base de conhecimento de nove regras e uma variante
(R01–R09 e R06b) para produzir conclusões em linguagem simples. Cada conclusão traz um fator de certeza (CF, no estilo MYCIN)
e uma trilha de explicação com links para a fonte oficial. O sistema separa explicitamente fato, conhecimento, inferência e
explicação, e inclui guardrails que impedem conclusões indevidas (votação simbólica não é voto individual; processo sem
condenação definitiva não é culpa). Em uma amostra de 20 deputados de Minas Gerais, o motor gerou 40 findings. Os fatores de
certeza e limiares das regras são escolhas do especialista e **não foram calibrados empiricamente**.

## 1. Introdução e problema
O cidadão que quer saber "o que meu deputado fez?" encontra dados dispersos em portais diferentes (Câmara, TSE, Receita,
CGU), com formatos e chaves distintos, sem explicação e sem noção de quanto cada dado é confiável. Dados abertos não bastam:
é preciso interpretá-los com cuidado. Um mesmo nome pode ser de duas pessoas, um CPF vem mascarado, uma votação simbólica
não registra voto individual, e um processo em andamento não é condenação.

O problema tratado é: **como cruzar fontes públicas heterogêneas e produzir conclusões compreensíveis por leigos, com grau de
certeza explícito e rastreável até o documento oficial?** Esse é um problema típico de Sistema Especialista (SE): conhecimento
de domínio expresso em regras, incerteza, e necessidade de justificar cada resposta.

Objetivos: (i) construir a base de fatos a partir de fontes oficiais; (ii) codificar o conhecimento de especialistas como regras
em YAML, separadas do código; (iii) implementar motor de inferência progressivo e regressivo com fatores de certeza;
(iv) explicar cada conclusão; (v) respeitar a LGPD e a presunção de inocência.

## 2. Estado da arte
Nenhum projeto aberto ativo cobre "tudo sobre um político e a correlação entre as informações". Os existentes tornaram-se
fontes metodológicas ("especialistas") do nosso conhecimento:

| Projeto | O que faz | Situação / uso no nosso trabalho |
|---|---|---|
| Operação Serenata de Amor / Rosie | Detecta gastos suspeitos da CEAP com modelos estatísticos | Foco só em CEAP, execução manual. Inspirou R04 (outlier de gasto) |
| Parlametria / Leggo | Perfil e produtividade legislativa | Arquivado desde 02/2023. Referência de produção legislativa |
| Basômetro (Estadão) | Taxa de governismo por votações nominais | Parado desde 2020. Fonte da R01 |
| Radar Parlamentar | Posicionamento por votações | Só votações. Referência de afinidade de votos |
| Radar da República | Pontuação de atuação parlamentar | Fonte da fórmula de produção ponderada (R05) |
| Radar do Voto | Relação entre votos e destino de emendas | Fonte da R07 |
| Elas no Congresso | Monitoramento da atuação, com cuidado com lacunas de dado | Inspirou o guardrail R08 |
| Perfil Político | Perfil de políticos | Inativo |

Lacuna: nenhum integra gastos, emendas, financiamento, empresas e sanções num grafo navegável **com explicação e incerteza
explícitas**. A pesquisa que fundamenta esta seção está em `docs/plano-original.md`.

## 3. Fundamentação em Sistemas Especialistas
Um SE separa o **conhecimento** do domínio (regras) do mecanismo que o aplica (motor), e justifica suas respostas.

### 3.1 Base de fatos
Memória de trabalho com os fatos conhecidos. Aqui, cada `Fact` (`contracts/models.py`) tem `tipo`, `chave`, `atributos`,
`fonte`, `id_oficial`, `url` e `coletado_em`: rastreabilidade obrigatória. Persistida em DuckDB (`repo/store.py`); os 15 tipos de fato
estão em `docs/fact_types.md`. Em tempo de inferência, o `FactBase` (`engine/factbase.py`) oferece `of(tipo)` e `exclude(...)`, que
permite aos guardrails podar fatos antes das regras.

### 3.2 Base de conhecimento
Regras SE/ENTÃO em arquivos YAML (`knowledge/rules/R*.yaml`), com `se`, `entao` (texto leigo), `cf`, `penalidades`, `por_que`,
`limitacoes` e `fonte_metodologica`. O conhecimento é **dado, não código**: adicionar regra não exige alterar o motor. As
expressões de `se` são avaliadas por um avaliador seguro (`engine/safe_expr.py`, só comparações e aritmética sobre AST), e não por `eval`.

### 3.3 Motor de inferência
- **Encadeamento progressivo** (`engine/forward.py`, dirigido por dados): 1) executa os guardrails (prioridade < 10), que restringem a
  base; 2) para cada regra de inferência não composta, chama o predicado, avalia `se`, calcula o CF e emite `Finding` com `Explanation`.
- **Encadeamento regressivo** (`engine/backward.py`, dirigido por objetivo): `prove(objetivo, deputado)` calcula as regras alcançáveis,
  resolve sub-objetivos declarados em `requer`, combina regras que concluem o mesmo objetivo e detecta ciclos pela pilha de objetivos
  (ramo cíclico vale CF 0 e fica na trilha). Usado pelo endpoint `/perguntar`. Ver ADR-004.
- **Guardrails**: regras de prioridade alta que *bloqueiam* conclusões (R02, R08).

### 3.4 Fatores de certeza (MYCIN)
Implementados em `engine/certainty.py` (Shortliffe e Buchanan, 1975). CF ∈ [−1, 1].

- Combinação de duas evidências para a mesma conclusão:
  - ambos ≥ 0: `CF = CF1 + CF2 · (1 − CF1)`
  - ambos < 0: `CF = CF1 + CF2 · (1 + CF1)`
  - sinais opostos: `CF = (CF1 + CF2) / (1 − min(|CF1|, |CF2|))`
- Conjunção de premissas (propagação): `CF_conclusão = CF_regra · max(0, min(CF_premissas))`.
- Penalidades multiplicativas por incerteza do dado: `CF = CF · f1 · f2 · …` (ex.: ×0,4 para identidade não confirmada).
- Na prática do sistema: `CF_finding = cf_regra × min(premissas) × Π penalidades`, depois mapeado para o semáforo
  `Nivel`: alta ≥ 0,7; média ≥ 0,4; indício ≥ 0,2; inconclusivo < 0,2.

Exemplo real: R01 tem cf 0,95 e penalidade ×0,7 se há menos de 30 votações; CF = 0,95 × 0,7 = 0,665 (nível média), valor observado
na amostra (0,67 arredondado).

### 3.5 Módulo de explicação
`engine/explain.py` monta, para cada finding, a trilha **"como"** (guardrails aplicados, regra e valores calculados, penalidades
com motivo e fator), o **"por quê"** (`por_que` da regra) e as **limitações**. As evidências (`Evidence`) apontam para
documento oficial (id e URL). Na regressiva, a trilha é a árvore de `PassoProva` (profundidade, objetivo, regra, CF, nota).

### 3.6 Engenharia do conhecimento
Os "especialistas" são metodologias publicadas (Basômetro, Serenata, Radar da República, Radar do Voto, Elas no Congresso) e a
legislação (CF/88 art. 5º, LVII). O conhecimento foi elicitado por **análise documental**, não por entrevista a especialistas:
extraímos de cada fonte a pergunta, a fórmula e a ressalva, e registramos no YAML (`fonte_metodologica`, `limitacoes`). Cada regra
declara o que **não** consegue afirmar. A validação com especialistas humanos fica como trabalho futuro.

## 4. Arquitetura e mapeamento conceito → código
Diagrama e fluxo detalhados em `docs/arquitetura.md`. Dependência em uma direção:
`sources → ingest → repo → engine → graph → api → web`, com `contracts/` compartilhado.

| Conceito de SE | Arquivo |
|---|---|
| Base de fatos | `repo/store.py`, `repo/migrations/*.sql`, `engine/factbase.py`, `contracts/models.py` (`Fact`) |
| Aquisição de dados | `sources/*/source.py`, `ingest/pipeline.py` |
| Resolução de entidades (incerteza do dado) | `ingest/resolve/*.py`, `repo/links.py` |
| Base de conhecimento | `knowledge/rules/R*.yaml`, formato em `knowledge/rules/_schema.md` |
| Carregador/validador de regras | `engine/rules.py` |
| Avaliador seguro de condições | `engine/safe_expr.py` |
| Predicados (condições) | `engine/predicates/` (`core`, `producao`, `circuito`, `emendas`, `presuncao`, `registry`) |
| Motor progressivo | `engine/forward.py`, `engine/run.py` |
| Motor regressivo | `engine/backward.py` |
| Fatores de certeza | `engine/certainty.py` |
| Guardrails | `engine/predicates/core.py` (R02), `engine/predicates/presuncao.py` (R08) |
| Módulo de explicação | `engine/explain.py`, `contracts/models.py` (`Explanation`) |
| Grafo de correlações | `graph/build.py`, `contracts/graph.py` |
| Interface do usuário | `api/main.py`, `web/` |

## 5. Base de conhecimento
Convenção: `CF final = cf × min(premissas) × penalidades`. "Findings" são os da amostra (seção 8).

### R01 Taxa de governismo
- **SE** taxa de votos "Sim"/"Não" iguais à orientação do governo ≥ 0,7 (mínimo de 10 votações nominais com orientação) **ENTÃO** "Votou junto com o governo em X% das N votações".
- **CF** 0,95; **penalidade** ×0,7 se menos de 30 votações. **Fonte**: Basômetro.
- **Limitações**: só nominais com orientação do líder do governo; abstenção e obstrução fora da conta. O corte 0,7 é nosso.

### R02 Votação simbólica não gera voto individual (guardrail)
- Remove da base os `voto` e `votacao` de votações não nominais antes de qualquer regra. Prioridade 1.
- **Fonte**: Regimento Interno da Câmara. Limitação: votação simbólica aparece só como resultado da Casa.

### R03 Fornecedor com sanção vigente
- **SE** houve despesa CEAP a um CNPJ cuja sanção CEIS/CNEP estava vigente na data do gasto (início ≤ data ≤ fim ou sem fim) **ENTÃO** alerta com número de despesas e valor líquido.
- **CF** 0,9, sem penalidades. Estornos (valor < 0) não contam; só entra o CNPJ com líquido > 0. Casamento exato por CNPJ.
- **Fonte**: Portal da Transparência (CGU) + CEAP. **Limitação**: não prova que o deputado sabia da sanção.

### R04 Gasto da cota fora do padrão
- **SE** o z-score robusto do total por categoria (`z = 0,6745 · (v − mediana) / MAD`) > 3,5, com ao menos 5 deputados na categoria **ENTÃO** alerta com categoria e "vezes a mediana".
- **CF** 0,5; ×0,8 se z < 5. **Fonte**: Serenata de Amor (Rosie), simplificado.
- **Limitações**: gasto alto pode ter justificativa (estado distante, mandato mais longo); sem normalizar por UF.

### R05 Produção legislativa ponderada
- Pontuação 0–40: `32·(1 − e^(−iniciativa/25)) + 8·(1 − e^(−relatorias/10,57))`, com `iniciativa = autorias + 0,25·coautorias` (autor prevalece sobre coautor).
- **CF** 0,8; ×0,7 se menos de 5 proposições. Média do partido só como contexto (≥ 3 colegas), nunca como conclusão.
- **Fonte**: Radar da República V2. **Limitações**: mede quantidade, não qualidade nem aprovação; quem não tem fato de autoria fica sem pontuação (lacuna não é zero).

### R06 Circuito doador-sócio-fornecedor (identidade confirmada)
- **SE** o deputado pagou (CEAP) empresa cujo sócio (QSA) tem o mesmo nome normalizado de doador PF da campanha dele **e** o CPF íntegro é igual **ENTÃO** alerta.
- **CF** 0,85. **Fonte**: CEAP + TSE + Receita (QSA); lógica do Radar da República. **Limitações**: não prova irregularidade; só doadores PF de candidatura resolvida.

### R06b Circuito (indício, identidade não confirmada)
- Mesmo circuito, mas CPF mascarado ou ausente com dígitos visíveis compatíveis. **CF** 0,85 × 0,4 = 0,34 (**indício**, teto 0,4 por construção). O nome do sócio não é exposto (LGPD). Dígitos visíveis incompatíveis descartam o caso. Ver ADR-003.

### R07 Concentração eleitoral de emendas
- **SE** a razão entre a fatia de votos do deputado nos municípios que receberam suas emendas e a fatia nos demais municípios da UF ≥ 3 **ENTÃO** alerta.
- **CF** 0,6; ×0,8 se há emendas Pix anteriores a 2027 (destino final não rastreável); ×0,7 se menos de 3 municípios de destino. Só a eleição mais recente; municípios sem registro de votos ficam fora (não se inventa zero); resto = 0% não divide.
- **Fonte**: Radar do Voto. **Limitação**: correlação não é causa (mais votos onde atua há mais tempo).

### R08 Presunção de inocência e lacuna de dados (guardrail)
- Remove todo fato `processo` cujo `transitado_em_julgado` não seja verdadeiro e registra deputados sem nenhum dado, para os quais nada é imputado. Prioridade 2.
- **Fonte**: CF/88 art. 5º, LVII; Elas no Congresso. **Limitação**: ainda não há fonte que produza `processo`; a garantia de "não inventar valor" é estrutural (os predicados partem de fatos existentes) e o guardrail a audita.

### R09 Merece atenção da fiscalização (composta)
- `requer: [risco_integridade]`, objetivo provado por R03, R04, R06 e R06b (CF combinado por MYCIN). **CF** 0,8 × CF do sub-objetivo. Só existe no regressivo (`/perguntar`); `make infer` não a materializa. Indício não é acusação.

## 6. Aquisição de dados e resolução de entidades
**Fontes** (`sources/`): Câmara dos Deputados API v2 (deputados, votações, votos, orientação, proposições e autorias); CEAP (arquivo anual da Câmara);
TSE (candidaturas, prestação de contas, votos por município, eleição 2022); CGU (CEIS, CNEP, emendas); OpenSanctions `br_pep` (JSON aninhado; licença CC BY-NC 4.0, uso acadêmico);
Receita Federal via BrasilAPI (apenas os CNPJs que aparecem, evitando a base completa). Todo fato guarda fonte, id oficial e URL.

**Pipeline** (`ingest/pipeline.py`): execução em ordem fixa, escopo por UF e amostra, reuso de bruto (`--reusar-raw`), idempotência (cada passo apaga o que vai reafirmar).

**Resolução** (`ingest/resolve/`), com CF por ligação:
| Ligação | Método e CF |
|---|---|
| candidatura → deputado | CPF íntegro 1,0; nome+UF único 0,8; desempate por partido 0,7; ambíguo não liga |
| emenda → deputado | nome do autor único 0,8 (sem UF do autor) |
| PEP → deputado | nome + CPF mascarado compatível 0,95; nome civil 0,7; nome parlamentar 0,5 |
| despesa → empresa/sanção | CNPJ exato 1,0 |

`deputado_id` só é gravado no fato com CF ≥ 0,7. CPF íntegro diferente descarta o par; ambiguidades vão para `entity_ambiguity`. Ver ADR-002.
A chave de despesa CEAP é determinística (`idDocumento` + hash da linha) porque o id da Câmara se repete.
O CPF do deputado é obtido em `GET /deputados/{id}` (`detalhar_deputados`); sem ele a ligação cai em nome+UF.

### 6.1 Propagação da incerteza da resolução de entidades (`deputado_cf` → `premissas_cf`)
Antes, o CF do link (ex.: 0,8 por nome) ficava só em `entity_link` e não afetava o finding. Agora ele é propagado.
Desenho: o fato enriquecido carrega o CF da ligação (`deputado_cf`); o predicado o inclui em `premissas_cf` do `Candidate`, e o motor aplica a conjunção de MYCIN: `CF = cf_regra × min(premissas) × penalidades`. Ligação por CPF (1,0) não altera o CF; ligação por nome (0,8) o reduz.
Medido na amostra: as emendas ligam por nome (0,8), então R07 = 0,6 × 0,8 (link) × 0,8 (penalidade de emenda Pix anterior a 2027) = 0,384 (CF médio observado 0,384). R01, R03 e R04 não dependem de ligação e mantêm 0,665, 0,9 e 0,4.

## 7. Guardrails éticos e LGPD
- Votação simbólica nunca vira voto individual (R02). Processo sem trânsito em julgado nunca reduz nota (R08). Média partidária é contexto (R05).
- Falta de dado não é zero (R05, R07).
- Toda conclusão traz nível de certeza e link para a fonte oficial; toda regra declara suas limitações.
- CPF/CNPJ apenas de fontes oficiais abertas; nada de dados de parentes ou terceiros não públicos. O nome de sócio não confirmado não é exposto (R06b).
- Texto ao leitor evita acusação: "indício", "merece conferência". A API é somente leitura e nunca chama serviço externo.
- O grafo não funde homônimos e não exibe nomes de pessoa física sem identidade confirmada (correção em curso).
- A base de amostra com CPF não é versionada (minimização); a base pública é pseudonimizada (`--pseudonimizar`, HMAC-SHA256 `hmac:<32 hex>` com sal `RAIO_X_ID_SALT`; `doador_cpf_visivel` preserva a R06b; CPF de fornecedor PF em `despesa_ceap.fornecedor` também é substituído) e verificada por varredura: 0 CPFs íntegros (controle 752). A varredura não cobre `data/raw`. Ver ADR-006.
- Licença dos dados: o OpenSanctions é CC BY-NC; o projeto é acadêmico e não comercial.

## 8. Resultados na amostra
Amostra: 20 deputados de MG, 2024 (`make sample`). Número de findings por regra:

| Regra | Findings | CF observado |
|---|---|---|
| R01 Governismo | 14 | 0,665 |
| R03 Fornecedor sancionado | 2 | 0,9 |
| R04 Outlier CEAP | 5 | 0,4 |
| R07 Concentração de emendas | 9 | 0,384 (médio) |
| R05 Produção ponderada | 10 | 0,584 (médio; 0,56–0,8, penalidade ×0,7 com < 5 proposições) |
| R06, R06b | 0 | nenhum circuito com `--limite-rfb 50`; com 300 surge 1 R06b |
| **Total** | **40** | |

Taxas de resolução na amostra: 20/20 candidaturas ligadas ao deputado por CPF (cf 1,0); 20/20 PEP por CPF (0,95); 3.189 links despesa → empresa; 254 links despesa → sanção; 1.008 doações; 17.060 registros de votos por município.
Emendas, duas métricas distintas: 2.083 ligadas no escopo da amostra; e, no total global da CGU, 37.297 de 77.113 ligadas a um deputado (o restante é de bancada, comissão ou autores fora da Câmara/amostra).

A amostra é gerada com `--incluir-proposicoes`. Testes: 472 Python, 50 unitários e 45 e2e no web.

Guardrails na amostra: R02 removeu 121 votações simbólicas; R08 removeu 0 processos (não há fonte `processo`). O objetivo da R05 chama-se `pontuacao_producao_legislativa`.

**Aviso metodológico.** Os CFs das regras (0,95; 0,9; 0,5; 0,6; 0,85; 0,8), as penalidades e os limiares (z > 3,5; razão ≥ 3; taxa ≥ 0,7; mínimo de votações) são **estimativas do
especialista, baseadas nas metodologias citadas, e não foram calibrados empiricamente** contra casos rotulados. Os CFs devem ser lidos como graus ordinais de confiança, não como
probabilidades. Os achados também não foram comparados sistematicamente com Basômetro, Radar do Voto ou Serenata, nem validados com leigos. Os 40 findings são conclusões do sistema,
não afirmações sobre irregularidade.

## 9. Limitações e trabalhos futuros
Limitações: amostra pequena (20 deputados, um estado, um ano); CFs sem calibração; **R06 confirmado não dispara com dados reais da RFB**: o QSA vem sempre mascarado (617 sócios mascarados, 96 sem CPF, 0 íntegros), logo só a R06b (indício) é alcançável, e o zero de R06/R06b com 50 CNPJs era cobertura (com 300 surge 1 R06b); 
fonte `processo` inexistente; pesos de R07 sensíveis ao cadastro de emendas Pix; conhecimento elicitado por documentos, sem entrevistas.
Trabalhos futuros: (1) coletar proposições (habilita R05); (3) calibrar CFs com casos rotulados (curva de confiabilidade) e analisar sensibilidade dos limiares;
(4) validar com especialistas e com leigos; (5) novos plugins (Senado, TCU, estados); (6) backward interativo (perguntar ao usuário fatos faltantes); (7) Postgres e reavaliação incremental.

## Referências
- SHORTLIFFE, E. H.; BUCHANAN, B. G. A model of inexact reasoning in medicine. *Mathematical Biosciences*, v. 23, p. 351-379, 1975.
- BUCHANAN, B. G.; SHORTLIFFE, E. H. *Rule-Based Expert Systems: the MYCIN experiments of the Stanford Heuristic Programming Project*. Addison-Wesley, 1984.
- GIARRATANO, J.; RILEY, G. *Expert Systems: Principles and Programming*. 4. ed. Course Technology, 2004.
- BRASIL. Constituição da República Federativa do Brasil de 1988, art. 5º, LVII. Lei nº 13.709/2018 (LGPD).
- Operação Serenata de Amor / Rosie. https://serenata.ai
- Parlametria / Leggo; Basômetro (Estadão); Radar Parlamentar; Radar da República; Radar do Voto; Elas no Congresso; Perfil Político: projetos descritos em `docs/plano-original.md`.
- Câmara dos Deputados, Dados Abertos API v2. https://dadosabertos.camara.leg.br
- TSE, Dados Abertos. https://dadosabertos.tse.jus.br · CGU, Portal da Transparência (CEIS, CNEP, emendas) · Receita Federal (QSA) via BrasilAPI · OpenSanctions `br_pep` (CC BY-NC 4.0).
