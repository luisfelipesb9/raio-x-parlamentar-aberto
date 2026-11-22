CREATE TABLE IF NOT EXISTS fact (
  tipo TEXT, chave TEXT, atributos JSON, fonte TEXT, id_oficial TEXT, url TEXT,
  coletado_em TIMESTAMPTZ, PRIMARY KEY (tipo, chave)
);
CREATE TABLE IF NOT EXISTS entity_link (
  origem TEXT, destino TEXT, metodo TEXT, cf DOUBLE, PRIMARY KEY (origem, destino)
);
CREATE TABLE IF NOT EXISTS finding (
  id TEXT PRIMARY KEY, deputado_id TEXT, regra TEXT, cf DOUBLE,
  payload JSON, explanation JSON
);
