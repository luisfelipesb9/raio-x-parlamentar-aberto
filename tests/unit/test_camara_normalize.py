from sources.camara.source import CamaraSource

RAW = {
    "deputados": [{"id": 1, "nome": "Fulana", "siglaPartido": "XX", "siglaUf": "MG",
                   "uri": "u"}],
    "votacoes": [
        {"id": "100-1", "uri": "v", "data": "2025-02-01", "descricao": "PL 1",
         "_votos": [{"tipoVoto": "Sim", "deputado_": {"id": 1}}],
         "_orientacoes": [{"siglaPartidoBloco": "Governo", "orientacaoVoto": "Sim"}]},
        {"id": "100-2", "uri": "v2", "_votos": [], "_orientacoes": []},
    ],
}


def test_normalize():
    facts = CamaraSource(client=object()).normalize(RAW)
    by = {(f.tipo, f.chave): f for f in facts}
    assert by[("votacao", "100-1")].atributos == {
        "data": "2025-02-01", "descricao": "PL 1", "nominal": True, "orientacao_governo": "Sim"}
    assert by[("votacao", "100-2")].atributos["nominal"] is False
    assert by[("voto", "100-1:1")].atributos["deputado_id"] == "1"
    assert all(f.fonte and f.id_oficial for f in facts)
