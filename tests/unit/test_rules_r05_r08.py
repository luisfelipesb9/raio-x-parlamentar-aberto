"""R05–R08: produção ponderada, circuito doador-sócio, concentração de emendas, guardrail."""
from contracts import Fact
from engine import forward
from engine.factbase import FactBase
from engine.rules import load_rules


def F(tipo, chave, /, **at):
    return Fact(tipo=tipo, chave=chave, atributos=at, fonte="teste", id_oficial=chave,
                url=f"https://exemplo/{tipo}/{chave}")


def run(fs):
    return forward.run(FactBase(fs), load_rules())


def achados(res, regra):
    return {f.deputado_id: f for f in res.findings if f.regra == regra}


def autorias(dep, papel, n, prefixo=None):
    pre = prefixo or f"{dep}{papel}"
    return [F("autoria", f"{pre}{i}:{dep}:{papel}", proposicao_id=f"{pre}{i}",
              deputado_id=dep, papel=papel) for i in range(n)]


# ------------------------------------------------------------------ R05
def test_r05_formula_iniciativa_autor_mais_quarto_de_coautor():
    # 24 autorias + 4 coautorias => iniciativa 25 => 32*(1-e^-1) = 20.2278 (literal conhecido)
    fs = [F("deputado", "1", nome="A", partido="X", uf="MG")]
    fs += autorias("1", "autor", 24) + autorias("1", "coautor", 4)
    f = achados(run(fs), "R05")["1"]
    assert f.valores["iniciativa"] == 25.0
    assert f.valores["pontos"] == 20.23
    assert f.categoria == "producao"
    assert "20.23" in f.conclusao and "40" in f.conclusao


def test_r05_so_coautoria_pesa_um_quarto():
    fs = [F("deputado", "1", nome="A", partido="X", uf="MG")] + autorias("1", "coautor", 100)
    assert achados(run(fs), "R05")["1"].valores["pontos"] == 20.23  # 100*0.25 = 25


def test_r05_score_satura_em_40():
    fs = [F("deputado", "1", nome="A", partido="X", uf="MG")]
    fs += autorias("1", "autor", 600) + autorias("1", "relator", 300)
    assert achados(run(fs), "R05")["1"].valores["pontos"] == 40.0


def test_r05_relatoria_isolada_usa_escala_10_57():
    # 1 autoria: 32*(1-e^(-1/25)) = 1.2548; 1 relatoria: 8*(1-e^(-1/10.57)) = 0.7222
    fs = [F("deputado", "1", nome="A", partido="X", uf="MG")]
    fs += autorias("1", "autor", 1) + autorias("1", "relator", 1)
    f = achados(run(fs), "R05")["1"]
    assert f.valores["pontos"] == 1.98


def test_r05_sem_dados_nao_inventa_valor():
    fs = [F("deputado", "1", nome="A", partido="X", uf="MG"),
          F("deputado", "2", nome="B", partido="X", uf="MG")] + autorias("2", "autor", 5)
    assert "1" not in achados(run(fs), "R05")


def test_r05_media_do_partido_so_como_contexto():
    fs = []
    for d, n in (("1", 25), ("2", 25), ("3", 2)):  # 20.23, 20.23 e 2.46 pontos
        fs.append(F("deputado", d, nome=d, partido="X", uf="MG"))
        fs += autorias(d, "autor", n)
    fs.append(F("deputado", "4", nome="4", partido="Y", uf="MG"))
    fs += autorias("4", "autor", 25)
    ach = achados(run(fs), "R05")
    assert ach["1"].valores["contexto_media_partido"] == 14.31  # (20.23+20.23+2.46)/3
    assert ach["4"].valores["contexto_media_partido"] is None  # partido com 1 colega: sem contexto
    assert "14.31" not in ach["1"].conclusao  # contexto nunca vira conclusão pessoal


# ------------------------------------------------------------------ R06
CNPJ = "11111111000191"


