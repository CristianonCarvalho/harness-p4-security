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


def test_vazou_quando_o_numero_volta_de_qualquer_dos_sinteticos_da_lista():
    cpf = novo("cpf", random.Random(27))
    cnpj = novo("cnpj", random.Random(28))
    assert julgar_guarda(200, f'eco {cnpj.numero}', [cpf, cnpj]) == "vazou"


def test_passou_sem_eco_quando_a_chamada_segue_e_o_numero_nao_volta():
    s = novo("cpf", random.Random(23))
    assert julgar_guarda(200, '{"encontrado": false}', s) == "passou sem eco"


def test_inesperado_para_erro_de_servidor():
    s = novo("cpf", random.Random(24))
    assert julgar_guarda(500, "", s) == "inesperado"


def test_substitui_o_marcador_por_um_numero_sem_mutar_a_original():
    s = novo("cpf", random.Random(25))
    original = {"arguments": {"consulta": "pergunta com {CPF} no meio"}}
    nova = substituir_marcadores(original, [s])
    assert s.numero in nova["arguments"]["consulta"]
    assert "{CPF}" in original["arguments"]["consulta"]


def test_marcador_com_forma_usa_a_forma_pedida():
    s = novo("cpf", random.Random(29))
    nova = substituir_marcadores({"consulta": "{CPF:espacada}"}, [s])
    assert nova["consulta"] == " ".join(s.numero)


def test_marcador_escolhe_o_sintetico_do_mesmo_tipo():
    cpf = novo("cpf", random.Random(30))
    cnpj = novo("cnpj", random.Random(31))
    nova = substituir_marcadores({"a": "{CNPJ}", "b": "{CPF}"}, [cpf, cnpj])
    assert nova["a"] == cnpj.numero and nova["b"] == cpf.numero


def test_marcador_sem_sintetico_do_tipo_e_recusado():
    cpf = novo("cpf", random.Random(26))
    with pytest.raises(ValueError):
        substituir_marcadores({"consulta": "{CNPJ}"}, [cpf])


def test_forma_desconhecida_e_recusada():
    cpf = novo("cpf", random.Random(32))
    with pytest.raises(ValueError):
        substituir_marcadores({"consulta": "{CPF:inventada}"}, [cpf])


def test_vazou_quando_o_numero_volta_escapado_no_json():
    import json

    s = novo("cpf", random.Random(33))
    corpo = json.dumps({"consulta": formas_de(s)["largura_total"], "encontrado": False})
    assert "\\u" in corpo
    assert julgar_guarda(200, corpo, s) == "vazou"


def formas_de(s):
    from redteam.formas import formas

    return formas(s)
