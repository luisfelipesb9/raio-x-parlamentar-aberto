# ADR-010 — O web lê o conteúdo e as regras no build (exceção a "web só lê o banco")
Status: Aceito · 2026-11-26

## Contexto
As páginas públicas de método, regras, FAQ, dados e estudantes (SEO/GEO) precisam repetir o que a base de conhecimento
diz: nome, limiar, janela, `cf` e penalidades de cada regra. Digitar esses números à mão em outro lugar faria o site
divergir do motor. `docs/mapa-do-repositorio.md` diz que `web/` só lê o banco (via API).

## Decisão
- Exceção documentada: `web/scripts/gen-conteudo.mjs` lê `docs/conteudo/**/*.md` e `knowledge/rules/R*.yaml` e grava
  `web/src/content/gerado/conteudo.json`, que é versionado.
- A leitura acontece **só em desenvolvimento e no CI** (`pnpm gen:conteudo`). O build do Next e o servidor leem apenas o
  JSON committed; **nunca** abrem `docs/` nem `knowledge/` em runtime e **nunca** chamam API externa.
- Um teste do web falha se `conteudo.json` for diferente da saída do gerador: editar um texto ou uma regra sem
  regenerar quebra o CI.
- O gerador usa um parser de YAML mínimo, sem dependência. Ele recusa escalares sem aspas que o `yaml.safe_load` do
  motor leria de outro jeito (`yes`, `no`, `.5`, `1_000`...), para não haver duas leituras do mesmo arquivo.
- Sentido do fluxo: `knowledge/` e `docs/` -> gerador -> JSON -> `web/`. O web não importa código Python nem a API.

## Consequências
Os parâmetros das regras no site vêm sempre do YAML. Quem muda uma regra precisa rodar `pnpm gen:conteudo` e
committar o JSON. O parser mínimo cobre só o subconjunto usado hoje; construção nova no YAML vira erro explícito.
