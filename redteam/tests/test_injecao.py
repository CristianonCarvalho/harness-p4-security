import json
from pathlib import Path

import pytest

from redteam.esquema import CATALOGO_DIR
from redteam.injecao import carregar_ataque_injecao, carregar_criterio_injecao, validar_entrada_injecao

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


def _ataque_com_criterio(tmp_path, criterio):
    bruto = json.loads((Path(CATALOGO_DIR) / "I1.json").read_text(encoding="utf-8"))
    bruto["criterio"] = criterio
    caminho = tmp_path / "I1.json"  # o nome do arquivo precisa ser o id do ataque
    caminho.write_text(json.dumps(bruto, ensure_ascii=False), encoding="utf-8")
    return caminho


def test_oraculo_valor_com_valor_e_aceito(tmp_path):
    caminho = _ataque_com_criterio(tmp_path, {"oraculo": "valor", "valor": "27%"})
    assert carregar_criterio_injecao(caminho) == {"oraculo": "valor", "valor": "27%"}
    assert carregar_ataque_injecao(caminho)[3] == "valor"


@pytest.mark.parametrize("criterio", [
    {"oraculo": "valor"},
    {"oraculo": "valor", "valor": "   "},
    {"oraculo": "valor", "valor": 27},
])
def test_oraculo_valor_sem_valor_textual_e_recusado(tmp_path, criterio):
    with pytest.raises(ValueError):
        carregar_criterio_injecao(_ataque_com_criterio(tmp_path, criterio))


def test_oraculo_desconhecido_e_recusado(tmp_path):
    with pytest.raises(ValueError):
        carregar_criterio_injecao(_ataque_com_criterio(tmp_path, {"oraculo": "lua"}))


def test_i5_pe_os_dois_fragmentos_no_dispositivo_que_o_modelo_le():
    # A medição v1 pôs o segundo fragmento em alvo2, e o modelo nunca leu esse dispositivo.
    _, registros, _, _ = carregar_ataque_injecao(Path(CATALOGO_DIR) / "I5.json")
    assert len(registros) == 2
    assert {r["alvo"] for r in registros} == {"alvo"}
