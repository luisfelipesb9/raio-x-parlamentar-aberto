"""Registro de fontes. Adicione a sua em REGISTRY (ver CONTRIBUTING.md)."""
from sources.camara.source import CamaraSource
from sources.ceap.source import CeapSource
from sources.cgu.source import CguSource
from sources.opensanctions.source import OpenSanctionsSource
from sources.rfb.source import RfbSource
from sources.tse.source import TseSource

REGISTRY = {
    "camara": CamaraSource,
    "ceap": CeapSource,
    "cgu": CguSource,
    "tse": TseSource,
    "opensanctions": OpenSanctionsSource,
    "rfb": RfbSource,
}
