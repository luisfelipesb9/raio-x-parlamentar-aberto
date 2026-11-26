"""O sal dos ids de pessoa não tem valor padrão: sem RAIO_X_ID_SALT o sistema falha fechado."""
import pytest

from contracts import Fact
from graph import SalAusenteError, build_graph, project, sal_do_ambiente


def _fato(tipo, chave, **atributos):
    return Fact(tipo=tipo, chave=chave, atributos=atributos, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def _doacao():
    return [
        _fato("deputado", "1", nome="Dep Um", partido="ABC", uf="MG"),
        _fato("candidatura", "sq1", ano="2022", nome="Dep Um", uf="MG", partido="ABC",
              cargo="DEPUTADO FEDERAL", deputado_id="1"),
        _fato("doacao", "r1", sq_candidato="sq1", doador_nome="Maria",
              doador_cpf_cnpj="12345678901", valor=1.0, tipo_doador="PF"),
    ]


def test_sal_do_ambiente_devolve_o_valor_definido(monkeypatch):
    monkeypatch.setenv("RAIO_X_ID_SALT", "  sal-qualquer  ")
    assert sal_do_ambiente() == "sal-qualquer"


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_sem_sal_o_erro_diz_como_definir(monkeypatch, valor):
    if valor is None:
        monkeypatch.delenv("RAIO_X_ID_SALT", raising=False)
    else:
        monkeypatch.setenv("RAIO_X_ID_SALT", valor)
    with pytest.raises(SalAusenteError) as erro:
        sal_do_ambiente()
    msg = str(erro.value)
    assert "RAIO_X_ID_SALT" in msg
    assert "export" in msg
    assert "Vercel" in msg


def test_project_sem_sal_explicito_exige_a_variavel(monkeypatch):
    monkeypatch.delenv("RAIO_X_ID_SALT", raising=False)
    with pytest.raises(SalAusenteError):
        project(_doacao(), [])
    with pytest.raises(SalAusenteError):
        build_graph(_doacao(), [])


def test_project_com_sal_explicito_nao_consulta_o_ambiente(monkeypatch):
    monkeypatch.delenv("RAIO_X_ID_SALT", raising=False)
    nodes, _ = project(_doacao(), [], sal_id="sal-explicito")
    assert any(n.tipo == "pessoa" for n in nodes)


def test_api_nao_sobe_sem_sal(monkeypatch):
    pytest.importorskip("fastapi")
    from api.main import create_app
    monkeypatch.delenv("RAIO_X_ID_SALT", raising=False)
    with pytest.raises(SalAusenteError, match="RAIO_X_ID_SALT"):
        create_app()


@pytest.mark.parametrize("vazio", ["", "   "])
def test_sal_explicito_vazio_tambem_e_erro_mesmo_com_o_ambiente_definido(monkeypatch, vazio):
    monkeypatch.setenv("RAIO_X_ID_SALT", "sal-do-ambiente")
    with pytest.raises(SalAusenteError, match="RAIO_X_ID_SALT"):
        project(_doacao(), [], sal_id=vazio)
    with pytest.raises(SalAusenteError):
        build_graph(_doacao(), [], sal_id=vazio)


def _ids_de_pessoa(sal):
    nodes, _ = project(_doacao(), [], sal_id=sal)
    return sorted(n.id for n in nodes if n.tipo == "pessoa")


def test_sais_diferentes_dao_ids_diferentes_e_o_id_nao_traz_o_cpf():
    ids_a, ids_b = _ids_de_pessoa("sal-a"), _ids_de_pessoa("sal-b")
    assert len(ids_a) == 1 and len(ids_b) == 1
    assert ids_a != ids_b
    assert _ids_de_pessoa("sal-a") == ids_a  # determinístico para o mesmo sal
    for pid in ids_a + ids_b:
        assert "12345678901" not in pid
        assert pid.startswith("pessoa:cpf:")
