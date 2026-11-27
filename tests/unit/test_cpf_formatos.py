"""CPF em texto livre: o regex pega as grafias comuns (hífen/barra/espaço/NBSP/ponto+espaço) e
o CPF numérico que perdeu o zero à esquerda (só em chaves `cpf*`), sem falso positivo em
valores monetários, datas, CNPJ e ids.

Os CPFs de teste são calculados aqui (nunca escritos por extenso): o próprio repositório é varrido
por `scripts/checa_pii.py` e um CPF válido literal neste arquivo reprovaria o CI.
"""
import pytest

from contracts import Fact
from ingest.pseudonimizar import dv_ok, hash_cpf, pseudonimizar_fatos
from scripts.checa_pii import achados_em_texto

SAL = "sal-de-teste"
NBSP = " "


def cpf(base9: str) -> str:
    d = [int(c) for c in base9]
    for n in (9, 10):
        soma = sum(v * p for v, p in zip(d, range(n + 1, 1, -1), strict=True))
        d.append((soma * 10 % 11) % 10)
    return "".join(map(str, d))


CPF = cpf("529982247")
CPF_ZERO = cpf("012345678")  # começa com zero: some o zero quando guardado como número
assert dv_ok(CPF) and dv_ok(CPF_ZERO) and CPF_ZERO.startswith("0")


def _variantes(d: str) -> list[str]:
    return [
        d,
        f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}",
        f"{d[:9]}-{d[9:]}",
        f"{d[:3]} {d[3:6]} {d[6:9]} {d[9:]}",
        f"{d[:3]}.{d[3:6]}.{d[6:9]}/{d[9:]}",
        f"{d[:3]}{NBSP}{d[3:6]}{NBSP}{d[6:9]}{NBSP}{d[9:]}",
        f"{d[:3]}.{NBSP}{d[3:6]}.{NBSP}{d[6:9]}-{d[9:]}",
        f"{d[:3]}. {d[3:6]}. {d[6:9]}-{d[9:]}",
        f"{d[:3]}.{d[3:6]}.{d[6:9]}.{d[9:]}",
    ]


NEGATIVOS = [
    "R$ 1.234.567,89",
    "valor 12.345.678,90 pagos",
    "2025-01-15 e 15/01/2025 10:30:45",
    "CNPJ 12.345.678/0001-95",
    "CNPJ 12345678000195",
    "id 123456789012",
    "protocolo 20250115093045",
    "52998224700",                       # 11 dígitos com DV errado
    "529 982 247 00",                    # separado, DV errado
    "11111111111",                       # sequência repetida
    "529 982 247",                       # só 9 dígitos
    "***.982.247-**",                    # mascarado pela fonte
    "100 200 300 400",                   # números soltos
]


def _fato(tipo="despesa_ceap", **atributos):
    return Fact(tipo=tipo, chave="k1", atributos=atributos, fonte="teste", id_oficial="k1",
                url="https://exemplo/k1")


@pytest.mark.parametrize("variante", _variantes(CPF))
def test_pseudonimizacao_pega_cada_grafia(variante):
    [f] = pseudonimizar_fatos([_fato(fornecedor=f"FULANO DE TAL {variante} ME")], SAL)
    texto = f.atributos["fornecedor"]
    assert texto == f"FULANO DE TAL {hash_cpf(CPF, SAL)} ME"


@pytest.mark.parametrize("variante", _variantes(CPF))
def test_checa_pii_pega_cada_grafia(variante):
    achados = achados_em_texto("x.py", f"contato {variante} fim", permitidos=frozenset())
    assert [a.tipo for a in achados] == ["cpf"]


@pytest.mark.parametrize("texto", NEGATIVOS)
def test_sem_falso_positivo_na_pseudonimizacao(texto):
    [f] = pseudonimizar_fatos([_fato(obs=texto)], SAL)
    assert f.atributos["obs"] == texto


@pytest.mark.parametrize("texto", NEGATIVOS)
def test_sem_falso_positivo_no_checa_pii(texto):
    assert achados_em_texto("x.py", texto, permitidos=frozenset()) == []


@pytest.mark.parametrize("valor", [int(CPF_ZERO), str(int(CPF_ZERO))])
def test_cpf_numerico_sem_zero_a_esquerda_em_chave_cpf(valor):
    assert len(str(int(CPF_ZERO))) == 10
    [f] = pseudonimizar_fatos([_fato(cpf_responsavel=valor)], SAL)
    assert f.atributos["cpf_responsavel"] == hash_cpf(CPF_ZERO, SAL)


def test_cpf_numerico_de_11_digitos_em_chave_cpf_tambem_e_trocado():
    [f] = pseudonimizar_fatos([_fato(cpf_x=int(CPF))], SAL)
    assert f.atributos["cpf_x"] == hash_cpf(CPF, SAL)


def test_dez_digitos_em_chave_que_nao_comeca_com_cpf_nao_muda():
    [f] = pseudonimizar_fatos([_fato(protocolo=int(CPF_ZERO), numero_cpf=int(CPF_ZERO))], SAL)
    assert f.atributos["protocolo"] == int(CPF_ZERO)
    assert f.atributos["numero_cpf"] == int(CPF_ZERO)


def test_dez_digitos_com_dv_invalido_em_chave_cpf_nao_muda():
    invalido = int(CPF_ZERO) + 1
    [f] = pseudonimizar_fatos([_fato(cpf_responsavel=invalido)], SAL)
    assert f.atributos["cpf_responsavel"] == invalido


