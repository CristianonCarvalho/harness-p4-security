import json

import httpx
import pytest

from redteam.esquema import Attack
from redteam.http.medicao import exigir_previsao, gravar, rodar_ataque

TOKEN = "u" * 40
REQ = {"nome": "r", "metodo": "POST", "caminho": "/mcp", "autenticacao": "ausente",
       "cabecalhos": {}, "corpo": {"a": 1}, "alvos": ["replica"]}
ESPERADO = {"status": [401]}


def _attack(motivo="previsão escrita"):
    return Attack(id="H1", superficie="http", nome="x", nucleo=True, rotulos={},
                  previsao={"resultado_esperado": "defendido", "confianca": 80, "motivo": motivo})


def test_previsao_vazia_recusa_a_medicao():
    with pytest.raises(ValueError):
        exigir_previsao(_attack(motivo=""))


def test_tres_repeticoes_com_veredito_por_repeticao():
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, text="{}")))
    registros = rodar_ataque(_attack(), [REQ], ESPERADO, "http://teste.invalid", TOKEN,
                             cliente=cliente, repeticoes=3)
    assert [r["repeticao"] for r in registros] == [1, 2, 3]
    assert all(r["veredito"] == "defendido" for r in registros)


def test_medicao_recusa_rodar_sem_previsao():
    cliente = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, text="{}")))
    with pytest.raises(ValueError):
        rodar_ataque(_attack(motivo=""), [REQ], ESPERADO, "http://teste.invalid", TOKEN, cliente=cliente)


def test_registro_gravado_nao_contem_o_token(tmp_path):
    destino = tmp_path / "medicao.json"
    registros = [{"ataque": "H1", "requisicao": "r", "repeticao": 1, "status": 401,
                  "veredito": "defendido", "trecho": f"ecoou {TOKEN}"}]
    gravar(registros, destino, TOKEN)
    texto = destino.read_text(encoding="utf-8")
    assert TOKEN not in texto and "<TOKEN>" in texto
    assert json.loads(texto)[0]["status"] == 401
