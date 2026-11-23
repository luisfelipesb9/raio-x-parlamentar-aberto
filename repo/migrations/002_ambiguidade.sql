-- Ambiguidade de resolução de entidades: origem que casou com >1 destino não vira entity_link.
-- (Índice em entity_link.destino foi medido e descartado: o planner do DuckDB usa Seq Scan,
--  0,7 ms em 200 mil links, e o índice só encareceria a escrita.)
CREATE TABLE IF NOT EXISTS entity_ambiguity (
  origem TEXT PRIMARY KEY, candidatos JSON, motivo TEXT
);
