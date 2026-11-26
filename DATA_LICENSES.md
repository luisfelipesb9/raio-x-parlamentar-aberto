# Licenças e termos dos dados

O **código** deste repositório é licenciado sob MIT (arquivo `LICENSE`). Os **dados** que o sistema consome pertencem às fontes oficiais e seguem a licença ou os termos de cada uma. Este documento diz o que sabemos, o que ainda não conseguimos confirmar e como atribuir a fonte.

> Levantamento atualizado em 26/11/2026 a partir das páginas oficiais. **Não é parecer jurídico.** Onde está escrito "a confirmar", não encontramos o texto oficial e não vamos afirmar o que não sabemos. Se você sabe a resposta, abra uma issue com o link da fonte oficial.
>
> Detalhes, links e datas de acesso de cada item: [`docs/licencas/resumo-das-descobertas.md`](docs/licencas/resumo-das-descobertas.md). Rascunhos de pedidos às fontes: [`docs/licencas/pedidos.md`](docs/licencas/pedidos.md). Textos de crédito prontos: [`docs/licencas/atribuicao.md`](docs/licencas/atribuicao.md).

## Como ler a situação

- **Confirmado** = lemos o texto oficial.
- **Leitura indireta** = o catálogo oficial (dados.gov.br) não abre na nossa ferramenta de verificação; lemos o campo pelo índice de busca do próprio catálogo. Precisa de uma conferência visual no navegador (links no resumo).
- **Inferido** = conclusão nossa a partir de textos oficiais que não falam diretamente do caso.
- **A confirmar** = não achamos o texto oficial.

Duas distinções que evitam erro:

1. O Decreto 8.777/2016 (reuso aberto, só creditando a fonte) vale para o **Poder Executivo federal**: CGU, Receita Federal, IBGE. **Não** obriga a Câmara (Legislativo) nem o TSE (Judiciário), que têm políticas próprias.
2. O rodapé "CC BY-ND 3.0" dos sites gov.br diz respeito ao **conteúdo do site** ("Todo o conteúdo deste site"), e não aos conjuntos de dados. Não encontramos nenhuma página que o aplique aos dados.

## O que este repositório distribui (e o que não distribui)

- **Não versionamos dados reais de pessoas.** O repositório contém só código, regras, fixtures **sintéticas** de teste e um gerador de banco de demonstração **fictício** (`make seed-demo`, ver `docs/demo.md`).
- O banco de amostra com dados reais é gerado localmente (`make sample`), fica em `data/` (ignorado pelo git) e **não** deve ser publicado. A base pública é pseudonimizada (ADR-006).
- As fotos dos deputados **não são copiadas** para o repositório: o site apenas exibe a imagem a partir do endereço da Câmara, com o crédito.

## Por fonte

