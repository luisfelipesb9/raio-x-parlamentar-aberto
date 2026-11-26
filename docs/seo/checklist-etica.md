# Checklist de revisão ética de páginas públicas sobre pessoas

Use antes de publicar ou atualizar qualquer página, post, resumo ou exemplo que fale de deputados, doadores, sócios ou fornecedores. Cada item é "sim" ou "não". **Um "não" bloqueia a publicação** até ser corrigido. Origem: `docs/politica-de-uso-e-correcao.md`, `DATA_LICENSES.md` e as regras R02 e R08 do projeto. Não é parecer jurídico; em caso de dúvida legal, pedir orientação a quem tenha competência para isso.

Página: ____________  Revisor 1: ____________  Data: ________  Revisor 2 (obrigatório em risco alto): ____________

## A. Não acusação

- [ ] A página traz o aviso de que **não é acusação** perto do topo (texto padrão em `briefs/README.md`).
- [ ] Nenhuma frase afirma crime, fraude, corrupção, desvio, "esquema", "laranja", "caixa dois" ou "irregularidade" como fato.
- [ ] Os verbos são "indica", "aponta", "merece conferência". Nada de "prova", "comprova", "revela", "denuncia", "flagra".
- [ ] Nenhuma frase atribui intenção ou conhecimento ("sabia", "quis", "escondeu").
- [ ] A **limitação principal** da regra aparece junto do resultado, não só no fim ("não prova que o deputado sabia da sanção", "correlação não é causa").
- [ ] Título, meta description, texto de imagem social e JSON-LD seguem as mesmas regras (o título é o que os motores mais repetem).

## B. Nível de certeza

- [ ] Todo achado mostra o **nível de certeza** (alta, média, indício, inconclusivo) e o fator, e diz que não é probabilidade.
- [ ] Indício (CF abaixo de 0,4, como a R06b) está escrito como indício, sem texto que o promova.
- [ ] A página diz que os fatores e limiares **não foram calibrados** (quando fala de CF ou de limiar).
- [ ] Nenhum número foi arredondado de modo a mudar o nível (por exemplo, 0,665 não vira "alto").

## C. Fonte e data

- [ ] Cada fato tem **link da fonte oficial** que foi aberto por quem revisa (não link copiado de busca).
- [ ] Cada número tem a **data de coleta** ou a data da consulta.
- [ ] O **escopo** está dito: 20 deputados de MG, período das votações, ano da cota, eleição usada. Nada de "os deputados" sem recorte.
- [ ] Número de terceiros (Transparência Brasil, imprensa, Radar) foi lido **na fonte original**, não em resumo de busca.
- [ ] O texto distingue o que o sistema calculou do que a fonte oficial publica.
- [ ] Nada do que se sabe só por hipótese está escrito como fato.

## D. Sem ranking de "piores"

- [ ] A página não ordena pessoas por gasto, governismo, emendas, pontuação ou risco.
- [ ] Não há "top 10", "quem mais", "quem menos" nem título que sugira ordem de culpa.
- [ ] Se o leitor pedir ranking (prompts P03, P10, P16), a página explica por que não há e aponta a fonte oficial ou externa que o publica.
- [ ] Média do partido ou da amostra aparece só como **contexto**, nunca como conclusão sobre a pessoa.
- [ ] Nenhuma nota moral ou semáforo de "bom" e "mau" sobre pessoa.

## E. Processo, simbólica e falta de dado

- [ ] **Processo sem condenação definitiva não é culpa:** a página não usa processo em andamento como achado (R08) e diz que o projeto ainda não tem fonte de processos.
- [ ] **Votação simbólica não é voto individual:** nenhuma frase atribui voto a quem votou de forma simbólica; as contas de voto usam só votação nominal (R02).
- [ ] **Falta de dado não é zero:** deputado sem registro aparece como "sem dado", não como "nenhuma produção" ou "nenhum gasto".
- [ ] Nenhum "não há problema" é concluído da ausência de achado: a página diz que ausência de achado não é atestado.

## F. Dados pessoais e LGPD

- [ ] **Nenhum CPF** aparece, inteiro ou parcial, em texto, imagem, captura, JSON-LD ou exemplo.
- [ ] Nome de pessoa física **não confirmada** (sócio, doador com identidade em dúvida) **não** aparece (R06b).
- [ ] Nenhum dado de parente ou de terceiro que não seja público e oficial.
- [ ] Exemplos e capturas usam **dados fictícios** da demonstração e dizem "exemplo fictício". Se usarem dado real, há justificativa de interesse público e a revisão 2 aprovou.
- [ ] Nenhuma página replica tabela de `docs/relatorio/comparacao-externa.md` com nomes de deputados.
- [ ] Foto de deputado, quando houver, é exibida por link com crédito "Câmara dos Deputados" (`DATA_LICENSES.md`); a licença formal das fotos está **a confirmar**.
- [ ] Atribuição de cada fonte está correta e a regra de uso não comercial da OpenSanctions está respeitada.
- [ ] O JSON-LD não inclui dado pessoal além do que a página já exibe.

## G. Canal de correção

- [ ] A página linka a **política de uso e correção** e diz como pedir correção (issue "Correção de dado", com fonte oficial e **sem CPF**).
- [ ] Existe um responsável nomeado para atender correções e um prazo declarado como "razoável, projeto voluntário", sem prazo contratual.
- [ ] Quando houve correção, ela está no CHANGELOG e a data de revisão da página mudou.
- [ ] Erro de identidade (homônimo, ligação errada) leva à **remoção** do dado, não à nota de rodapé.

## H. Honestidade sobre o projeto

- [ ] A página não diz que o projeto é fonte oficial, parecer jurídico ou tribunal.
- [ ] Não diz que as regras foram validadas por especialistas ou leigos (não foram) nem que a comparação externa cobre mais do que a R01.
- [ ] Não diz "completo", "líder", "inovador", "o melhor".
- [ ] Não promete atualização automática ou em tempo real.
- [ ] Nenhuma ferramenta de IA aparece como autora, coautora ou assistente em texto, créditos ou metadados.

## I. Conferência técnica mínima

- [ ] Todos os links abrem (sem 404) na data da revisão.
- [ ] Os valores de limiar e CF batem com `knowledge/rules/*.yaml` na data da revisão.
- [ ] O JSON-LD diz o mesmo que o texto visível.
- [ ] Data de publicação e de última revisão estão visíveis.

## Páginas de risco alto (exigem revisor 2 e, nas R06 e R09, pessoa de fora da equipe)

`/regras/r03`, `/regras/r06`, `/regras/r07`, `/regras/r08`, `/regras/r09`, qualquer página que responda P19, P20 ou P21, e qualquer uso de dado real de uma pessoa.

## Se a revisão falhar

Não publicar. Registrar o item reprovado, corrigir e repetir a revisão inteira (não só o item).
