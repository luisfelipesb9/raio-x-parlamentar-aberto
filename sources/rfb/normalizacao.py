"""Reexporta as funções de CNPJ (a implementação vive em `contracts/cnpj.py`)."""
from contracts.cnpj import cnpj_valido, dv_cnpj, normalizar_cnpj

__all__ = ["cnpj_valido", "dv_cnpj", "normalizar_cnpj"]
