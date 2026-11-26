"""scripts/checa_pii.py: CPF íntegro fora da allowlist e segredos óbvios nos arquivos versionados.

Os CPFs de teste são calculados aqui (nunca escritos por extenso): o próprio repositório é varrido
pelo script e um CPF válido literal neste arquivo reprovaria o CI.
"""
import subprocess
from pathlib import Path

import pytest

from scripts.checa_pii import Achado, achados_em_texto, checar, main


def cpf(base9: str) -> str:
    """CPF com dígitos verificadores corretos a partir dos 9 primeiros dígitos."""
    d = [int(c) for c in base9]
    for n in (9, 10):
        soma = sum(v * p for v, p in zip(d, range(n + 1, 1, -1), strict=True))
        d.append((soma * 10 % 11) % 10)
    return "".join(map(str, d))


CPF_A = cpf("529982247")   # sequência qualquer com dígitos válidos
CPF_B = cpf("111444777")


def _formatado(c: str) -> str:
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"


# ---------- CPF ----------

@pytest.mark.parametrize("texto", [f"cpf={CPF_A}", f"cpf: {_formatado(CPF_A)}", f'"{CPF_A}"'])
def test_cpf_valido_fora_da_allowlist_e_achado(texto):
    achados = achados_em_texto("x.py", texto, permitidos=frozenset())
    assert [a.tipo for a in achados] == ["cpf"]
    assert achados[0].linha == 1


def test_achado_nunca_carrega_o_valor_encontrado():
    [a] = achados_em_texto("x.py", f"a\nb {CPF_A}\n", permitidos=frozenset())
    assert (a.arquivo, a.linha) == ("x.py", 2)
    assert CPF_A not in repr(a) and CPF_A[:6] not in repr(a)


def test_cpf_com_digito_verificador_errado_nao_e_achado():
    errado = CPF_A[:10] + str((int(CPF_A[10]) + 1) % 10)
    assert achados_em_texto("x.py", errado, permitidos=frozenset()) == []


def test_sequencia_repetida_cnpj_e_numero_longo_nao_sao_cpf():
    texto = "11111111111 e 12.345.678/0001-95 e 123456789012345"
    assert achados_em_texto("x.py", texto, permitidos=frozenset()) == []


def test_cpf_mascarado_nao_e_achado():
    assert achados_em_texto("x.py", "***.529.982-** e ***529982**", permitidos=frozenset()) == []


def test_allowlist_aceita_cpf_com_ou_sem_pontuacao():
    permitidos = frozenset({CPF_A})
    assert achados_em_texto("x.py", f"{CPF_A} {_formatado(CPF_A)}", permitidos=permitidos) == []
    assert len(achados_em_texto("x.py", CPF_B, permitidos=permitidos)) == 1


def test_hash_hmac_com_onze_digitos_seguidos_nao_e_cpf():
    assert achados_em_texto("x.py", "hmac:" + CPF_A + "a" * 21, permitidos=frozenset()) == []


# ---------- segredos ----------

@pytest.mark.parametrize("texto,tipo", [
    ("chave = 'AKIA" + "ABCDEFGHIJKLMNOP" + "'", "segredo"),
    ("-----BEGIN RSA " + "PRIVATE KEY-----", "segredo"),
    ("ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8", "segredo"),
    ("xoxb-" + "123456789012-abcdefghij", "segredo"),
    ("API_TOKEN = '" + "abcd1234efgh5678ijkl9012" + "'", "segredo"),
    ('password: "' + "Sup3rS3cretaLonga99" + '"', "segredo"),
])
def test_segredo_obvio_e_achado(texto, tipo):
    achados = achados_em_texto("x.py", texto, permitidos=frozenset())
    assert [a.tipo for a in achados] == [tipo]


@pytest.mark.parametrize("texto", [
    "export RAIO_X_ID_SALT=<segredo>",
    "token = os.environ['X']",
    "password = ''",
    "senha: curta",
    "RAIO_X_ID_SALT=<segredo> make sample-publico",
])
def test_referencia_a_segredo_sem_valor_nao_e_achado(texto):
    assert achados_em_texto("x.py", texto, permitidos=frozenset()) == []


# ---------- arquivos ----------

def _repo(tmp_path: Path, arquivos: dict[str, str | bytes]) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for nome, conteudo in arquivos.items():
        alvo = tmp_path / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(conteudo, bytes):
            alvo.write_bytes(conteudo)
        else:
            alvo.write_text(conteudo, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def test_varre_so_arquivos_versionados(tmp_path):
    raiz = _repo(tmp_path, {"a.txt": "nada aqui"})
    (raiz / "solto.txt").write_text(f"cpf {CPF_A}", encoding="utf-8")  # não adicionado ao git
    assert checar(raiz, permitidos=frozenset()) == []


def test_acha_cpf_em_arquivo_versionado_e_informa_arquivo_e_linha(tmp_path):
    raiz = _repo(tmp_path, {"docs/x.md": f"linha 1\ncpf {CPF_A}\n"})
    assert checar(raiz, permitidos=frozenset()) == [Achado("docs/x.md", 2, "cpf")]


def test_pula_binarios_e_lockfiles(tmp_path):
    raiz = _repo(tmp_path, {
        "img.bin": b"\x00\x01" + CPF_A.encode(),
        "uv.lock": f"x {CPF_A}",
        "web/pnpm-lock.yaml": f"x {CPF_A}",
    })
    assert checar(raiz, permitidos=frozenset()) == []


def test_env_versionado_e_achado_mas_env_example_nao(tmp_path):
    raiz = _repo(tmp_path, {".env": "A=1", "web/.env.local": "B=2", ".env.example": "A="})
    assert sorted((a.arquivo, a.tipo) for a in checar(raiz, permitidos=frozenset())) == [
        (".env", "env"), ("web/.env.local", "env")]


def test_main_sai_1_com_achado_e_0_sem(tmp_path, capsys):
    (tmp_path / "limpo").mkdir()
    (tmp_path / "sujo").mkdir()
    limpo = _repo(tmp_path / "limpo", {"a.txt": "ok"})
    sujo = _repo(tmp_path / "sujo", {"a.txt": f"cpf {CPF_A}"})
    assert main(["--raiz", str(limpo)]) == 0
    assert main(["--raiz", str(sujo)]) == 1
    saida = capsys.readouterr().out
    assert "a.txt:1" in saida and CPF_A not in saida


# ---------- o repositório real ----------

def test_o_repositorio_passa_na_checagem():
    raiz = Path(__file__).resolve().parents[2]
    assert checar(raiz) == []
