# ADR-009 — A API lê o manifesto do bruto (exceção a "a API só lê o banco")
Status: Proposto · 2026-11-26

## Contexto
`AGENTS.md` diz que `api/` e `web/` só leem o banco. Mas `Evidence.sha256_bruto` (contrato v0.2.0, ADR-007) vem do
manifesto `data/raw/manifest.json`, e findings gravados antes de o motor preencher esse campo ficam sem o hash. Para
completá-los na leitura, a API consulta o manifesto. Isso é leitura de arquivo, fora do banco, e a primeira versão
ainda importava o pacote `sources` (seis plugins de coleta, com dependências de rede) só para isso, o que pesava no
cold start da API.

## Decisão
- Exceção documentada: a API pode ler, **somente leitura e de forma opcional**, `data/raw/manifest.json` (pasta
  `$RAIO_X_RAW` ou `data/raw`; ou `raw_dir` em `create_app`). Sem o arquivo (deploy sem `data/raw`), o hash fica vazio e
  nada falha. Arquivo ilegível vira aviso no log e hash vazio; a API não quebra.
- O código de leitura mora em `repo/proveniencia.py`, módulo folha (só biblioteca padrão), sem importar `sources`.
  `sources/manifest.py` (quem escreve o manifesto) importa dali o formato e a leitura. Um teste garante que
  `import api.state` não carrega o pacote `sources`.
- O mapa `Fact.fonte` -> pasta da fonte também mora em `repo/proveniencia.py` (`ORIGEM_POR_FONTE_FATO`). Um teste confere
  que ele é igual ao derivado de `fontes_fato` dos plugins: fonte nova obriga a atualizar os dois.
- `sources/base.py` e `sources/manifest.py` importam `repo.proveniencia`. É a segunda exceção de direção (`sources` ->
  `repo`), restrita a esse módulo folha, que não importa nada do projeto.

## Limitações e mitigação
- O hash vem do manifesto **atual**, não do usado no ingest: se o bruto foi refeito depois da inferência, o hash mostrado
  é o do arquivo novo.
- Mitigação: `python -m engine.run --raw PASTA` grava o `sha256_bruto` na evidência na hora da inferência. A API só
  completa findings antigos, nunca troca um hash já preenchido.
- Fonte com vários arquivos brutos (Câmara, CGU, RFB) continua sem hash: o fato não diz de qual arquivo veio.

## Consequências
Cold start da API sem os plugins de coleta; uma exceção a mais, pequena e testada. Quando os findings antigos forem
regravados com `engine.run --raw`, a leitura do manifesto na API pode ser removida.