def circuito(socio_cpf="12345678901", socio_nome="JOSE DA SILVA JUNIOR", doador_cpf="12345678901",
             tipo_doador="PF", dep_na_candidatura="1", cnpj_socio=CNPJ, link_cf=None,
             visivel=None, socio_visivel=None):
    cand_at = {"ano": 2022, "cpf": "99999999999", "nome": "X", "cargo": "Deputado Federal",
               "uf": "MG", "partido": "X"}
    if link_cf is not None:
        cand_at["deputado_cf"] = link_cf
    if dep_na_candidatura:
        cand_at["deputado_id"] = dep_na_candidatura
    return [
        F("deputado", "1", nome="Dep", partido="X", uf="MG"),
        F("candidatura", "S1", **cand_at),
        F("doacao", "D1", sq_candidato="S1", doador_nome="José da Silva Júnior",
          doador_cpf_cnpj=doador_cpf, valor=5000.0, data="2022-08-01", tipo_doador=tipo_doador,
          **({} if visivel is None else {"doador_cpf_visivel": visivel})),
        F("despesa_ceap", "N1", deputado_id="1", cnpj=CNPJ, fornecedor="Gráfica Ltda",
          valor=30000.0, categoria="divulgacao", data="2023-03-01"),
        F("socio", f"{cnpj_socio}:{socio_nome}", cnpj=cnpj_socio, nome=socio_nome,
          cpf_cnpj=socio_cpf, qualificacao="Sócio-Administrador",
          **({} if socio_visivel is None else {"cpf_visivel": socio_visivel})),
    ]


def test_r06_cpf_integro_igual_da_cf_alto():
    f = achados(run(circuito()), "R06")["1"]
    assert f.cf == 0.85 and f.nivel.value == "alta"
    assert f.valores["confirmado_por_cpf"] is True
    assert f.categoria == "integridade"


def test_r06_cpf_mascarado_compativel_vira_indicio_com_cf_ate_0_4():
    # '***456789**' exibe os dígitos 4–9 do CPF 12345678901: compatível, mas não confirma
    res = run(circuito(socio_cpf="***456789**"))
    assert achados(res, "R06") == {}  # nunca vira finding "confirmado"
    f = achados(res, "R06b")["1"]
    assert f.cf <= 0.4 and f.cf == 0.34
    assert "sujeito a confirmação de identidade" in f.conclusao
    assert f.valores["confirmado_por_cpf"] is False


def test_r06_cpf_mascarado_incompativel_descarta_homonimia():
    res = run(circuito(socio_cpf="***999999**"))
    assert achados(res, "R06") == {} and achados(res, "R06b") == {}


def test_r06_cpf_integro_diferente_descarta_homonimia():
    res = run(circuito(socio_cpf="98765432100"))
    assert achados(res, "R06") == {} and achados(res, "R06b") == {}


def test_r06_exige_doador_pessoa_fisica():
    assert achados(run(circuito(tipo_doador="PJ")), "R06") == {}


def test_r06_candidatura_sem_deputado_resolvido_nao_dispara():
    assert achados(run(circuito(dep_na_candidatura=None)), "R06") == {}


def test_r06_socio_de_outra_empresa_nao_dispara():
    assert achados(run(circuito(cnpj_socio="22222222000100")), "R06") == {}


def test_r06_nome_normalizado_sem_acento_e_maiusculo():
    res = run(circuito(socio_nome="  jose   da silva junior "))
    assert "1" in achados(res, "R06")


