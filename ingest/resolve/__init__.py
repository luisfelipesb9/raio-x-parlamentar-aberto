"""Resolução de entidades: funções puras (fatos → fatos enriquecidos + entity_link)."""
from ingest.resolve.candidatura import resolver_candidaturas
from ingest.resolve.cnpj import resolver_cnpj
from ingest.resolve.comum import Resolucao, normaliza_nome
from ingest.resolve.emenda import resolver_emendas
from ingest.resolve.pep import resolver_peps

__all__ = ["Resolucao", "normaliza_nome", "resolver_candidaturas", "resolver_cnpj",
           "resolver_emendas", "resolver_peps"]
