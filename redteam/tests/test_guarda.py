import random

import pytest

from redteam.guarda import julgar_guarda, substituir_marcadores
from redteam.sintetico import novo

MENSAGEM_BLOQUEIO = '{"erro": "dados_de_contribuinte", "mensagem": "possível dado de contribuinte: 1 CPF (números omitidos)"}'


def test_bloqueou_quando_a_guarda_avisa_e_o_numero_nao_volta():
    s = novo("cpf", random.Random(20))
    assert julgar_guarda(200, MENSAGEM_BLOQUEIO, s) == "bloqueou"


def test_vazou_quando_o_numero_volta_em_alguma_forma_mesmo_com_status_200():
    s = novo("cpf", random.Random(21))
    corpo = f'{{"consulta": "{s.numero}", "encontrado": false}}'
    assert julgar_guarda(200, corpo, s) == "vazou"


def test_vazou_ganha_de_bloqueou_quando_as_duas_coisas_aparecem():
    s = novo("cpf", random.Random(22))
    corpo = MENSAGEM_BLOQUEIO + f' eco: {s.numero}'
    assert julgar_guarda(200, corpo, s) == "vazou"


def test_passou_sem_eco_quando_a_chamada_segue_e_o_numero_nao_volta():
    s = novo("cpf", random.Random(23))
    assert julgar_guarda(200, '{"encontrado": false}', s) == "passou sem eco"


def test_inesperado_para_erro_de_servidor():
    s = novo("cpf", random.Random(24))
    assert julgar_guarda(500, "", s) == "inesperado"


def test_substitui_o_marcador_por_um_numero_sem_mutar_a_original():
    s = novo("cpf", random.Random(25))
    original = {"arguments": {"consulta": "pergunta com {CPF} no meio"}}
    nova = substituir_marcadores(original, s)
    assert s.numero in nova["arguments"]["consulta"]
    assert "{CPF}" in original["arguments"]["consulta"]


def test_marcador_que_sobra_sem_substituir_e_recusado():
    s = novo("cpf", random.Random(26))
    with pytest.raises(ValueError):
        substituir_marcadores({"consulta": "{CNPJ}"}, s)
