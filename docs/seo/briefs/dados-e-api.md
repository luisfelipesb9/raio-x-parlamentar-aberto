# Brief: Dados e API

- **URL sugerida:** `/dados-e-api`
- **Tipo:** documentação (`TechArticle`)
- **Prompts que atende:** P09, P25, P27, P28, P29
- **Público:** desenvolvedor, jornalista de dados, analista
- **Intenção:** decisão/uso ("como obtenho e uso estes dados?")

## Antes de escrever: o que o repositório permite afirmar

Do `api/main.py` (leitura de 2026-11-26), a API somente leitura expõe: `/saude`, `/deputados`, `/deputados/{id}`, `/deputados/{id}/findings`, `/deputados/{id}/metricas`, `/cobertura`, `/findings/{id}/explicar`, `/grafo`, `/grafo/backlinks/{node_id}`, `/perguntar`, `/comparar`. A documentação interativa fica em `/docs` da API (README). API em produção, segundo `docs/HANDOFF.md`: https://raio-x-api.vercel.app/saude (a confirmar que está de pé antes de publicar; não foi chamada neste estudo).

**Lacunas que o redator precisa fechar com os autores antes de publicar:** parâmetros e exemplos de resposta de cada rota; se a API pública tem limite de uso; se o banco de produção é pseudonimizado (o relatório diz que a base pública é); versão do contrato (`CONTRACT_VERSION` aparece no rodapé do site); endereço estável do repositório.

## Primeira frase citável

"A API do Raio-X Parlamentar é somente leitura e devolve, para cada deputado da amostra, os achados com nível de certeza, a trilha de explicação e o link da fonte oficial; os dados brutos continuam nas fontes oficiais (Câmara, TSE, CGU), que devem ser consultadas diretamente."

## Estrutura de H2

1. **O que a API entrega e o que não entrega** (lista das rotas acima; escopo de 20 deputados de MG; não redistribui dado bruto nem CPF)
2. **Como chamar** (um exemplo `curl` por rota principal, com a resposta real **de uma base fictícia**; bloco copiável; só incluir exemplo que alguém rodou)
3. **Formato de um achado** (campos de `Finding`, `Explanation`, `Evidence`; link para os contratos em `web/src/types/schemas/*.json` do repositório, link a confirmar)
4. **Como ler o nível de certeza** (CF e os quatro níveis; link para `/glossario/fator-de-certeza`)
5. **Como rodar o sistema na sua máquina** (`make setup`, `make demo`, `make dev-demo`; requisitos: Python 3.11+ com uv, Node 22 com pnpm; `RAIO_X_ID_SALT` e `RAIO_X_DB` para outro banco; "sem o sal a API não sobe")
6. **Como obter os dados oficiais** (Câmara: API em https://dadosabertos.camara.leg.br/ com documentação Swagger em `/swagger/api.html`, coleções de deputados, votações, proposições etc.; CEAP: tabela e CSV em https://www.camara.leg.br/transparencia/gastos-parlamentares; TSE: https://dadosabertos.tse.jus.br/ ; CGU: link a confirmar em navegador)
7. **Cuidados que aprendemos** (da `DATA_LICENSES.md` e do relatório, com a ressalva "no nosso uso": a API da Câmara já devolveu HTTP 429 e o limite não é documentado, por isso pausa, novas tentativas e arquivos em lote; o id de despesa da CEAP se repete, por isso o projeto monta uma chave com `idDocumento` mais hash da linha; o QSA vem com CPF mascarado; a BrasilAPI não é adequada para ingestão em massa)
8. **Licenças e atribuição** (tabela resumida de `DATA_LICENSES.md`: código MIT; TSE CC BY; Câmara sem licença nomeada, citar a fonte; CGU, Receita e IBGE a confirmar; OpenSanctions CC BY-NC 4.0, uso não comercial; textos de atribuição sugeridos)
9. **Dados pessoais e LGPD** (pseudonimização HMAC-SHA256 com sal; nenhum CPF íntegro na base publicada; "ser público não dispensa finalidade, boa-fé e interesse público", LGPD art. 7º, §3º; canal de correção)
10. **Como contribuir com uma fonte nova** (issue "Nova fonte"; `docs/ROADMAP.md`; CONTRIBUTING)

## Dados e fontes a citar (links verificados em 2026-11-26)

- https://dadosabertos.camara.leg.br/ (Câmara; caminhos de documentação citados na própria página)
- https://github.com/CamaraDosDeputados/dados-abertos (repositório oficial para dúvidas; apareceu em resultado de busca; abrir)
- https://www.camara.leg.br/transparencia/gastos-parlamentares
- https://dadosabertos.tse.jus.br/
- Portal da Transparência (CGU): link de download dos conjuntos CEIS, CNEP e emendas **a confirmar** (a leitura automática falhou com HTTP 405)

## Schema.org

- `TechArticle` com `proficiencyLevel: "Intermediate"`, `dependencies` (Python, Node) e `inLanguage: pt-BR`.
- `BreadcrumbList`.
- `WebAPI` (schema.org) para descrever a API: `documentation` (URL do `/docs`), `provider`. Usar só se a documentação estiver publicada e estável.
- Não usar `Dataset` para os dados reais (o projeto não os redistribui; `DATA_LICENSES.md`). Se um dia houver exportação da base fictícia ou pseudonimizada, ela pode ganhar `Dataset` com `license` e `isBasedOn` apontando as fontes oficiais.

## O que NÃO afirmar

- Que a API serve "todos os dados públicos de deputados" ou "dados em tempo real".
- Que os dados podem ser usados para qualquer fim: lembrar OpenSanctions (não comercial) e que a licença de cada fonte vale.
- Que o uso é "livre de LGPD" por ser dado público.
- Limites de uso, SLA ou disponibilidade que ninguém definiu.
- Que a conferência de dados (`make verifica`) prova que o dado oficial está certo: prova que o sistema o reproduz.

## Aviso de não acusação

Linha curta no topo: "Os achados da API são pistas rastreáveis, não conclusões sobre a conduta de ninguém."

## Links internos

`/metodo`, `/regras`, `/fontes`, `/glossario/pseudonimizacao`, `/glossario/fator-de-certeza`, `/estudantes`, `/faq`.