| Fonte | Condição | Atribuição | Situação |
|---|---|---|---|
| **Câmara dos Deputados** (API v2 e arquivos) | Sem licença nomeada (nem na página da API, nem no repositório oficial do GitHub). Termos gerais do portal: informações "de domínio público, gratuitas e podem ser reproduzidas desde que citada a fonte". FAQ da API: cobrar por aplicativo que use os dados não tem restrição. Que os termos do portal alcancem a API é **inferência**. | Sim: "Câmara dos Deputados" | Uso permitido; licença formal **a confirmar** (pedido pronto em `docs/licencas/pedidos.md`). Limite de requisições não documentado (já observamos HTTP 429): usamos pausa, novas tentativas e arquivos em lote. |
| **CEAP** (cota parlamentar) | Sem página própria; é publicada no mesmo portal. Presume-se o mesmo regime da Câmara (**inferência**). | Sim: Câmara dos Deputados | Mesmo status da Câmara. Atenção: traz CPF/CNPJ de fornecedores, que podem ser pessoa física. |
| **TSE** (candidaturas, prestação de contas, votação) | "Creative Commons Attribution" (CC BY) no campo de licença de cada conjunto de 2022 (candidatos, resultados, prestação de contas). A versão da licença não é declarada. A Portaria TSE 93/2021 (política de dados abertos) existe, mas o site do TSE bloqueou a leitura do texto: não a citamos. | Sim (CC BY) | Confirmado para os conjuntos de 2022. A licença **não** dispensa as obrigações de LGPD sobre CPF e dados pessoais. |
| **CGU**: CEIS e CNEP | Catálogo dados.gov.br: licença "Other (Public Domain)" (**leitura indireta**). Base legal geral: Decreto 8.777/2016, que fala em licença aberta e reuso irrestrito, "limitando-se a creditar a autoria ou a fonte". O Portal da Transparência remete a "Termos de Uso" que a nossa ferramenta não conseguiu abrir (HTTP 405). | Sim: CGU, Portal da Transparência | Provável uso livre com crédito. Conferir o campo no navegador e, se quiser segurança formal, pedir à CGU. |
| **CGU**: emendas parlamentares | Catálogo dados.gov.br: licença **não especificada** (leitura indireta). Vale a base legal do Decreto 8.777/2016 (**inferência**). | Sim: CGU, Portal da Transparência | **A confirmar** (nenhuma licença nomeada achada). |
| **CGU**: lista de PEP | Catálogo dados.gov.br: licença **não especificada** (leitura indireta). A página de download do Portal da Transparência não traz licença e diz "Origem das informações: CGU". Vale o Decreto 8.777/2016 (**inferência**). | Sim: CGU, Portal da Transparência | **A confirmar** (nenhuma licença nomeada achada). Ver a seção do OpenSanctions. |
| **Receita Federal** via **BrasilAPI** (CNPJ) | BrasilAPI: código MIT, mas **sem termos de uso dos dados** ("ainda elaborando"); pede para não fazer crawling automatizado. | Sim (Receita Federal) | Usamos só para uma amostra pequena e limitada de CNPJs. **Não é adequada para ingestão em massa**; para cobertura nacional o plano é o arquivo mensal da Receita. |
| **Receita Federal**: conjunto CNPJ (arquivo mensal) | Catálogo dados.gov.br: licença "Creative Commons Attribution" (CC BY), publicador Receita Federal, atualização mensal (**leitura indireta**). A página de dados abertos do CNPJ no gov.br da Receita redireciona para esse conjunto. Não achamos portaria que formalize a escolha da licença. | Sim (Receita Federal) | CC BY: uso livre, inclusive comercial, com crédito. Conferir o campo no navegador. |
| **OpenSanctions** (`br_pep`) | **CC BY-NC 4.0** (uso **não comercial**, com atribuição e indicação de alterações). Os dados originais vêm da CGU. | Sim | Ver a seção abaixo. |
| **IBGE** (localidades) | Termos da API **não encontrados** (o site bloqueou a leitura). Sinais: o Plano de Dados Abertos 2024-2025 do IBGE diz seguir o Decreto 8.777/2016; um e-mail oficial do IBGE de 2013, repassado por terceiro, diz que o conteúdo do portal é "de domínio público" com citação da fonte. | Sim (prática) | Uso para códigos de município (dado público e de baixo risco). Termos da API **a confirmar**. |
| **Fotos oficiais** (Câmara) | O Banco de Imagens da Câmara diz que as imagens "podem ser livremente utilizadas, sem custo e sem necessidade de autorização", sob CC BY, com crédito. Que os retratos de `/internet/deputado/bandep/` estejam sob a mesma licença **não está escrito** em nenhuma página que achamos (**inferência**). | "Câmara dos Deputados" | Exibimos por link, sem copiar. |

## OpenSanctions: fonte opcional, com aviso

Decisão do projeto: o `br_pep` do OpenSanctions é uma **fonte opcional**.

Os dados do `br_pep` estão sob **CC BY-NC 4.0**. O OpenSanctions diz que os dados em massa são gratuitos para uso não comercial e que "Businesses must acquire a data license to use the dataset". Isto significa que:

