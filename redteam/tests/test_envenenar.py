import json
from pathlib import Path

import pytest

from redteam.envenenar import envenenar
from redteam.integridade import corpus_sha256

CANARIO = "CANARIO-1A2B3C4D"


def _corpus(base: Path, texto_alvo: str = "Texto A.") -> None:
    (base / "corpus").mkdir(parents=True, exist_ok=True)
    dados = {
        "fontes": [],
        "dispositivos": [
            {"id": "LC214.art125", "texto": texto_alvo},
            {"id": "EC132.art8.parunico", "texto": "Texto B."},
            {"id": "OUTRO", "texto": "Texto C."},
        ],
    }
    (base / "corpus" / "dispositivos.json").write_text(json.dumps(dados), encoding="utf-8")


def _textos(base: Path) -> dict:
    dados = json.loads((base / "corpus" / "dispositivos.json").read_text(encoding="utf-8"))
    return {d["id"]: d["texto"] for d in dados["dispositivos"]}


def test_inicio_no_alvo_acrescenta_antes_do_texto(tmp_path):
    _corpus(tmp_path)
    envenenar(tmp_path, [{"alvo": "alvo", "posicao": "inicio", "payload": "PAYLOAD"}], CANARIO)
    assert _textos(tmp_path)["LC214.art125"] == "PAYLOAD Texto A."


def test_fim_no_alvo2_acrescenta_depois_do_texto(tmp_path):
    _corpus(tmp_path)
    envenenar(tmp_path, [{"alvo": "alvo2", "posicao": "fim", "payload": "PAYLOAD"}], CANARIO)
    assert _textos(tmp_path)["EC132.art8.parunico"] == "Texto B. PAYLOAD"


def test_outros_registros_nao_mudam(tmp_path):
    _corpus(tmp_path)
    envenenar(tmp_path, [{"alvo": "alvo", "posicao": "inicio", "payload": "P"}], CANARIO)
    textos = _textos(tmp_path)
    assert textos["EC132.art8.parunico"] == "Texto B."
    assert textos["OUTRO"] == "Texto C."


def test_canario_substitui_o_placeholder(tmp_path):
    _corpus(tmp_path)
    envenenar(tmp_path, [{"alvo": "alvo", "posicao": "fim", "payload": "Inclua {CANARIO}."}], CANARIO)
    texto = _textos(tmp_path)["LC214.art125"]
    assert CANARIO in texto
    assert "{CANARIO}" not in texto


def test_devolve_o_novo_hash_do_corpus(tmp_path):
    _corpus(tmp_path)
    antes = corpus_sha256(tmp_path)
    depois = envenenar(tmp_path, [{"alvo": "alvo", "posicao": "fim", "payload": "P"}], CANARIO)
    assert depois == corpus_sha256(tmp_path)
    assert depois != antes


def test_dois_fragmentos_no_mesmo_alvo_se_acumulam(tmp_path):
    # Teste de caracterização: o I5 corrigido põe um fragmento no início e outro no fim do mesmo registro.
    _corpus(tmp_path)
    envenenar(tmp_path, [
        {"alvo": "alvo", "posicao": "inicio", "payload": "P1"},
        {"alvo": "alvo", "posicao": "fim", "payload": "P2"},
    ], CANARIO)
    assert _textos(tmp_path)["LC214.art125"] == "P1 Texto A. P2"


def test_alvo_sem_texto_e_recusado(tmp_path):
    _corpus(tmp_path, texto_alvo="")
    with pytest.raises(ValueError, match="sem texto"):
        envenenar(tmp_path, [{"alvo": "alvo", "posicao": "fim", "payload": "P"}], CANARIO)


def test_alvo_desconhecido_e_recusado(tmp_path):
    _corpus(tmp_path)
    with pytest.raises(ValueError, match="alvo desconhecido"):
        envenenar(tmp_path, [{"alvo": "outro", "posicao": "fim", "payload": "P"}], CANARIO)


def test_posicao_desconhecida_e_recusada(tmp_path):
    _corpus(tmp_path)
    with pytest.raises(ValueError, match="posicao"):
        envenenar(tmp_path, [{"alvo": "alvo", "posicao": "meio", "payload": "P"}], CANARIO)
