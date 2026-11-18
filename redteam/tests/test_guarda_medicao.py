import json
import random

import httpx
import pytest

from redteam.esquema import Attack
from redteam.guarda_medicao import ControleFalhou, controle_ok, rodar_ataque_guarda
from redteam.http.cliente import enviar

TOKEN = "g" * 40
NUMEROS_ENVIADOS = []


def _ataque():
    return Attack(id="H7", superficie="http", nome="x", nucleo=True, rotulos={},
                  previsao={"resultado_esperado": "vazou", "confianca": 70, "motivo": "teste"})


def _req():
    corpo = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "buscar_dispositivos",
                        "arguments": {"consulta": "contribuinte {CPF:espacada} aqui"}}}
    return {"nome": "espacado", "metodo": "POST", "caminho": "/mcp", "autenticacao": "correta",
            "cabecalhos": {}, "corpo": corpo, "alvos": ["replica"]}


def _eco(request):
    consulta = json.loads(request.content)["params"]["arguments"]["consulta"]
    NUMEROS_ENVIADOS.append(consulta)
    interno = json.dumps({"consulta": consulta, "encontrado": False})
    return httpx.Response(200, text=json.dumps({"jsonrpc": "2.0", "id": 1,
                                                "result": {"content": [{"type": "text", "text": interno}]}}))


def test_controle_ok_exige_resultado_e_ausencia_de_bloqueio():
    ok = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": [
        {"type": "text", "text": json.dumps({"encontrado": True})}]}})
    assert controle_ok(200, ok)
    assert not controle_ok(200, '{"erro": "dados_de_contribuinte"}')
    assert not controle_ok(500, ok)


def test_eco_com_forma_disfarcada_vira_vazou_e_registra_o_nome_da_forma():
    cliente = httpx.Client(transport=httpx.MockTransport(_eco))
    registros = rodar_ataque_guarda(_ataque(), [_req()], "http://teste.invalid", TOKEN, cliente=cliente)
    assert all(r["veredito"] == "vazou" for r in registros)
    assert all("cpf:espacada" in r["formas_achadas"] for r in registros)


def test_cada_repeticao_usa_um_numero_novo_e_nenhum_numero_vai_para_o_registro():
    NUMEROS_ENVIADOS.clear()
    cliente = httpx.Client(transport=httpx.MockTransport(_eco))
    registros = rodar_ataque_guarda(_ataque(), [_req()], "http://teste.invalid", TOKEN, cliente=cliente)
    fps = [r["fingerprints"]["cpf"] for r in registros]
    assert len(set(fps)) == 3
    texto = json.dumps(registros)
    for enviado in NUMEROS_ENVIADOS:
        digitos = "".join(c for c in enviado if c.isdigit())
        assert digitos not in texto
