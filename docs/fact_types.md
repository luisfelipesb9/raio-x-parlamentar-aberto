# Tipos de fato (contrato de atributos)

Todo `Fact` tem `tipo`, `chave`, `fonte`, `id_oficial`, `url`. Abaixo, os `atributos` obrigatórios
(opcionais entre colchetes). Datas ISO `YYYY-MM-DD`. CNPJ/CPF só dígitos (CNPJ 14, CPF 11; mascarado
mantém `*`, ex. `***123456**`). IDs de deputado sempre string do `id` da Câmara.
Mudar este arquivo = ADR.

| tipo | chave | atributos | fonte (dono) |
|---|---|---|---|
| deputado | id_deputado | nome, partido, uf, [foto, cpf, nome_civil] | camara (A) |
| votacao | id_votacao | data, descricao, nominal(bool), orientacao_governo(Sim/Não/None) | camara (A) |
| voto | `{votacao}:{dep}` | votacao_id, deputado_id, voto | camara (A) |
| proposicao | id_proposicao | sigla_tipo, numero, ano, ementa, data | camara (A) |
| autoria | `{prop}:{dep}:{papel}` | proposicao_id, deputado_id, papel(autor/coautor/relator), [orgao] | camara (A) |
| despesa_ceap | id_documento | deputado_id, cnpj (ou cpf), fornecedor, valor(float), categoria, data | ceap (A) |
| sancao | `{cadastro}:{id}` | cnpj, cadastro(CEIS/CNEP), inicio, [fim], orgao | cgu (B) |
| emenda | codigo_emenda | deputado_id ou autor_nome, ano, valor_empenhado, valor_pago, municipio_ibge, [tipo(pix/...)] | cgu (B) |
| candidatura | sq_candidato | ano, cpf, nome, nome_urna, cargo, uf, partido, [deputado_id] | tse (B) |
| doacao | id_receita | sq_candidato, doador_nome, doador_cpf_cnpj, valor, data, tipo_doador(PF/PJ/proprio/partido) | tse (B) |
| votos_municipio | `{ano}:{sq}:{ibge}` | ano, sq_candidato, municipio_ibge, uf, votos, votos_validos_municipio | tse (B) |
| pep | id_opensanctions | nome, [cpf], cargo, orgao, inicio, [fim] | opensanctions (B) |
| empresa | cnpj | razao_social, situacao, cnae, [municipio_ibge] | rfb (B) |
| socio | `{cnpj}:{nome_norm}` | cnpj, nome, cpf_cnpj (pode vir mascarado), qualificacao | rfb (B) |
| processo | id | deputado_id, tipo, transitado_em_julgado(bool), [condenado(bool)] | (futuro) |

`entity_link` (repo, dono C): origem `tipo:chave`, destino `tipo:chave`, metodo (cpf|cnpj|nome_norm), cf.
`deputado_id` em candidatura é preenchido pela resolução (C).

## Notas (Onda 1)
- `despesa_ceap.chave` = sempre `{idDocumento|sem-doc}:{sha1(linha)[:10]}` (estável entre lotes; idênticas ganham -2,-3) (id_oficial mantém o id da Câmara). `data` pode ser None; `valor` pode ser negativo (estorno); placeholder de telefonia não gera cnpj/cpf.
- `autoria` coautor só com `proponente==1` (apoiadores de PEC não contam).
- Atributo `deputado_cf` (float 0–1) acompanha todo `deputado_id` preenchido pela resolução (candidatura, emenda); ausente = 1.0 (id vindo da própria Câmara). Predicados devem propagá-lo em `premissas_cf`.
- Pseudonimização (`--pseudonimizar`, ADR-006): CPF íntegro de terceiro → `hmac:<32hex>` + `*_visivel` (dígitos 4–9: `doador_cpf_visivel` na doação, `cpf_visivel` no sócio). CPF mascarado permanece mascarado (nunca vira hmac). CPF de deputado/candidato fica íntegro.

## Nota (Onda 4): CNPJ alfanumérico
- A Receita Federal emite, desde julho/2026, CNPJ de 14 posições com letras (12 primeiras em `A–Z`/`0–9`, 2 últimas de DV numérico; formatos numérico e alfanumérico coexistem). Fonte: [Perguntas e Respostas do CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf), pergunta 14.
- O contrato dos tipos **não muda**: `cnpj` (`despesa_ceap`, `sancao`, `empresa`, `socio`), `doador_cpf_cnpj` e `cpf_cnpj` continuam string de 14 caracteres, sem máscara. O "só dígitos" do cabeçalho vale para o CNPJ numérico; o alfanumérico é gravado em maiúsculas, sem `.`, `/` e `-`. CPF segue com 11 dígitos.
- Uma única implementação de forma e DV (módulo 11 sobre `ord(c) - 48`) em `sources/rfb/normalizacao.py` (`normalizar_cnpj`, `cnpj_valido`, `dv_cnpj`); `sources/ceap`, `sources/tse`, `sources/rfb` e `ingest/resolve` a usam. Fornecedor com CNPJ alfanumérico não perde o documento nem vira CPF (11 posições).
- Ainda só dígitos, fora desta nota: `sources/cgu`, `graph/build.py` e `engine/predicates/circuito.py` (ver pendências do PR).
