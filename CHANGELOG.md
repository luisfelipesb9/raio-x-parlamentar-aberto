# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Correções de dado
(veja a [política](docs/politica-de-uso-e-correcao.md)) também são registradas aqui.

## [0.2.0] - 2026-11-26
### Adicionado
- Mapa de relações legível: ligações nos dois sentidos, agrupamento de folhas, corte justo por relação e valor
  com resumo do que ficou de fora, e verbetes leigos no glossário.
- Diagnóstico do passo "inconclusivo" no encadeamento regressivo (`dados_insuficientes`, `abaixo_do_limiar`,
  `sem_regra_aplicavel`), exibido em Perguntar com os números.
- Cobertura e verificação: endpoints `/cobertura` e `/deputados/{id}/metricas`, manifesto do bruto com sha256,
  `coletado_em` nas evidências e `make verifica`, que recalcula governismo e CEAP direto dos brutos.
- Página **Fontes e método** e painel "Dados e verificação" na ficha, com "Verificar na fonte" em cada achado.
- Interface de juiz consultivo opcional, com implementação nula (ADR-008).
- Documentação de comunidade: licença MIT, guia de contribuição, código de conduta, política de segurança e política de uso e correção.

### Alterado
- Tema claro como padrão; o escuro só por escolha no botão.
- Contrato `contracts/` na versão 0.2.0 ([ADR-007](docs/adr/ADR-007-contrato-v0-2-0.md)).
- A API lê o manifesto do bruto ([ADR-009](docs/adr/ADR-009-api-le-manifesto-do-bruto.md)).
- Pseudonimização da base pública aceita ([ADR-006](docs/adr/ADR-006-pseudonimizacao.md)).

## [0.1.0] - 2026-11-22
### Adicionado
- Fundação: contratos, motor de inferência (fatores de certeza, encadeamento progressivo e regressivo),
  regras R01 a R09 e R06b em YAML, guardrails de votação simbólica e presunção de inocência.
- Fontes: Câmara, CEAP, CGU, TSE, OpenSanctions e RFB; pipeline de ingestão com resolução de entidades.
- Banco DuckDB, API somente leitura, projeção em grafo e site (ficha, grafo, perguntar, comparar, glossário).
- Pseudonimização HMAC e varredura de CPF para a base pública.
