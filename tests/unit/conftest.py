import os

import pytest

from contracts import Fact

# Sal de TESTE (não é segredo): o sistema não tem sal padrão e `api.main` cria o app na importação,
# então a variável precisa existir antes da coleta dos testes. Teste que exercita a falta do sal
# a remove (monkeypatch.delenv).
os.environ["RAIO_X_ID_SALT"] = "sal-somente-para-testes"


@pytest.fixture(autouse=True)
def _raw_isolado(monkeypatch):
    """`$RAIO_X_RAW` vale por cima de `sources.base.RAW_DIR`: sem isto, quem exporta a variável
    para a pasta real de brutos faria os testes de coleta gravarem lá. Teste que precisa dela a
    define de novo (monkeypatch.setenv)."""
    monkeypatch.delenv("RAIO_X_RAW", raising=False)


def F(tipo, chave, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


@pytest.fixture
def fatos_votacao():
    fs = [F("deputado", d, nome=f"Dep {d}") for d in ("1", "2")]
    for i in range(12):
        fs.append(F("votacao", f"v{i}", nominal=True, orientacao_governo="Sim"))
        fs.append(F("voto", f"v{i}:1", votacao_id=f"v{i}", deputado_id="1", voto="Sim"))
        fs.append(F("voto", f"v{i}:2", votacao_id=f"v{i}", deputado_id="2",
                    voto="Não" if i % 2 else "Sim"))
    # votação simbólica com um "voto" que NÃO pode ser usado
    fs.append(F("votacao", "s1", nominal=False, orientacao_governo="Sim"))
    fs.append(F("voto", "s1:2", votacao_id="s1", deputado_id="2", voto="Sim"))
    return fs


@pytest.fixture
def fatos_ceap():
    fs = []
    for d in range(1, 8):
        fs.append(F("despesa_ceap", f"n{d}", deputado_id=str(d), cnpj=f"0000000000000{d}",
                    valor=1000 + d * 10, categoria="combustivel", data="2025-02-10"))
    fs.append(F("despesa_ceap", "n99", deputado_id="7", cnpj="00000000000007",
                valor=50000, categoria="combustivel", data="2025-02-11"))
    fs.append(F("sancao", "ceis1", cnpj="00000000000003", cadastro="CEIS",
                inicio="2025-01-01", fim=None))
    fs.append(F("sancao", "ceis2", cnpj="00000000000004", cadastro="CEIS",
                inicio="2024-01-01", fim="2024-12-31"))  # expirada: não dispara
    return fs