# ------------------------------------------------------------------ R07
def eleicao(votos_destino, votos_resto, validos=1000, destino=("A", "B"), resto=("C", "D", "E"),
            cand_cf=None, emenda_cf=None):
    extra_c = {} if cand_cf is None else {"deputado_cf": cand_cf}
    extra_e = {} if emenda_cf is None else {"deputado_cf": emenda_cf}
    fs = [F("deputado", "1", nome="Dep", partido="X", uf="MG"),
          F("candidatura", "S1", ano=2022, cpf="1", nome="Dep", cargo="Deputado Federal",
            uf="MG", partido="X", deputado_id="1", **extra_c)]
    for m in destino:
        fs.append(F("votos_municipio", f"2022:S1:{m}", ano=2022, sq_candidato="S1",
                    municipio_ibge=m, uf="MG", votos=votos_destino, votos_validos_municipio=validos))
        fs.append(F("emenda", f"E{m}", deputado_id="1", ano=2023, valor_empenhado=100000.0,
                    valor_pago=100000.0, municipio_ibge=m, tipo="individual", **extra_e))
    for m in resto:
        fs.append(F("votos_municipio", f"2022:S1:{m}", ano=2022, sq_candidato="S1",
                    municipio_ibge=m, uf="MG", votos=votos_resto, votos_validos_municipio=validos))
    return fs


def test_r07_dispara_quando_voto_no_destino_e_3x_o_resto():
    # 30% nos municípios das emendas vs 1% no resto da UF => razão 30
    f = achados(run(eleicao(300, 10)), "R07")["1"]
    assert f.valores["pct_destino"] == 30.0 and f.valores["pct_resto"] == 1.0
    assert f.valores["razao"] == 30.0
    assert f.categoria == "emendas" and "30" in f.conclusao


def test_r07_nao_dispara_com_votacao_uniforme():
    assert achados(run(eleicao(100, 100)), "R07") == {}


def test_r07_limiar_exato_3x_dispara_e_abaixo_nao():
    assert "1" in achados(run(eleicao(300, 100)), "R07")      # razão 3.0
    assert achados(run(eleicao(290, 100)), "R07") == {}        # razão 2.9


def test_r07_resto_com_zero_votos_nao_divide_por_zero_nem_inventa():
    assert achados(run(eleicao(300, 0)), "R07") == {}


def test_r07_sem_emendas_ou_emenda_sem_deputado_nao_dispara():
    fs = [f for f in eleicao(300, 10) if f.tipo != "emenda"]
    fs.append(F("emenda", "X1", autor_nome="Dep", ano=2023, valor_empenhado=1.0,
                municipio_ibge="A"))
    assert achados(run(fs), "R07") == {}


def test_r07_emenda_pix_antes_de_2027_reduz_cf_e_avisa():
    base = achados(run(eleicao(300, 10)), "R07")["1"].cf
    fs = eleicao(300, 10)
    fs.append(F("emenda", "EP", deputado_id="1", ano=2024, valor_empenhado=50000.0,
                valor_pago=0.0, municipio_ibge="A", tipo="pix"))
    f = achados(run(fs), "R07")["1"]
    assert f.valores["n_emendas_pix_pre_2027"] == 1
    assert f.cf < base


# ------------------------------------------------------------------ R08
def processo(chave, transitado, dep="1"):
    return F("processo", chave, deputado_id=dep, tipo="penal", transitado_em_julgado=transitado)


def test_r08_guardrail_roda_antes_e_tem_prioridade_baixa():
    regras = load_rules()
    r08 = next(r for r in regras if r.id == "R08")
    assert r08.tipo == "guardrail" and r08.prioridade < 10


def test_r08_remove_processo_sem_transito_e_mantem_o_transitado():
    fb = FactBase([processo("p1", False), processo("p2", True), processo("p3", False, dep="2")])
    res = forward.run(fb, load_rules())
    assert "R08" in res.guardrail_log
    assert [p.chave for p in fb.of("processo")] == ["p2"]
    assert len(fb.excluidos["R08_presuncao_inocencia"]) == 2


