# Licenças e termos dos dados

O **código** deste repositório é licenciado sob MIT (arquivo `LICENSE`). Os **dados** que o sistema consome pertencem às fontes oficiais e seguem a licença ou os termos de cada uma. Este documento diz o que sabemos, o que ainda não conseguimos confirmar e como atribuir a fonte.

> Levantamento feito em 26/11/2026 a partir das páginas oficiais. **Não é parecer jurídico.** Onde está escrito "a confirmar", não encontramos o texto oficial e não vamos afirmar o que não sabemos. Se você sabe a resposta, abra uma issue com o link da fonte oficial.

## O que este repositório distribui (e o que não distribui)

- **Não versionamos dados reais de pessoas.** O repositório contém só código, regras, fixtures **sintéticas** de teste e um gerador de banco de demonstração **fictício** (`make seed-demo`, ver `docs/demo.md`).
- O banco de amostra com dados reais é gerado localmente (`make sample`), fica em `data/` (ignorado pelo git) e **não** deve ser publicado. A base pública é pseudonimizada (ADR-006).
- As fotos dos deputados **não são copiadas** para o repositório: o site apenas exibe a imagem a partir do endereço da Câmara, com o crédito.

## Por fonte

| Fonte | Condição confirmada | Atribuição | Situação |
|---|---|---|---|
| **Câmara dos Deputados** (API v2 e arquivos) | Sem licença nomeada. Termos do portal: informações "de domínio público", reprodução com citação da fonte. FAQ oficial: sem restrição a usar os dados em aplicativos. | Sim: "Câmara dos Deputados" | Uso permitido; licença formal **a confirmar**. Limite de requisições não documentado (já observamos HTTP 429): usamos pausa, novas tentativas e arquivos em lote. |
| **CEAP** (cota parlamentar) | Sem página própria; é publicada no mesmo portal. Presume-se o mesmo regime da Câmara (**inferência**). | Sim: Câmara dos Deputados | Mesmo status da Câmara. Atenção: traz CPF/CNPJ de fornecedores, que podem ser pessoa física. |
| **TSE** (candidaturas, prestação de contas, votação) | "Creative Commons Attribution" (CC BY) na página de cada conjunto de 2022. A versão da licença não é declarada. | Sim (CC BY) | Confirmado. A licença **não** dispensa as obrigações de LGPD sobre CPF e dados pessoais. |
| **CGU** (CEIS, CNEP, emendas) | Licença do conjunto **a confirmar**. Base legal geral: Decreto 8.777/2016 (dados abertos de reuso irrestrito, creditando a fonte). O rodapé do gov.br cita CC BY-ND 3.0 para o conteúdo do **site**, e não vimos nada que o aplique aos conjuntos de dados. | Sim: CGU, Portal da Transparência | **A confirmar.** Provável uso livre com crédito. |
| **Receita Federal** via **BrasilAPI** (CNPJ) | BrasilAPI: código MIT, mas **sem termos de uso dos dados** ("ainda elaborando"); pede para não fazer crawling automatizado. Licença do conjunto CNPJ da Receita: **a confirmar**. | Sim (Receita Federal) | Usamos só para uma amostra pequena e limitada de CNPJs. **Não é adequada para ingestão em massa**; para cobertura nacional o plano é o arquivo mensal da Receita. |
| **OpenSanctions** (`br_pep`) | **CC BY-NC 4.0** (uso **não comercial**, com atribuição e indicação de alterações). Os dados originais vêm da CGU. | Sim | Ver a seção abaixo. |
| **IBGE** (localidades) | Termos da API **a confirmar**. | Sim (prática) | Uso para códigos de município. |
| **Fotos oficiais** (Câmara) | O Banco de Imagens da Câmara cita CC BY com crédito. Que os retratos de `/internet/deputado/bandep/` estejam sob a mesma licença é **a confirmar**. | "Câmara dos Deputados" | Exibimos por link, sem copiar. |

## OpenSanctions: restrição de uso comercial

Os dados do `br_pep` estão sob **CC BY-NC 4.0**. Isto significa que:

- o **código** que os baixa é MIT, mas **os dados não**: nunca os apresentamos como MIT e **não os redistribuímos** neste repositório (as fixtures de teste são sintéticas);
- quem usar este projeto para **fins comerciais** deve **desativar essa fonte** (por exemplo, rodando a ingestão sem `opensanctions` em `--fontes`) ou obter licença própria junto à OpenSanctions;
- é preciso citar a fonte e indicar se houve alterações.

Estamos avaliando trocar a origem por download direto da lista de PEP da CGU, quando a licença dela for confirmada.

## Texto de atribuição sugerido

Ajuste a data de acesso. Os marcados "provisório" dependem da confirmação acima.

- **Câmara:** "Dados: Câmara dos Deputados, Dados Abertos (dadosabertos.camara.leg.br), acessados em AAAA-MM-DD."
- **CEAP:** "Despesas da Cota para o Exercício da Atividade Parlamentar (CEAP): Câmara dos Deputados, Dados Abertos."
- **TSE:** "Dados: Tribunal Superior Eleitoral, Portal de Dados Abertos (dadosabertos.tse.jus.br), licença CC BY. Processados pelo Raio-X Parlamentar."
- **CGU:** "Dados: Controladoria-Geral da União, Portal da Transparência (portaldatransparencia.gov.br): CEIS, CNEP e emendas parlamentares." (provisório)
- **Receita Federal:** "Dados: Receita Federal do Brasil, Cadastro Nacional da Pessoa Jurídica (CNPJ)." (provisório)
- **OpenSanctions:** "OpenSanctions br_pep (opensanctions.org/datasets/br_pep/), dados originais da CGU, licença CC BY-NC 4.0; uso não comercial; alterações indicadas pelo projeto."
- **IBGE:** "Fonte: IBGE (servicodados.ibge.gov.br)." (provisório)
- **Fotos:** "Foto: Câmara dos Deputados."

## Dados pessoais

Ser público não dispensa finalidade, boa-fé e interesse público (LGPD, art. 7º, §3º). O projeto tem finalidade declarada (transparência e ensino), minimiza dados (amostra pseudonimizada, nenhum CPF íntegro em respostas) e oferece canal de correção. Veja `docs/politica-de-uso-e-correcao.md` e `SECURITY.md`.

## Pendências (ajude a fechar)

1. Ler o campo "Licença" dos conjuntos CNPJ, CEIS, CNEP, emendas e PEP no portal dados.gov.br e, se estiver vazio, perguntar à Receita ou à CGU.
2. Perguntar à OpenSanctions sobre o uso em um repositório público, gratuito e acadêmico, ou migrar o `br_pep` para a CGU.
3. Pedir à Câmara uma declaração de licença para a API, o CEAP e as fotos oficiais.
4. Confirmar os termos de uso da API do IBGE e a Portaria TSE 93/2021.
