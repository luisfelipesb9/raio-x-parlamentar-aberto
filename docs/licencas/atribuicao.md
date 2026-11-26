# Texto de crédito por fonte

Pronto para o rodapé do site e para o README. Troque `AAAA-MM-DD` pela data real do acesso (ou da coleta) e o ano, quando indicado. Os marcados **(provisório)** dependem de confirmação listada em `DATA_LICENSES.md`.

Regras gerais:

- O crédito aparece **junto do dado** (ficha, grafo, explicação) sempre que possível, e a lista completa fica no rodapé e no README.
- Sempre que o projeto resumir, juntar ou calcular algo a partir do dado, escreva "processados pelo Raio-X Parlamentar". O projeto não é fonte oficial.
- Cada achado mantém o link para a fonte oficial (princípio de rastreabilidade).

## Bloco curto (rodapé do site)

> Dados públicos de: Câmara dos Deputados, Tribunal Superior Eleitoral (CC BY), Controladoria-Geral da União (Portal da Transparência), Receita Federal do Brasil (CNPJ, CC BY), IBGE e, opcionalmente, OpenSanctions (CC BY-NC 4.0, uso não comercial). Fotos: Câmara dos Deputados. Processados pelo Raio-X Parlamentar, que não é fonte oficial: confirme sempre na fonte indicada em cada achado. Detalhes: DATA_LICENSES.md.

## Texto por fonte

| Fonte | Texto de crédito | Condição por trás |
|---|---|---|
| Câmara dos Deputados (API e arquivos) | "Dados: Câmara dos Deputados, Dados Abertos (dadosabertos.camara.leg.br), acessados em AAAA-MM-DD. Informações de domínio público, reproduzidas com citação da fonte." | Termos gerais do portal: reprodução com citação da fonte "Câmara dos Deputados". Licença formal da API **a confirmar**. |
| CEAP | "Despesas da Cota para o Exercício da Atividade Parlamentar (CEAP): Câmara dos Deputados, arquivos de Dados Abertos, ano(s) AAAA." | Mesmo regime da Câmara (inferência). |
| TSE | "Dados: Tribunal Superior Eleitoral (TSE), Portal de Dados Abertos (dadosabertos.tse.jus.br), licença Creative Commons Atribuição (CC BY). Eleição de 2022. Dados processados pelo Raio-X Parlamentar." | CC BY (versão não declarada: não escreva "4.0"). |
| CGU: CEIS, CNEP, emendas parlamentares, PEP | "Dados: Controladoria-Geral da União (CGU), Portal da Transparência (portaldatransparencia.gov.br): CEIS, CNEP e emendas parlamentares, acessados em AAAA-MM-DD." **(provisório)** | CEIS e CNEP: domínio público no catálogo (leitura indireta). Emendas e PEP: licença não especificada; Decreto 8.777/2016. |
| Receita Federal (arquivo mensal do CNPJ) | "Dados: Receita Federal do Brasil, Cadastro Nacional da Pessoa Jurídica (CNPJ), Dados Abertos, arquivo de MM/AAAA, licença Creative Commons Atribuição (CC BY). Processados pelo Raio-X Parlamentar." | CC BY no catálogo dados.gov.br (leitura indireta). |
| BrasilAPI (se usada para CNPJ) | "Consulta de CNPJ via BrasilAPI (brasilapi.com.br); dado original da Receita Federal." | Código MIT; sem termos de uso dos dados. Só amostra pequena. |
| OpenSanctions `br_pep` (opcional) | "Dados de PEP do Brasil: OpenSanctions (opensanctions.org/datasets/br_pep/), com dados originais da CGU/Portal da Transparência, licença Creative Commons Atribuição-NãoComercial 4.0 (CC BY-NC 4.0). Alterações: normalização e cruzamento pelo Raio-X Parlamentar. Uso restrito a fins não comerciais." | CC BY-NC 4.0: mostre este texto **só** quando a fonte estiver ativa. |
| IBGE | "Fonte: IBGE (servicodados.ibge.gov.br), localidades, acessados em AAAA-MM-DD." **(provisório)** | Termos da API não encontrados; citar o IBGE é a prática pedida nos sinais oficiais. |
| Fotos dos deputados | "Foto: Câmara dos Deputados." (com fotógrafo identificado: "Nome do Fotógrafo/Câmara dos Deputados"; sem autoria: "Arquivo/Câmara dos Deputados") | Banco de Imagens: CC BY com crédito nesse formato. Extensão aos retratos `bandep` **a confirmar**. |

## Onde colocar

- **Site:** rodapé (bloco curto) e uma página "Fontes e licenças" com a tabela acima; crédito da foto como legenda pequena junto da imagem.
- **README:** seção "Dados e licenças" com o bloco curto e o link para `DATA_LICENSES.md`, deixando claro que **o código é MIT e os dados seguem a licença de cada fonte**.
- **Respostas da API:** campo de fonte em cada fato (já exigido: `fonte`, `id_oficial`, `url`).
- **Quando o OpenSanctions estiver desativado:** retire o crédito dele do rodapé; quando ativado, mantenha o aviso de uso não comercial visível.