def test_r08_processo_sem_transito_nao_chega_a_nenhum_predicado(monkeypatch):
    """Predicado-sonda (só no teste) conta os `processo` que uma regra enxergaria."""
    from engine.predicates import PREDICATES, Candidate
    from engine.rules import Rule

    def sonda(fb, params):
        return [Candidate("1", {"n_processos": len(fb.of("processo"))})]

    monkeypatch.setitem(PREDICATES, "sonda_processo", sonda)
    regra = Rule(id="RT", nome="sonda", predicado="sonda_processo", entao="{n_processos}")
    fs = [processo("p1", False), processo("p2", False), processo("p3", True)]
    r08 = next(r for r in load_rules() if r.id == "R08")

    sem_guardrail = forward.run(FactBase(fs), [regra])
    com_guardrail = forward.run(FactBase(fs), [r08, regra])
    assert sem_guardrail.findings[0].valores["n_processos"] == 3  # a sonda enxerga tudo...
    assert com_guardrail.findings[0].valores["n_processos"] == 1  # ...o R08 deixa só o transitado


def test_r08_registra_deputados_sem_dados_e_nenhuma_regra_inventa_valor():
    fs = [F("deputado", "1", nome="Sem dados", partido="X", uf="MG"),
          F("deputado", "2", nome="Com dados", partido="X", uf="MG")] + autorias("2", "autor", 5)
    res = run(fs)
    assert "1 deputado(s) sem nenhum dado" in res.guardrail_log["R08"]
    assert all(f.deputado_id != "1" for f in res.findings)


# ------------------------------------------------------------------ R06: separação e valores
def circuito_misto():
    """Dois sócios na mesma empresa: um com CPF íntegro, outro mascarado."""
    fs = circuito()
    fs.append(F("doacao", "D2", sq_candidato="S1", doador_nome="Maria Souza",
                doador_cpf_cnpj="55555555555", valor=700.0, data="2022-08-02", tipo_doador="PF"))
    fs.append(F("socio", f"{CNPJ}:MARIA SOUZA", cnpj=CNPJ, nome="MARIA SOUZA",
                cpf_cnpj="***555555**", qualificacao="Sócia"))
    return fs


def test_r06_confirmado_nao_empresta_cf_alto_ao_mascarado():
    res = run(circuito_misto())
    conf, ind = achados(res, "R06")["1"], achados(res, "R06b")["1"]
    assert conf.cf == 0.85 and conf.valores["n_circuitos"] == 1
    assert ind.cf <= 0.4 and ind.valores["n_circuitos"] == 1


def test_r06_nao_duplica_valor_ceap_nem_doacao():
    fs = circuito()
    fs.append(F("socio", f"{CNPJ}:JOSE DA SILVA JUNIOR 2", cnpj=CNPJ,
                nome="JOSE DA SILVA JUNIOR", cpf_cnpj="12345678901", qualificacao="Sócio"))
    fs.append(F("doacao", "D1b", sq_candidato="S1", doador_nome="José da Silva Júnior",
                doador_cpf_cnpj="12345678901", valor=1000.0, data="2022-09-01", tipo_doador="PF"))
    f = achados(run(fs), "R06")["1"]
    assert f.valores["valor_ceap"] == 30000.0           # uma vez por (deputado, cnpj)
    assert f.valores["valor_doado"] == 6000.0           # 5000 + 1000, cada doação uma vez
    ids = [(e.tipo, e.id_oficial) for e in f.evidencias]
    assert len(ids) == len(set(ids))


def test_r06_indicio_nao_expoe_nome_do_socio():
    f = achados(run(circuito(socio_cpf="***456789**")), "R06b")["1"]
    assert "socios" not in f.valores
    assert "SILVA" not in str(f.valores).upper() and "SILVA" not in f.conclusao.upper()
    assert all(e.tipo != "socio" for e in f.evidencias)  # id_oficial do sócio embute o nome


