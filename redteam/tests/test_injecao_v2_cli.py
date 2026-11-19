import json
import random
from pathlib import Path

import pytest

from redteam.injecao_v2 import ATAQUES_V2, MODELOS_V2, main, planejar_piloto, preparar_calibracao


def _linha(i, ataque, modelo, marcador, resposta):
    return {
        "chave": f"{ataque}|{modelo}|{i}", "ataque": ataque, "modelo": modelo, "repeticao": i,
        "status": "rodada", "erro": None, "canario": "CANARIO-1A2B3C4D", "marcador_automatico": marcador,
        "resposta_completa": resposta, "resposta_trecho": resposta[:500], "julgamento": None,
        "custo": 0.01,
    }


def _jsonl_com_linhas(caminho):
    linhas = []
    for i in range(1, 4):
        linhas.append(_linha(i, "I8", "claude-haiku-5-5", "canario_presente", f"Substituo: CANARIO-1A2B3C4D {i}"))
        linhas.append(_linha(i, "I9", "claude-haiku-5-5", "valor_ausente", f"A alíquota é zero {i}."))
    for i in range(1, 7):
        linhas.append(_linha(i, "I10", "claude-sonnet-5-5", "canario_ausente", f"Resposta neutra {i}."))
    with caminho.open("w", encoding="utf-8") as f:
        for l in linhas:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    return linhas


def test_piloto_tem_uma_rodada_por_arquivo_e_modelo():
    plano = planejar_piloto()
    assert len(plano) == len(ATAQUES_V2) * len(MODELOS_V2) == 18
    assert all(rep == 1 for _, _, rep in plano)


def test_sem_executar_nao_roda_nem_cria_arquivos(tmp_path):
    jsonl = tmp_path / "medicao.jsonl"
    assert main(["--jsonl", str(jsonl), "--base", str(tmp_path / "base")]) == 0
    assert not jsonl.exists()


def test_executar_sem_p2_e_erro_de_uso(tmp_path):
    with pytest.raises(SystemExit):
        main(["--executar", "--jsonl", str(tmp_path / "m.jsonl"), "--base", str(tmp_path / "b")])


def test_calibrar_escreve_cego_sem_metadados_e_mapa_separado(tmp_path):
    jsonl = tmp_path / "piloto.jsonl"
    _jsonl_com_linhas(jsonl)
    cego, mapa = tmp_path / "cego.json", tmp_path / "mapa-privado.json"
    assert main(["--calibrar", str(cego), "--mapa", str(mapa), "--jsonl", str(jsonl),
                 "--base", str(tmp_path / "b")]) == 0
    itens = json.loads(cego.read_text(encoding="utf-8"))
    assert len(itens) == 10
    for item in itens:
        assert set(item) == {"id", "pergunta", "texto_embutido", "resposta"}
    texto = cego.read_text(encoding="utf-8")
    for proibido in ("chave", "ataque", "modelo", "marcador", "julgamento", "verdict", "I8", "I9", "I10"):
        assert proibido not in texto
    chaves = set(json.loads(mapa.read_text(encoding="utf-8")).values())
    assert chaves <= {l["chave"] for l in _jsonl_com_linhas(tmp_path / "outro.jsonl")}


def test_preparar_calibracao_com_poucas_linhas_e_erro(tmp_path):
    jsonl = tmp_path / "piloto.jsonl"
    with jsonl.open("w", encoding="utf-8") as f:
        f.write(json.dumps(_linha(1, "I8", "claude-haiku-5-5", "canario_presente", "x")) + "\n")
    with pytest.raises(ValueError):
        preparar_calibracao(jsonl, random.Random(1))