def test_dez_digitos_em_chave_cpf_dentro_de_lista_e_dict():
    [f] = pseudonimizar_fatos(
        [_fato(extra={"cpf_a": int(CPF_ZERO)}, cpfs_lista=[int(CPF_ZERO)])], SAL)
    assert f.atributos["extra"]["cpf_a"] == hash_cpf(CPF_ZERO, SAL)
    assert f.atributos["cpfs_lista"] == [hash_cpf(CPF_ZERO, SAL)]


def test_deputado_continua_intacto():
    f = _fato(tipo="deputado", cpf=int(CPF_ZERO), nome=f"Fulano {CPF}")
    assert pseudonimizar_fatos([f], SAL) == [f]


@pytest.mark.parametrize("trecho", ['"cpf": {n}', "cpf_resp = '{n}'", "cpfSocio: {n}"])
def test_checa_pii_pega_cpf_de_10_digitos_em_chave_cpf(trecho):
    n = str(int(CPF_ZERO))
    achados = achados_em_texto("x.json", trecho.format(n=n), permitidos=frozenset())
    assert [a.tipo for a in achados] == ["cpf"]


def test_checa_pii_ignora_10_digitos_fora_de_chave_cpf():
    n = str(int(CPF_ZERO))
    assert achados_em_texto("x.json", f'"protocolo": {n}', permitidos=frozenset()) == []


# ---------- SQ_CANDIDATO (id público do TSE) que coincide com dígitos verificadores de CPF ----------

def _sq_com_dv_de_cpf() -> str:
    """11 dígitos que fecham como CPF por coincidência, como alguns SQ_CANDIDATO reais."""
    return cpf("600016034")


def test_sq_candidato_nao_e_trocado_por_hash_em_nenhum_tipo():
    sq = _sq_com_dv_de_cpf()
    assert dv_ok(sq)
    for tipo in ("votos_municipio", "doacao"):
        f = Fact(tipo=tipo, chave=f"2022:{sq}:1", fonte="t", id_oficial=f"2022:{sq}:1", url="https://x",
                 atributos={"ano": 2022, "sq_candidato": sq})
        assert pseudonimizar_fatos([f], SAL)[0].atributos["sq_candidato"] == sq


def test_campo_cpf_continua_sendo_trocado_no_mesmo_tipo():
    f = Fact(tipo="doacao", chave="d", fonte="t", id_oficial="d", url="https://x",
             atributos={"sq_candidato": _sq_com_dv_de_cpf(), "doador_cpf_cnpj": CPF})
    saida = pseudonimizar_fatos([f], SAL)[0].atributos
    assert saida["doador_cpf_cnpj"] == hash_cpf(CPF, SAL)


def test_varredura_ignora_sq_candidato_mas_acha_cpf_de_verdade():
    from ingest.varredura import cpfs_integros
    sq = _sq_com_dv_de_cpf()
    ok = [Fact(tipo="candidatura", chave=sq, fonte="t", id_oficial=sq, url="https://x", atributos={}),
          Fact(tipo="votos_municipio", chave=f"2022:{sq}:1", fonte="t", id_oficial=f"2022:{sq}:1",
               url="https://x", atributos={"sq_candidato": sq})]
    assert cpfs_integros(ok) == []
    mau = Fact(tipo="doacao", chave="d", fonte="t", id_oficial="d", url="https://x",
               atributos={"sq_candidato": sq, "doador_cpf_cnpj": CPF})
    assert [(a.tipo, a.campo) for a in cpfs_integros([mau])] == [("doacao", "doador_cpf_cnpj")]
    # chave de outro tipo com 11 dígitos que fecham como CPF continua sendo acusada
    outro = Fact(tipo="despesa_ceap", chave=sq, fonte="t", id_oficial="x", url="https://x", atributos={})
    assert [(a.tipo, a.campo) for a in cpfs_integros([outro])] == [("despesa_ceap", "chave")]


def test_varredura_de_derivados_ignora_so_ids_publicos_e_valor_cru():
    from ingest.varredura import tem_cpf_derivado
    sq, outro = _sq_com_dv_de_cpf(), CPF
    # ignorados: referência à candidatura, evidência de votos_municipio e valor em reais cru
    sqs = {sq}
    assert not tem_cpf_derivado(f"candidatura:{sq}", sqs)
    assert not tem_cpf_derivado('{"tipo":"votos_municipio","id_oficial":"' + sq + ':14931"}', sqs)
    assert not tem_cpf_derivado('{"valor_emendas":' + sq[:9] + "." + sq[9:] + "}")
    # continuam acusados: CPF solto, em outro tipo de evidência, formatado, ou colado a "candidatura:"
    assert tem_cpf_derivado(f"doador {outro}")
    assert tem_cpf_derivado('{"tipo":"doacao","id_oficial":"' + outro + ':1"}')
    assert tem_cpf_derivado(f"{outro[:3]}.{outro[3:6]}.{outro[6:9]}-{outro[9:]}")
    assert tem_cpf_derivado(f"{outro[:3]}.{outro[3:6]}.{outro[6:9]}.{outro[9:]}")
    assert tem_cpf_derivado(f"despesa:{outro}")
    # o mesmo número, se NÃO é o SQ de uma candidatura do banco, é acusado
    assert tem_cpf_derivado(f"candidatura:{sq}")
    assert tem_cpf_derivado(f"candidatura:{sq}", {outro})