def test_r06_texto_nao_afirma_mascarado_quando_cpf_ausente():
    f = achados(run(circuito(socio_cpf=None)), "R06b")["1"]
    assert f.conclusao == (
        "Pagou R$ 30000.0 da cota parlamentar a empresa(s) cujo sócio tem o mesmo nome de uma "
        "pessoa que doou R$ 5000.0 à campanha do deputado: indício sujeito a confirmação de "
        "identidade, pois o CPF do sócio não pôde ser conferido (mascarado ou ausente) e o "
        "casamento foi feito só pelo nome.")


# ------------------------------------------------------------------ R03: B1 e I3
def sancao_pf():
    return F("sancao", "ceis-pf", cnpj=None, cadastro="CEIS", inicio="2025-01-01", fim=None)


def test_r03_despesa_sem_cnpj_nao_casa_com_sancao_sem_cnpj():
    fs = [sancao_pf(), F("despesa_ceap", "t1", deputado_id="1", cnpj=None, valor=300.0,
                         categoria="telefonia", data="2025-02-10")]
    assert achados(run(fs), "R03") == {}


def test_r03_estorno_zera_liquido_e_nao_dispara():
    cnpj = "00000000000003"
    fs = [F("sancao", "ceis1", cnpj=cnpj, cadastro="CEIS", inicio="2025-01-01", fim=None),
          F("despesa_ceap", "d1", deputado_id="1", cnpj=cnpj, valor=500.0, categoria="c",
            data="2025-02-10"),
          F("despesa_ceap", "d2", deputado_id="1", cnpj=cnpj, valor=-500.0, categoria="c",
            data="2025-02-11")]
    assert achados(run(fs), "R03") == {}


def test_r03_so_conta_valores_positivos_quando_liquido_positivo():
    cnpj = "00000000000003"
    fs = [F("sancao", "ceis1", cnpj=cnpj, cadastro="CEIS", inicio="2025-01-01", fim=None),
          F("despesa_ceap", "d1", deputado_id="1", cnpj=cnpj, valor=500.0, categoria="c",
            data="2025-02-10"),
          F("despesa_ceap", "d2", deputado_id="1", cnpj=cnpj, valor=-200.0, categoria="c",
            data="2025-02-11")]
    f = achados(run(fs), "R03")["1"]
    assert f.valores["n_despesas"] == 1 and f.valores["valor_total"] == 300.0


# ------------------------------------------------------------------ R07: nit
def test_r07_n_emendas_conta_emendas_distintas_nao_linhas():
    fs = eleicao(300, 10)
    fs.append(F("emenda", "EA", deputado_id="1", ano=2023, valor_empenhado=100000.0,
                valor_pago=0.0, municipio_ibge="A", tipo="individual"))  # mesma emenda EA, outra linha
    f = achados(run(fs), "R07")["1"]
    assert f.valores["n_emendas"] == 2 and f.valores["valor_emendas"] == 200000.0


# ------------------------------------------------------------------ I1: deputado_cf (resolução)
def test_r07_propaga_menor_deputado_cf_da_candidatura_e_da_emenda():
    assert achados(run(eleicao(300, 10)), "R07")["1"].cf == 0.42  # 0.6 × 0.7 (poucos municípios)
    f = achados(run(eleicao(300, 10, cand_cf=0.8, emenda_cf=0.7)), "R07")["1"]
    assert f.cf == 0.294  # 0.6 × min(0.8, 0.7) × 0.7


def test_r06_propaga_deputado_cf_da_candidatura():
    assert achados(run(circuito()), "R06")["1"].cf == 0.85
    assert achados(run(circuito(link_cf=0.8)), "R06")["1"].cf == 0.68        # 0.85 × 0.8
    assert achados(run(circuito(socio_cpf="***456789**", link_cf=0.7)), "R06b")["1"].cf == 0.238


def test_r05_objetivo_e_descritivo_nao_uma_conclusao_de_relevancia():
    r05 = next(r for r in load_rules() if r.id == "R05")
    assert r05.conclui == "pontuacao_producao_legislativa"


