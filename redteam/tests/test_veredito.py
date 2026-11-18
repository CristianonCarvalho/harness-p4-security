import json

from redteam.http.veredito import Resposta, julgar

ESPERADO_401 = {"status": [401], "erro_mcp": "nao_autorizado", "sem_stacktrace": True}
CORPO_401 = json.dumps({"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32001, "message": "nao_autorizado"}})


def test_defendido_quando_todas_as_expectativas_batem():
    assert julgar(ESPERADO_401, Resposta(401, CORPO_401)) == "defendido"


def test_furou_quando_bloqueio_esperado_recebe_sucesso():
    assert julgar({"status": [401]}, Resposta(200, "{}")) == "furou"


def test_inesperado_para_erro_de_servidor():
    assert julgar({"status": [401]}, Resposta(500, "")) == "inesperado"


def test_inesperado_quando_a_mensagem_do_erro_nao_bate():
    corpo = json.dumps({"error": {"message": "outra coisa"}})
    assert julgar(ESPERADO_401, Resposta(401, corpo)) == "inesperado"


def test_traceback_no_corpo_reprova_mesmo_com_status_certo():
    assert julgar({"status": [400], "sem_stacktrace": True},
                  Resposta(400, "Traceback (most recent call last)")) == "inesperado"


def test_corpo_que_nao_e_json_nao_bate_com_erro_mcp():
    assert julgar(ESPERADO_401, Resposta(401, "texto puro")) == "inesperado"
