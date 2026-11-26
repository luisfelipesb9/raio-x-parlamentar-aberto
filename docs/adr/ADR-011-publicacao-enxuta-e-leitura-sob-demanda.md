# ADR-011 — Banco público enxuto e API sem snapshot global de fatos
Status: Proposto · 2026-11-26

## Contexto
A pesquisa de viabilidade ([`pesquisa.md`](../ampliacao/pesquisa.md)) e as medições ([`medicoes.md`](../ampliacao/medicoes.md))
mostram, para ampliar de 20 para 513 deputados na Vercel Hobby (envio pela CLI ≤ 100 MB; função ≤ 2 GB de RAM; ~4 h de CPU
ativa por mês):

1. O ingest nacional cabe de graça, local, em etapas.
2. O **banco público** como está (~185 MB extrapolados) não passa pelo envio de 100 MB. Metade do arquivo é o índice da chave
   primária; ~80% dos dados são `despesa_ceap` e `votos_municipio` crus.
3. O **`Snapshot`** da API carrega todos os fatos como objetos Python: ≈ 4,1 KB por fato (131 MB para 31,8 mil). Com 0,5–0,9 M de
   fatos passa dos 2 GB. Grafo (+1 MB) e inferência (+7 MB) são baratos.

## Decisão
Escolhemos o desenho (a) da pesquisa, sem custo e sem trocar de hospedagem: publicar uma **visão derivada enxuta** e ler **sob demanda**.

1. **Novo passo `publicar/`** (camada entre `graph/` e `api/`; pode importar tudo à esquerda, e só `api/`/`web/` leem o resultado;
   AGENTS.md e `docs/mapa-do-repositorio.md` ganham a linha). Entrada: o banco já pseudonimizado e com findings
   (`--pseudonimizar` + `engine.run`). Saída: o arquivo público, **sem chave primária nem índices**, com:
   - todos os `findings` e `explanation`, e a tabela `entity_link` dos fatos mantidos;
   - **só os fatos que a API ainda precisa**: `deputado`, `votacao`, `voto` (nominais), `proposicao`, `autoria`, `candidatura`,
     `sancao`, e os fatos de `despesa_ceap`, `votos_municipio`, `doacao`, `emenda`, `empresa`, `socio`, `pep` **citados como
     evidência** por algum finding (ou necessários ao nome de município/empresa de um nó do grafo);
   - tabelas novas **materializadas**: `graph_node` e `graph_edge` (saída de `graph.project`, calculada uma vez, sobre os fatos
     completos), `inferencia` (resultado do `forward.run`, por deputado, usado pelo encadeamento regressivo) e `publicacao_meta`
     (contagens por fonte e tipo no banco completo, janela de votos, data, versão do contrato, hash do banco de origem).
2. **A API deixa de montar o snapshot global.** `api/state.py` lê `graph_node`/`graph_edge` (objetos leves; estimativa nacional
   ~60–80 mil nós/arestas) e consulta o DuckDB **por deputado** para votos (`/comparar`), findings e evidências. `/perguntar` usa
   a tabela `inferencia`, sem rodar `forward.run` sobre todos os fatos. `/cobertura` lê `publicacao_meta`, para não subdeclarar
   a cobertura por causa do corte. Continua valendo "a API só lê": nenhum cálculo novo, só leitura de resultados já gravados.
3. **Contrato inalterado**: os tipos de `contracts/` e `docs/fact_types.md` não mudam (`CONTRACT_VERSION` fica em 0.2.0). As
   tabelas novas são do `repo/` (migration nova). Se aparecer necessidade de mudar tipo, abrir ADR própria e bump.
4. **Escopo do ingest nacional**: 513 deputados em exercício (não os 878 da legislatura); votos pelo dump anual quando a janela
   passar de um trimestre; CNPJ alfanumérico aceito (DV módulo 11 sobre ASCII); TSE por UF (`fetch_por_uf`); Receita pelo arquivo
   mensal filtrado só pelos CNPJs que aparecem nos dados (nunca BrasilAPI em massa); Câmara com nova tentativa e checkpoint.
5. **Mesmo sal** (`RAIO_X_ID_SALT`) na pseudonimização, para ids estáveis.

## Gatilho do plano B (decidir por medição, não por suposição)
Passar para Cloudflare R2 (arquivo) + API em Fly.io (~US$ 4–7/mês), ou Vercel Pro (US$ 20/mês), se, no teste com dados
nacionais: o arquivo público passar de **80 MB**; ou o pico de memória da API passar de **1 GB**; ou a partida a frio
passar de **10 s**. Qualquer custo exige novo ok do dono do projeto.

## Alternativas descartadas
- **Só tirar a chave primária**: reduz o arquivo à metade (~90 MB), mas não resolve a memória do snapshot.
- **JSON estático por deputado** (opção estática da pesquisa): resolve partida a frio, mas obriga a reescrever a camada de leitura; fica como reserva.
- **Publicar tudo e pagar Pro agora**: custo antes de medir.

## Consequências
- O banco público deixa de ser reprodutível por `make verifica` sozinho (faltam as despesas cruas): `verifica` continua rodando
  no banco de trabalho completo; no público passa a conferir que findings, contagens (`publicacao_meta`) e ausência de CPF
  batem com o banco de origem (hash registrado).
- Menos dado pessoal publicado (minimização, LGPD): despesas e doações que não sustentam achado ficam só no banco local.
  Quem quiser tudo reproduz com `make ingest` (código aberto).
- Mudança de arquitetura em `repo/`, `api/`, nova pasta `publicar/` e `Makefile`; migração do banco público atual por regeneração.
- Risco: nó do grafo que dependia de fato cortado. Mitigação: o grafo é materializado antes do corte; teste compara
  `/grafo` e `/perguntar` da amostra antes e depois (diferença esperada: nenhuma).

## Verificação (critérios de aceite)
Amostra de 20: respostas de `/deputados`, `/findings`, `/grafo`, `/perguntar`, `/comparar` iguais antes e depois.
Escala: teste sintético (amostra replicada com chaves distintas, **rotulado como sintético**) mede arquivo, pico de RAM e
partida a frio; depois, os mesmos números com dados nacionais reais. `make verifica`, `ingest.varredura` (0 CPF íntegro de
terceiro), `make deploy-check` e `seo-smoke` verdes.
