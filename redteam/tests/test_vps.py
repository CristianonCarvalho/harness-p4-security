import httpx
import pytest

from redteam.http.vps import assinatura, executar, listar

TOKEN = "v" * 40


def _req(nome, alvos=("vps",)):
    return {"ataque": "H1", "nome": nome, "metodo": "POST", "caminho": "/mcp",
            "autenticacao": "ausente", "cabecalhos": {}, "corpo": {"a": 1}, "alvos": list(alvos)}


def _lista(n):
    return [_req(f"r{i}") for i in range(n)]


def _cliente(status, texto="{}"):
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, text=texto)))


def test_listar_so_inclui_requisicoes_da_vps():
    catalogo = [("H1", [_req("para_vps"), _req("so_replica", alvos=("replica",))])]
    lista = listar(catalogo)
    assert [r["nome"] for r in lista] == ["para_vps"]


def test_mais_de_30_requisicoes_sao_recusadas():
    with pytest.raises(ValueError):
        executar(_lista(31), "https://teste.invalid", TOKEN, cliente=_cliente(401),
                 confirmacao=assinatura(_lista(31)), sleep=lambda s: None)


def test_assinatura_errada_nao_envia_nada():
    chamadas = []
    cliente = httpx.Client(transport=httpx.MockTransport(
        lambda r: chamadas.append(r) or httpx.Response(401)))
    with pytest.raises(ValueError):
        executar(_lista(2), "https://teste.invalid", TOKEN, cliente=cliente,
                 confirmacao="errada", sleep=lambda s: None)
    assert chamadas == []


def test_para_na_primeira_resposta_429():
    respostas = iter([401, 429, 401])
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(next(respostas))))
    resultados = executar(_lista(3), "https://teste.invalid", TOKEN, cliente=cliente,
                          confirmacao=assinatura(_lista(3)), sleep=lambda s: None)
    assert [r["status"] for r in resultados] == [401, 429]
    assert resultados[-1]["parada"] == "limite de taxa"


def test_respeita_o_intervalo_entre_requisicoes():
    pausas = []
    executar(_lista(3), "https://teste.invalid", TOKEN, cliente=_cliente(401),
             confirmacao=assinatura(_lista(3)), intervalo_s=0.5, sleep=pausas.append)
    assert pausas == [0.5, 0.5]


def test_resultado_nao_contem_o_token_mesmo_se_o_servidor_ecoar_o_token():
    resultados = executar(_lista(1), "https://teste.invalid", TOKEN,
                          cliente=_cliente(401, texto=f"ecoou {TOKEN}"),
                          confirmacao=assinatura(_lista(1)), sleep=lambda s: None)
    assert TOKEN not in str(resultados)
