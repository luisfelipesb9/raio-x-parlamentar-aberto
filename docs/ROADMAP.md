# Roteiro

Próximos passos, escritos como convite. "Bom para começar?" indica se a tarefa serve de porta de entrada.
Antes de começar, abra uma issue (modelos "Nova fonte" ou "Nova regra") e leia o [CONTRIBUTING](../CONTRIBUTING.md).

| Item | O que é | Bom para começar? |
|---|---|---|
| Fonte IBGE | Dados de municípios para contextualizar emendas e votos por município | Sim |
| Bens declarados no TSE | Patrimônio declarado na candidatura, para uma regra de evolução patrimonial | Não (exige regra nova e cuidado com identidade) |
| Presença e frentes parlamentares da Câmara | Novos fatos da API da Câmara para a ficha | Sim |
| Calibração dos fatores de certeza | Hoje são escolhas do especialista; calibrar com dados rotulados e documentar o método | Não |
| Cobertura dos 513 deputados | Hoje são 20 de MG; ampliar ingestão, janela de votações e desempenho | Não |
| Regressivo interativo | Deixar a pessoa escolher o objetivo e responder perguntas que faltam para o motor | Não |
| Validação com especialistas e leigos | Testar a linguagem e as regras com jornalistas, analistas e cidadãos; ver [HANDOFF](HANDOFF.md) | Sim (não exige código) |
| Fonte para o fato `processo` | O guardrail R08 existe, mas nenhum plugin produz `processo` ainda | Não |
| Comparação externa das demais regras | Hoje só a R01 foi comparada, ver [comparação externa](relatorio/comparacao-externa.md) | Sim |
