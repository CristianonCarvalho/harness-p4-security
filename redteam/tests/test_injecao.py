from pathlib import Path

import pytest

from redteam.esquema import CATALOGO_DIR
from redteam.injecao import carregar_ataque_injecao, validar_entrada_injecao

REG = {"alvo": "alvo", "posicao": "fim", "payload": "nota com {CANARIO}"}
PERGUNTA = "Qual é o tratamento de IBS e CBS? Consulte o corpus antes de responder."


def test_entrada_valida_passa():
    entrada = {"registros": [REG], "pergunta": PERGUNTA}
    assert validar_entrada_injecao(entrada) == ([REG], PERGUNTA)


@pytest.mark.parametrize("alteracao", [
    {"alvo": "lua"},
    {"posicao": "meio"},
    {"payload": ""},
])
def test_registro_invalido_e_recusado(alteracao):
    with pytest.raises(ValueError):
        validar_entrada_injecao({"registros": [{**REG, **alteracao}], "pergunta": PERGUNTA})


def test_lista_com_mais_de_dois_registros_e_recusada():
    with pytest.raises(ValueError):
        validar_entrada_injecao({"registros": [REG, REG, REG], "pergunta": PERGUNTA})


def test_pergunta_com_marcador_de_cpf_e_recusada():
    with pytest.raises(ValueError):
        validar_entrada_injecao({"registros": [REG], "pergunta": "contribuinte {CPF}?"})


def test_catalogo_de_injecao_carrega_e_nao_tem_url_nem_cpf():
    for i in range(1, 8):
        attack, registros, pergunta, oraculo = carregar_ataque_injecao(Path(CATALOGO_DIR) / f"I{i}.json")
        assert attack.id == f"I{i}" and attack.superficie == "injecao"
        assert oraculo == "canario" and registros and pergunta
        texto = str([r["payload"] for r in registros])
        assert "http" not in texto.lower() and "www" not in texto.lower() and "{CPF" not in texto


def test_i5_pe_os_dois_fragmentos_no_dispositivo_que_o_modelo_le():
    # A medição v1 pôs o segundo fragmento em alvo2, e o modelo nunca leu esse dispositivo.
    _, registros, _, _ = carregar_ataque_injecao(Path(CATALOGO_DIR) / "I5.json")
    assert len(registros) == 2
    assert {r["alvo"] for r in registros} == {"alvo"}