- o **código** que os baixa é MIT, mas **os dados não**: nunca os apresentamos como MIT e **não os redistribuímos** neste repositório (as fixtures de teste são sintéticas);
- quem usar este projeto para **fins comerciais** deve **desativar essa fonte** (por exemplo, rodando a ingestão sem `opensanctions` em `--fontes`) ou obter licença própria junto à OpenSanctions (<https://www.opensanctions.org/licensing/>);
- é preciso citar a fonte e indicar se houve alterações;
- a página do OpenSanctions não trata de projetos de código aberto; o nosso caso (gratuito, acadêmico, sem fins lucrativos) cabe no espírito dos exemplos de uso não comercial, mas **não há confirmação formal**. Pedido de esclarecimento pronto em `docs/licencas/pedidos.md`.

**Caminho de saída:** há uma issue para migrar o `br_pep` para o arquivo de PEP da CGU (<https://portaldatransparencia.gov.br/download-de-dados/pep>). Sobre a licença desse arquivo: o catálogo dados.gov.br não especifica licença (leitura indireta) e a página de download não cita nenhuma. Como a CGU é Poder Executivo federal, vale o Decreto 8.777/2016 (reuso irrestrito, creditando a fonte), mas isso é **inferência**. Recomendação: migrar só depois de a CGU confirmar por escrito (pedido pronto em `docs/licencas/pedidos.md`) ou de conferirmos o campo no navegador. Atenção: o arquivo da CGU e a compilação do OpenSanctions podem ter campos diferentes.

## Texto de atribuição sugerido

Textos completos, por fonte, para o site e o README: [`docs/licencas/atribuicao.md`](docs/licencas/atribuicao.md). Ajuste a data de acesso. Resumo:

- **Câmara:** "Dados: Câmara dos Deputados, Dados Abertos (dadosabertos.camara.leg.br), acessados em AAAA-MM-DD."
- **CEAP:** "Despesas da Cota para o Exercício da Atividade Parlamentar (CEAP): Câmara dos Deputados, Dados Abertos."
- **TSE:** "Dados: Tribunal Superior Eleitoral, Portal de Dados Abertos (dadosabertos.tse.jus.br), licença CC BY. Processados pelo Raio-X Parlamentar."
- **CGU:** "Dados: Controladoria-Geral da União, Portal da Transparência (portaldatransparencia.gov.br): CEIS, CNEP e emendas parlamentares."
- **Receita Federal:** "Dados: Receita Federal do Brasil, Cadastro Nacional da Pessoa Jurídica (CNPJ), Dados Abertos, licença CC BY. Processados pelo Raio-X Parlamentar."
- **OpenSanctions:** "OpenSanctions br_pep (opensanctions.org/datasets/br_pep/), dados originais da CGU, licença CC BY-NC 4.0; uso não comercial; alterações indicadas pelo projeto."
- **IBGE:** "Fonte: IBGE (servicodados.ibge.gov.br)."
- **Fotos:** "Foto: Câmara dos Deputados."

## Dados pessoais

Ser público não dispensa finalidade, boa-fé e interesse público (LGPD, art. 7º, §3º: o tratamento "deve considerar a finalidade, a boa-fé e o interesse público"). O projeto tem finalidade declarada (transparência e ensino), minimiza dados (amostra pseudonimizada, nenhum CPF íntegro em respostas) e oferece canal de correção. Veja `docs/politica-de-uso-e-correcao.md` e `SECURITY.md`. Nenhuma das licenças acima (CC BY, domínio público, Decreto 8.777) elimina essas obrigações.

## Pendências (ajude a fechar)

Fechadas nesta rodada: licença do conjunto CNPJ (CC BY, leitura indireta), do TSE (CC BY, lida direto), do CEIS e do CNEP (domínio público, leitura indireta); licença das imagens do Banco de Imagens da Câmara (CC BY); política do OpenSanctions (CC BY-NC 4.0; contato e licenciamento).

Ainda abertas:

1. **Conferência visual no navegador** do campo "Licença" dos conjuntos CNPJ, CEIS, CNEP, emendas e PEP no dados.gov.br (a ferramenta de verificação não abre o catálogo). Links no resumo.
2. **Enviar os pedidos** de `docs/licencas/pedidos.md`: Câmara (licença da API, do CEAP e das fotos `bandep`), CGU (emendas e PEP, e termos do Portal da Transparência) e OpenSanctions (repositório aberto, gratuito, acadêmico).
3. Ler os **Termos de Uso do Portal da Transparência** e a **Portaria TSE 93/2021** num navegador (os sites bloquearam a leitura automática).
4. **IBGE:** achar os termos da API de localidades (ou perguntar, se quiser registro formal).
5. Migrar o `br_pep` para a CGU quando a licença estiver confirmada (issue já aberta).
