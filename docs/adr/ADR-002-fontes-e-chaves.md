# ADR-002 — Fontes de dados e chaves de ligação
Status: Proposto · 2026-11-22

## Contexto
Os dados vêm de seis órgãos sem chave comum. O deputado é identificado pelo `id` da Câmara; o TSE usa
`sq_candidato` e CPF; as emendas (CGU) trazem só o nome do autor; o OpenSanctions (PEP) traz nome e CPF
mascarado; a CEAP tem `idDocumento` repetido em milhares de linhas. Homonímia é comum e ligar a pessoa
errada seria um dano real ao cidadão (LGPD, honra).

## Decisão
1. **Candidatura → deputado** (`ingest/resolve/candidatura.py`): CPF íntegro igual = cf 1,0; senão nome de
   urna/civil normalizado + UF, único nos dois sentidos = 0,8; ambíguo desempatado por partido = 0,7;
   sem desempate **não liga** e vai para `entity_ambiguity`. CPF íntegro diferente descarta o par.
2. **Emenda → deputado**: nome do autor normalizado único = 0,8 (a emenda não traz a UF do autor).
3. **PEP → deputado** (só link): nome + CPF mascarado compatível = 0,95; nome civil = 0,7; nome parlamentar = 0,5.
4. **CNPJ**: casamento exato, cf 1,0 (CEAP ↔ empresa RFB ↔ sanção CEIS/CNEP).
5. `deputado_id` só é gravado no fato quando cf ≥ 0,7 (`CF_MIN_ENRIQUECER`); abaixo disso fica só o link.
6. **Chave CEAP determinística**: `{idDocumento|sem-doc}:{sha1(campos da linha)[:10]}`; linhas idênticas ganham
   sufixo `-2`, `-3`. O `idDocumento` sozinho não serve (cerca de 9 mil ids se repetem em créditos/ajustes), e o hash
   torna a chave estável entre lotes (reprocessar não duplica). `id_oficial` mantém o id da Câmara.
7. **OpenSanctions**: usar `targets.nested.json` (JSON Lines), não o CSV simples, porque só o nested traz cargo,
   órgão e datas exigidos por `docs/fact_types.md`. Licença CC BY-NC 4.0 (uso acadêmico não comercial).
8. **RFB via BrasilAPI** só para os CNPJs que aparecem (evita a base completa de ~17 GB).

## Alternativas rejeitadas
- Ligar por nome sem desempate: produziria falsos positivos em homônimos.
- CSV do OpenSanctions: não tem cargo/datas.
- Chave CEAP = `idDocumento`: colide.

## Consequências
Cada ligação carrega CF e método auditáveis. O CPF do deputado é coletado de `GET /deputados/{id}` (`detalhar_deputados`, `--detalhar-deputados`); na amostra 20/20 candidaturas ligam por CPF (cf 1,0) e 20/20 PEP por CPF (0,95). Sem essa flag, a ligação cai em nome (0,8/0,7). Fonte `processo`
ainda não existe.
