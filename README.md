# Raio-X Parlamentar

Tudo o que é público sobre um deputado federal — votos, projetos, gastos, emendas, financiamento,
empresas e sanções — explicado em linguagem simples, com cada conclusão mostrando **como** foi
obtida e **o quanto** é certa.

É um **Sistema Especialista**: base de fatos (dados oficiais), base de conhecimento (regras em
`knowledge/rules/`), motor de inferência com fatores de certeza e módulo de explicação.

> **Pedro, comece aqui:** siga [docs/PEDRO_OODA.md](docs/PEDRO_OODA.md) (passo a passo do primeiro dia e do deploy).
> As tarefas estão nas [Issues](https://github.com/luisfelipesb9/raio-x-parlamentar/issues), em ordem de prioridade (P0 primeiro).

- Comece por [AGENTS.md](AGENTS.md) (mapa do repositório e regras).
- Arquitetura: [docs/arquitetura.md](docs/arquitetura.md) · Status/divisão: [docs/HANDOFF.md](docs/HANDOFF.md) · Decisões: [docs/adr/](docs/adr/README.md) · Relatório: [docs/relatorio/relatorio.md](docs/relatorio/relatorio.md)

```
make setup && make test
```
