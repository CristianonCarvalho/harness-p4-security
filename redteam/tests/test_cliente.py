import httpx

from redteam.http.cliente import TOKEN_ERRADO, enviar, montar_cabecalhos, montar_corpo, redigir

TOKEN = "t" * 40
REQ = {"nome": "x", "metodo": "POST", "caminho": "/mcp", "autenticacao": "correta",
       "cabecalhos": {}, "corpo": {"a": 1}, "alvos": ["replica"]}


def test_autenticacao_correta_errada_e_ausente():
    assert montar_cabecalhos("correta", TOKEN, {})["Authorization"] == f"Bearer {TOKEN}"
    assert montar_cabecalhos("errada", TOKEN, {})["Authorization"] == f"Bearer {TOKEN_ERRADO}"
    assert "Authorization" not in montar_cabecalhos("ausente", TOKEN, {})


def test_token_errado_de_teste_tem_mais_de_32_caracteres_e_difere_do_real():
    assert len(TOKEN_ERRADO) >= 32 and TOKEN_ERRADO != TOKEN


def test_corpo_texto_vai_cru_e_objeto_vira_json():
    assert montar_corpo("abc") == b"abc"
    assert montar_corpo({"a": 1}) == b'{"a": 1}'
    assert montar_corpo(None) is None


def test_redigir_troca_o_token():
    assert redigir(f"x {TOKEN} y", TOKEN) == "x <TOKEN> y"


def test_enviar_devolve_resposta_sem_o_token_e_trunca_o_corpo():
    def responder(request):
        return httpx.Response(401, text=TOKEN + "a" * 10000)

    with httpx.Client(transport=httpx.MockTransport(responder)) as cliente:
        r = enviar("http://teste.invalid", TOKEN, REQ, cliente=cliente)
    assert r.status == 401
    assert TOKEN not in r.corpo and len(r.corpo) <= 4000