# ------------------------------------------------------------------ R06b com doador pseudonimizado
HASH = "sha256:9f2c0d7e5b1a"


def test_r06b_doador_pseudonimizado_com_visivel_compativel_e_indicio():
    for socio_cpf in ("***456789**", "12345678901"):  # mascarado e íntegro compatíveis
        res = run(circuito(socio_cpf=socio_cpf, doador_cpf=HASH, visivel="456789"))
        assert achados(res, "R06") == {}               # hash nunca confirma identidade
        assert achados(res, "R06b")["1"].cf == 0.34


def test_r06_doador_pseudonimizado_com_visivel_incompativel_descarta():
    for socio_cpf in ("***999999**", "12399999901"):
        res = run(circuito(socio_cpf=socio_cpf, doador_cpf=HASH, visivel="456789"))
        assert achados(res, "R06") == {} and achados(res, "R06b") == {}


def test_r06b_doador_pseudonimizado_sem_visivel_continua_indicio():
    res = run(circuito(socio_cpf="***456789**", doador_cpf=HASH))
    assert achados(res, "R06b")["1"].cf == 0.34


def test_r06_doador_integro_ignora_visivel_e_continua_confirmando():
    res = run(circuito(doador_cpf="12345678901", visivel="000000"))
    assert achados(res, "R06")["1"].cf == 0.85


# ------------------------------------------------------------------ base pseudonimizada (hmac)
def test_r06_hashes_iguais_confirmam_identidade():
    res = run(circuito(socio_cpf="hmac:aaa111", doador_cpf="hmac:aaa111"))
    assert achados(res, "R06")["1"].cf == 0.85 and achados(res, "R06b") == {}


def test_r06_hashes_diferentes_descartam_homonimo():
    res = run(circuito(socio_cpf="hmac:aaa111", doador_cpf="hmac:bbb222"))
    assert achados(res, "R06") == {} and achados(res, "R06b") == {}


def test_r06b_doador_hash_com_visivel_contra_socio_mascarado_usa_visiveis():
    ok = run(circuito(socio_cpf="***456789**", doador_cpf="hmac:aaa111", visivel="456789"))
    assert achados(ok, "R06") == {} and achados(ok, "R06b")["1"].cf == 0.34
    no = run(circuito(socio_cpf="***999999**", doador_cpf="hmac:aaa111", visivel="456789"))
    assert achados(no, "R06") == {} and achados(no, "R06b") == {}


def test_r06b_socio_hash_com_cpf_visivel_contra_doador_integro_usa_visiveis():
    ok = run(circuito(socio_cpf="hmac:sss333", socio_visivel="456789"))
    assert achados(ok, "R06") == {} and achados(ok, "R06b")["1"].cf == 0.34
    no = run(circuito(socio_cpf="hmac:sss333", socio_visivel="999999"))
    assert achados(no, "R06") == {} and achados(no, "R06b") == {}


def test_r06_hashes_diferentes_descartam_mesmo_com_visiveis_iguais():
    # hmac vem sempre de CPF íntegro: hashes diferentes = pessoas diferentes (visível é coincidência)
    res = run(circuito(socio_cpf="hmac:sss333", socio_visivel="456789",
                       doador_cpf="hmac:aaa111", visivel="456789"))
    assert achados(res, "R06") == {} and achados(res, "R06b") == {}


def test_r06_hashes_iguais_com_visiveis_confirmam():
    res = run(circuito(socio_cpf="hmac:aaa111", socio_visivel="456789",
                       doador_cpf="hmac:aaa111", visivel="456789"))
    assert achados(res, "R06")["1"].cf == 0.85


def test_r06b_hash_sem_visivel_contra_mascarado_e_indeterminado():
    res = run(circuito(socio_cpf="***456789**", doador_cpf="hmac:aaa111"))
    assert achados(res, "R06") == {} and achados(res, "R06b")["1"].cf == 0.34
