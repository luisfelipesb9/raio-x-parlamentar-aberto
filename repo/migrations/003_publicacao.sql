-- Tabelas materializadas pelo passo `publicar/` (ADR-011). Ficam vazias no banco de trabalho; a API só as usa
-- quando `publicacao_meta` traz a chave `gerado_em` (senão cai no caminho antigo, sobre os fatos completos).
-- Sem chave primária nem índice: o arquivo público é somente leitura e o índice dobrava o tamanho (medicoes.md).
-- graph_node: saída de graph.project (payload = tipo, rotulo, atributos); graph_edge: payload = peso, cf, evidencia_ids.
CREATE TABLE IF NOT EXISTS graph_node (id TEXT, payload JSON);
CREATE TABLE IF NOT EXISTS graph_edge (origem TEXT, destino TEXT, rel TEXT, payload JSON);
-- Resultado do forward.run por deputado e regra (Finding sem evidências), lido pelo encadeamento regressivo.
CREATE TABLE IF NOT EXISTS inferencia (deputado_id TEXT, regra TEXT, payload JSON);
-- Contagens do banco COMPLETO (por fonte e tipo), janela de votos, data, contrato e hash da origem.
CREATE TABLE IF NOT EXISTS publicacao_meta (chave TEXT, valor JSON);
