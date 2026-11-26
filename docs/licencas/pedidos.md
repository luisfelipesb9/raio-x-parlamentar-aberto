# Rascunhos de pedidos às fontes

Textos curtos, em português, prontos para copiar e enviar. **Nada foi enviado.** Antes de enviar:

- troque `[CONTATO DO PROJETO]` por um contato público do projeto (por exemplo, um e-mail institucional ou o endereço das issues do repositório). Não use e-mail ou telefone pessoal;
- guarde o número de protocolo e a resposta, e cole a resposta oficial (com link ou anexo) numa issue, para atualizar `DATA_LICENSES.md`;
- se a resposta mudar a licença, atualize também `docs/licencas/atribuicao.md`.

Repositório: https://github.com/luisfelipesb9/raio-x-parlamentar-aberto

## Canais (verificados em 26/11/2026)

| Órgão | Canal | Observação |
|---|---|---|
| Câmara dos Deputados | E-mail do Dados Abertos: `dadosabertos.ditec@camara.leg.br`. Página de contato: https://dadosabertos.camara.leg.br/contact/contact.html. Dúvidas técnicas: issues em https://github.com/CamaraDosDeputados/dados-abertos/issues (monitorado pela Diretoria de Inovação e TI). Geral: Fale Conosco, https://www.camara.leg.br/fale-conosco | Comece pelo e-mail ou pela issue; o Fale Conosco é o canal geral do portal. |
| CGU | Suporte do Dados Abertos: `suporte.dadosabertos@cgu.gov.br` (área de negócio, indicado na página da API do Portal de Dados Abertos no catálogo Conecta gov.br: https://www.gov.br/conecta/catalogo/apis/api-portal-de-dados-abertos). Pedido de acesso à informação: Informa.BR, https://informabr.cgu.gov.br/ | Uma página do gov.br diz que o módulo de acesso à informação do Fala.BR passou a ser acessado pelo Informa.BR a partir de 30/06/2026; outra ainda cita https://falabr.cgu.gov.br/. Se um não abrir, use o outro. |
| Receita Federal | Informa.BR (mesmo endereço acima); o termo de uso da Receita indica o Fala.BR para dúvidas sobre ele | Só use se quiser confirmação formal; o campo de licença do CNPJ já diz CC BY (leitura indireta). |
| OpenSanctions | `info@opensanctions.org` e https://www.opensanctions.org/contact/ | Contato geral público do projeto. |
| IBGE | Fale Conosco: https://www.ibge.gov.br/atendimento.html | Não achamos canal específico para a API. |

---

## (a) Câmara dos Deputados

**Para:** `dadosabertos.ditec@camara.leg.br` (Dados Abertos, DITEC). Alternativa: abrir uma issue em https://github.com/CamaraDosDeputados/dados-abertos/issues com o mesmo texto.

**Assunto:** Declaração de licença de uso: API de Dados Abertos, arquivos do CEAP e fotos oficiais dos deputados

Prezados,

Somos um projeto aberto, gratuito e sem fins lucrativos, de caráter acadêmico (Sistemas Especialistas, BSI/Unimontes), chamado Raio-X Parlamentar. Ele reúne dados públicos sobre deputados federais num grafo navegável, sempre com o link para a fonte oficial e o nível de certeza de cada informação. O código é MIT; não redistribuímos os dados no repositório.

Usamos a API v2 de dados abertos, os arquivos em lote de votações, os arquivos do CEAP e as imagens dos deputados (exibidas por link, a partir do endereço da Câmara, sem cópia).

Não encontramos uma licença nomeada nas páginas do portal de Dados Abertos. Encontramos os Termos gerais do portal ("domínio público, gratuitas e podem ser reproduzidas desde que citada a fonte") e o Banco de Imagens (CC BY). Pedimos, por favor, a confirmação de:

1. Os dados da API e dos arquivos em lote (incluindo o CEAP) podem ser reutilizados, inclusive em projeto de código aberto, com a citação "Câmara dos Deputados"? Existe uma licença formal (por exemplo, CC BY) ou uma política que possamos citar?
2. As fotos oficiais servidas em `camara.leg.br/internet/deputado/bandep/<id>.jpg` (campo `urlFoto` da API) seguem a mesma licença CC BY do Banco de Imagens? Qual crédito devemos exibir quando não há fotógrafo identificado?
3. Existe limite de requisições à API que devamos respeitar? (Observamos respostas HTTP 429 e já usamos pausa e novas tentativas.)

Repositório: https://github.com/luisfelipesb9/raio-x-parlamentar-aberto

Agradecemos a atenção.
[CONTATO DO PROJETO]

---

## (b1) CGU (Portal da Transparência e dados.gov.br)

**Para:** `suporte.dadosabertos@cgu.gov.br`. Se preferir registro formal, faça um pedido de acesso à informação no Informa.BR (https://informabr.cgu.gov.br/) com o mesmo texto.

**Assunto:** Licença de uso dos conjuntos Emendas Parlamentares e Pessoas Expostas Politicamente (Portal da Transparência)

Prezados,

Somos um projeto aberto, gratuito e sem fins lucrativos, de caráter acadêmico, chamado Raio-X Parlamentar. Ele cruza dados públicos sobre deputados federais (candidaturas, empresas, sanções, emendas) e mostra o nível de certeza de cada achado, com o link para a fonte oficial. O código é MIT; não redistribuímos os dados no repositório.

Usamos os arquivos de download de dados do Portal da Transparência: CEIS, CNEP, emendas parlamentares e a lista de PEP. No catálogo dados.gov.br, os conjuntos de emendas e de PEP aparecem sem licença especificada, e as páginas de download não trazem a licença. Os Termos de Uso do Portal não indicam a licença dos conjuntos.

Pedimos, por favor, a confirmação de:

1. Os conjuntos de emendas parlamentares e de PEP estão sob licença aberta, nos termos do Decreto 8.777/2016, podendo ser reutilizados por terceiros (inclusive em projetos abertos e não comerciais), com a citação da fonte? Se houver licença nomeada, qual?
2. Qual o texto de atribuição preferido pela CGU? (Sugerimos: "Dados: Controladoria-Geral da União, Portal da Transparência.")
3. O CEIS e o CNEP constam como domínio público no catálogo; podem ser reutilizados nas mesmas condições?
4. Existe limite de requisições para os arquivos em lote ou para a API que devamos respeitar?

Repositório: https://github.com/luisfelipesb9/raio-x-parlamentar-aberto

Agradecemos a atenção.
[CONTATO DO PROJETO]

## (b2) Receita Federal (opcional)

**Para:** Informa.BR (https://informabr.cgu.gov.br/), órgão destinatário: Receita Federal. Só envie se quiser a confirmação por escrito.

**Assunto:** Confirmação da licença do conjunto de dados abertos do CNPJ

Prezados,

Somos um projeto aberto, gratuito e sem fins lucrativos, de caráter acadêmico, chamado Raio-X Parlamentar. Ele cruza dados públicos sobre deputados federais e empresas, mostrando o nível de certeza de cada achado, com o link para a fonte oficial. O código é MIT; não redistribuímos os dados no repositório.

Pretendemos usar o arquivo mensal do CNPJ (dadosabertos.rfb.gov.br). No catálogo dados.gov.br, o conjunto "Cadastro Nacional da Pessoa Jurídica - CNPJ" consta com a licença Creative Commons Attribution. Pedimos, por favor, a confirmação de:

1. A licença do conjunto é de fato Creative Commons Attribution (CC BY)? Qual versão?
2. Qual atribuição devemos exibir? (Sugerimos: "Dados: Receita Federal do Brasil, Cadastro Nacional da Pessoa Jurídica (CNPJ), Dados Abertos.")
3. Há alguma restrição ao uso dos dados de sócios (QSA) em um projeto que cruza essas informações com dados de parlamentares, além do que a LGPD já exige?

Repositório: https://github.com/luisfelipesb9/raio-x-parlamentar-aberto

Agradecemos a atenção.
[CONTATO DO PROJETO]

---

## (c) OpenSanctions

**Para:** `info@opensanctions.org` (contato geral público: https://www.opensanctions.org/contact/). Escreva em inglês.

**Subject:** Using the br_pep dataset in a free, open-source, non-commercial academic project

Hello,

We maintain Raio-X Parlamentar, a free, non-profit, open-source (MIT) academic project from a Brazilian university (Information Systems course). It cross-references public data on Brazilian federal deputies and shows a certainty level and an official-source link for every finding.

We optionally ingest the `br_pep` dataset (https://www.opensanctions.org/datasets/br_pep/), licensed CC BY-NC 4.0, to flag politically exposed persons. Our code that downloads it is MIT, but we never commit or redistribute the dataset itself, and we credit OpenSanctions and the original publisher (CGU) with a note on any changes. Anyone using our code commercially is told to disable this source or obtain their own licence from you.

We read your "Free and non-commercial use" page, which does not mention open-source projects. Could you confirm:

1. Is this use (free, non-commercial, academic, bulk download, no redistribution of the data) within the CC BY-NC 4.0 terms as you understand them?
2. Is there a preferred attribution text for br_pep?
3. Is there anything you would like us to do differently, such as a notice in the README or the interface?

We are also considering switching this source to the CGU's own PEP file once its licence is confirmed.

Repository: https://github.com/luisfelipesb9/raio-x-parlamentar-aberto

Thank you,
[CONTATO DO PROJETO]

---

## (d) IBGE

**Para:** Fale Conosco do IBGE (https://www.ibge.gov.br/atendimento.html). Só necessário se quiser registro formal; o uso do projeto é só de códigos de município.

**Assunto:** Termos de uso e atribuição da API de Localidades (servicodados.ibge.gov.br)

Prezados,

Somos um projeto aberto, gratuito e sem fins lucrativos, de caráter acadêmico, chamado Raio-X Parlamentar, que cruza dados públicos sobre deputados federais, sempre com o link para a fonte oficial. O código é MIT; não redistribuímos dados no repositório.

Consultamos a API de Localidades (`servicodados.ibge.gov.br/api/v1/localidades`) apenas para obter códigos e nomes de municípios e estados. Não encontramos, na documentação da API, os termos de uso ou a licença dos dados. Pedimos, por favor, a confirmação de:

1. Os dados da API de Localidades podem ser reutilizados em projeto de código aberto, inclusive com cópia local dos códigos e nomes, citando o IBGE como fonte? Existe licença formal?
2. Qual a forma de citação preferida? (Sugerimos: "Fonte: IBGE (servicodados.ibge.gov.br).")
3. Existe limite de requisições?

Repositório: https://github.com/luisfelipesb9/raio-x-parlamentar-aberto

Agradecemos a atenção.
[CONTATO DO PROJETO]
