# ADR-008 — Jev como juiz consultivo opcional (extensão proposta)
Status: Proposto · 2026-11-26

## Contexto
O núcleo do Raio-X é um sistema especialista determinístico: regras em YAML, fatores de certeza (CF) estilo MYCIN e guardrails
(ADR-001, ADR-004). Isso o torna auditável e explicável. Existem, porém, três pontos em que a decisão não é uma regra, e sim uma
**escolha entre opções fechadas**:
1. entender uma pergunta em texto livre e mapeá-la a um dos 5 objetivos do `/perguntar` (`alinhado_governo`, `risco_integridade`,
   `concentracao_eleitoral_emendas`, `pontuacao_producao_legislativa`, `merece_atencao_fiscalizacao`);
2. desempatar homônimos na resolução de entidades (`ingest/resolve/`);
3. sugerir a ordem de leitura dos findings para o analista.

O Jev é um modelo proprietário da TypeSafe AI (acesso antecipado desde 15/09/2026, apenas via API, não open source) que não conversa:
escolhe entre opções fechadas e devolve probabilidade e confiança. Princípio: "o modelo julga, o código controla". A descrição vem do
artigo https://insights.eximia.co/engenharia/o-que-e-o-jev-e-como-ele-muda-a-arquitetura-de-software/; a documentação oficial
(docs.typesafe.ai) **não pôde ser verificada**. Limitações declaradas: a saída é sempre válida, mas nem sempre correta; não é
determinístico; o inglês é o idioma principal (português precisa de validação); contexto de 64 mil tokens; os números de desempenho
são da própria empresa.

## Decisão
- Criar a interface `engine/judge.py` (ainda **não existe**) com `decidir(pergunta, opcoes) -> Decisao(opcao, probabilidade, confianca)`.
- `NullJudge` é o padrão: determinístico, sem rede (ex.: casa palavras-chave ou devolve "sem decisão"). `JevJudge` é opcional.
- **O julgamento nunca altera CF, regras nem guardrails.** Ele só escolhe uma opção de roteamento, desempate ou ordenação; a
  conclusão continua sendo calculada por `engine/forward.py` e `engine/backward.py`.
- Só dado público ou pseudonimizado vai para o julgador; **nunca CPF** (ADR-006). Texto livre do usuário passa por filtro de CPF/CNPJ antes do envio.
- Cada decisão é registrada em log (entrada enviada, opções, escolha, probabilidade, confiança, versão do modelo).
- Controlado por feature flag, **desligada por padrão** (ex.: `RAIO_X_JUDGE=null|jev`).
- Nenhuma chave de API no repositório; a chave vem de variável de ambiente.
- Antes de ligar: validar em português com um conjunto de casos rotulados do projeto e medir o acerto.
- Abaixo de um limiar de confiança, o sistema recai no `NullJudge` ou pergunta ao usuário.

## Alternativas consideradas
- **LLM generativo** (texto livre): rejeitado; pode inventar fatos e viola a explicabilidade e o princípio de não atribuir culpa.
- **Classificador próprio** (treinado com dados do projeto): viável, mas exige dados rotulados que não temos; fica como plano B.
- **Nada**: é o comportamento padrão e continua válido; a extensão só agrega conveniência (roteamento e triagem).

## Consequências
- Positivas: melhor usabilidade no texto livre; desempate auxiliar; núcleo intacto e testável sem rede.
- Riscos: custo de API de terceiro; não determinismo (mesma entrada pode dar saídas diferentes, por isso o log); privacidade
  (LGPD e ADR-006: o que sai do servidor precisa ser público ou pseudonimizado); dependência de fornecedor proprietário em acesso
  antecipado; qualidade em português desconhecida até validar.
- Mitigação: interface substituível, `NullJudge` como padrão, log de auditoria, limiar de confiança.
