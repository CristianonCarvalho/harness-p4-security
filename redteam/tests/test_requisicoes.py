import json

import pytest

from redteam.http.requisicoes import carregar_ataque_http, validar_criterio, validar_requisicoes

REQ = {"nome": "sem_autenticacao", "metodo": "POST", "caminho": "/mcp", "autenticacao": "ausente",
       "cabecalhos": {}, "corpo": {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
       "alvos": ["replica"]}


def test_requisicao_valida_passa():
    assert validar_requisicoes({"requisicoes": [REQ]}) == [REQ]


@pytest.mark.parametrize("alteracao", [
    {"metodo": "PUT"},
    {"caminho": "mcp"},
    {"autenticacao": "talvez"},
    {"cabecalhos": {"Authorization": "Bearer x"}},
    {"cabecalhos": {"authorization": "Bearer x"}},
    {"alvos": ["lua"]},
    {"alvos": []},
    {"nome": ""},
])
def test_requisicao_invalida_e_recusada(alteracao):
    with pytest.raises(ValueError):
        validar_requisicoes({"requisicoes": [{**REQ, **alteracao}]})


def test_lista_de_requisicoes_vazia_e_recusada():
    with pytest.raises(ValueError):
        validar_requisicoes({"requisicoes": []})


def test_criterio_aceita_so_as_chaves_conhecidas():
    assert validar_criterio({"esperado": {"status": [401]}}) == {"status": [401]}
    with pytest.raises(ValueError):
        validar_criterio({"esperado": {"magia": 1}})
    with pytest.raises(ValueError):
        validar_criterio({"esperado": {}})


def test_carrega_ataque_http_completo(tmp_path):
    ataque = {"id": "H1", "superficie": "http", "nome": "exemplo", "nucleo": True,
              "rotulos": {"classe": "autenticação"},
              "previsao": {"resultado_esperado": "defendido", "confianca": 80, "motivo": "teste"},
              "entrada": {"requisicoes": [REQ]},
              "criterio": {"esperado": {"status": [401]}}}
    caminho = tmp_path / "H1.json"
    caminho.write_text(json.dumps(ataque), encoding="utf-8")
    attack, reqs, esperado = carregar_ataque_http(caminho)
    assert attack.id == "H1" and reqs == [REQ] and esperado == {"status": [401]}


def test_corpo_repetido_e_aceito_ate_o_limite():
    req = {**REQ, "corpo": {"texto_repetido": {"caractere": "a", "vezes": 70000}}}
    assert validar_requisicoes({"requisicoes": [req]}) == [req]


@pytest.mark.parametrize("corpo", [
    {"texto_repetido": {"caractere": "ab", "vezes": 10}},
    {"texto_repetido": {"caractere": "a", "vezes": 0}},
    {"texto_repetido": {"caractere": "a", "vezes": 300000}},
])
def test_corpo_repetido_fora_do_limite_e_recusado(corpo):
    with pytest.raises(ValueError):
        validar_requisicoes({"requisicoes": [{**REQ, "corpo": corpo}]})
