import json

import pytest

from redteam.esquema import load_attack, load_catalog

BASE = {
    "id": "H1", "superficie": "http", "nome": "exemplo", "nucleo": True,
    "rotulos": {"classe": "autenticação"},
    "previsao": {"resultado_esperado": "defendido", "confianca": 60, "motivo": "teste"},
}


def _grava(pasta, d, nome=None):
    caminho = pasta / f"{nome or d['id']}.json"
    caminho.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return caminho


def test_carrega_ataque_valido(tmp_path):
    a = load_attack(_grava(tmp_path, BASE))
    assert (a.id, a.superficie, a.nucleo) == ("H1", "http", True)


def test_campo_obrigatorio_ausente(tmp_path):
    d = {k: v for k, v in BASE.items() if k != "previsao"}
    with pytest.raises(ValueError):
        load_attack(_grava(tmp_path, d))


@pytest.mark.parametrize("novo_id", ["X1", "H0", "H100", "h1"])
def test_id_fora_do_formato_e_recusado(tmp_path, novo_id):
    with pytest.raises(ValueError):
        load_attack(_grava(tmp_path, {**BASE, "id": novo_id}, nome=novo_id))


def test_prefixo_tem_de_combinar_com_a_superficie(tmp_path):
    with pytest.raises(ValueError):
        load_attack(_grava(tmp_path, {**BASE, "id": "I1"}))


def test_nome_do_arquivo_tem_de_ser_o_id(tmp_path):
    with pytest.raises(ValueError):
        load_attack(_grava(tmp_path, BASE, nome="H2"))


def test_nucleo_precisa_ser_booleano(tmp_path):
    with pytest.raises(ValueError):
        load_attack(_grava(tmp_path, {**BASE, "nucleo": "sim"}))


def test_catalogo_ordena_injecao_antes_de_http(tmp_path):
    _grava(tmp_path, BASE)
    _grava(tmp_path, {**BASE, "id": "I9", "superficie": "injecao"})
    assert [a.id for a in load_catalog(tmp_path)] == ["I9", "H1"]
