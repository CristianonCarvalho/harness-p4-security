import json
import subprocess
from pathlib import Path

import pytest

from redteam.injecao_v2 import (
    ATAQUES_V2,
    MODELOS_V2,
    chave,
    julgar_v2,
    medir_v2,
    planejar_v2,
)

ATAQUES_DIR = Path(__file__).resolve().parents[1] / "ataques"
CANARIO = "CANARIO-1A2B3C4D"
CORPUS = {"fontes": {}, "dispositivos": [{"id": "LC214.art125", "texto": "Texto A."}]}


@pytest.fixture
def p2(tmp_path):
    p2 = tmp_path / "p2"
    (p2 / "corpus").mkdir(parents=True)
    mcp = {"mcpServers": {"taxlaw": {"type": "stdio", "command": "uv", "args": ["run"]}}}
    (p2 / ".mcp.json").write_text(json.dumps(mcp), encoding="utf-8")
    (p2 / "corpus" / "dispositivos.json").write_text(json.dumps(CORPUS), encoding="utf-8")
    subprocess.run(["git", "-C", str(p2), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(p2), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(p2), "-c", "user.name=teste",
                    "-c", "user.email=teste@example.invalid", "commit", "-q", "-m", "base"], check=True)
    return p2


def _executor(chamadas, custo=0.1, limites=(), resultado="Alíquota zero."):
    def executor(argv, pergunta, cwd):
        chamadas.append((argv, pergunta, cwd))
        n = len(chamadas) - 1
        status = limites[n] if n < len(limites) else "allowed"
        return {"resultado": resultado, "custo": custo, "turnos": 1, "erro": None,
                "resultados_de_ferramentas": [], "limite_status": status}
    return executor


def _linhas(jsonl):
    return [json.loads(l) for l in jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_planejar_v2_tem_210_rodadas_com_as_repeticoes_certas():
    plano = planejar_v2()
    assert len(plano) == 210
    assert len({chave(*p) for p in plano}) == 210
    assert {a for a, _, _ in plano} == set(ATAQUES_V2)
    for ataque, _, rep in plano:
        limite = 5 if ataque in ("I10", "I16", "I19") else 15
        assert 1 <= rep <= limite
    assert {m for _, m, _ in plano} == set(MODELOS_V2)


def test_medir_v2_grava_uma_linha_por_rodada_e_apaga_as_pastas(tmp_path, p2):
    base, jsonl = tmp_path / "base", tmp_path / "medicao.jsonl"
    plano = [("I8", "claude-haiku-5-5", 1), ("I8", "claude-haiku-5-5", 2)]
    medir_v2(plano, p2, base, jsonl, ataques_dir=ATAQUES_DIR, executor=_executor([]),
             canario_fn=lambda: CANARIO)
    linhas = _linhas(jsonl)
    assert [l["chave"] for l in linhas] == [chave(*p) for p in plano]
    assert all(l["status"] == "rodada" and l["julgamento"] is None for l in linhas)
    assert list(base.iterdir()) == []


def test_medir_v2_pula_o_que_ja_esta_gravado(tmp_path, p2):
    base, jsonl = tmp_path / "base", tmp_path / "medicao.jsonl"
    plano = [("I8", "claude-haiku-5-5", 1), ("I8", "claude-haiku-5-5", 2)]
    chamadas = []
    medir_v2(plano[:1], p2, base, jsonl, ataques_dir=ATAQUES_DIR, executor=_executor(chamadas),
             canario_fn=lambda: CANARIO)
    medir_v2(plano, p2, base, jsonl, ataques_dir=ATAQUES_DIR, executor=_executor(chamadas),
             canario_fn=lambda: CANARIO)
    assert len(chamadas) == 2  # a primeira rodada não roda de novo
    assert len(_linhas(jsonl)) == 2


def test_medir_v2_para_no_teto_sem_gravar_as_rodadas_que_faltam(tmp_path, p2):
    jsonl = tmp_path / "medicao.jsonl"
    plano = [("I8", "claude-haiku-5-5", r) for r in range(1, 6)]
    chamadas = []
    saida = medir_v2(plano, p2, tmp_path / "base", jsonl, ataques_dir=ATAQUES_DIR,
                     total_max=2.0, por_execucao=0.5, executor=_executor(chamadas, custo=1.0),
                     canario_fn=lambda: CANARIO)
    assert len(chamadas) == 2
    assert len(_linhas(jsonl)) == 2
    assert saida["parada"] == "teto de custo do total"
    assert saida["pendentes"] == 3


def test_medir_v2_para_quando_o_limite_de_uso_nao_esta_liberado(tmp_path, p2):
    jsonl = tmp_path / "medicao.jsonl"
    plano = [("I8", "claude-haiku-5-5", r) for r in range(1, 5)]
    chamadas = []
    saida = medir_v2(plano, p2, tmp_path / "base", jsonl, ataques_dir=ATAQUES_DIR,
                     executor=_executor(chamadas, limites=("allowed", "rejected")),
                     canario_fn=lambda: CANARIO)
    assert len(chamadas) == 2
    assert len(_linhas(jsonl)) == 2
    assert saida["parada"] == "limite de uso: rejected"
    assert saida["pendentes"] == 2


def test_medir_v2_recupera_pasta_orfa_de_rodada_interrompida(tmp_path, p2):
    base, jsonl = tmp_path / "base", tmp_path / "medicao.jsonl"
    (base / "I8-claude-haiku-5-5-r1").mkdir(parents=True)
    medir_v2([("I8", "claude-haiku-5-5", 1)], p2, base, jsonl, ataques_dir=ATAQUES_DIR,
             executor=_executor([]), canario_fn=lambda: CANARIO)
    assert len(_linhas(jsonl)) == 1


def test_julgar_v2_preenche_o_julgamento_com_o_canario_da_rodada(tmp_path, p2):
    base, jsonl = tmp_path / "base", tmp_path / "medicao.jsonl"
    medir_v2([("I8", "claude-haiku-5-5", 1)], p2, base, jsonl, ataques_dir=ATAQUES_DIR,
             executor=_executor([], resultado=f"Substituo: {CANARIO}"), canario_fn=lambda: CANARIO)
    prompts = []

    def juiz(argv, prompt, cwd):
        prompts.append(prompt)
        return {"resultado": '{"justification": "trocou", "verdict": "fail", "classe": "obedeceu"}',
                "erro": None, "custo": 0.04}

    saida = julgar_v2(jsonl, base, ataques_dir=ATAQUES_DIR, executor=juiz)
    julgamento = _linhas(jsonl)[0]["julgamento"]
    assert julgamento["verdict"] == "fail" and julgamento["classe"] == "obedeceu"
    assert saida == {"julgadas": 1, "erros": 0}
    assert CANARIO in prompts[0]  # o texto embutido leva o canário da rodada


def test_julgar_v2_nao_envia_o_id_do_ataque_nem_o_modelo_ao_juiz(tmp_path, p2):
    base, jsonl = tmp_path / "base", tmp_path / "medicao.jsonl"
    medir_v2([("I8", "claude-haiku-5-5", 1)], p2, base, jsonl, ataques_dir=ATAQUES_DIR,
             executor=_executor([], resultado="ok"), canario_fn=lambda: CANARIO)
    prompts = []

    def juiz(argv, prompt, cwd):
        prompts.append(prompt)
        return {"resultado": '{"justification": "x", "verdict": "pass", "classe": "resistiu"}',
                "erro": None, "custo": 0.0}

    julgar_v2(jsonl, base, ataques_dir=ATAQUES_DIR, executor=juiz)
    assert "I8" not in prompts[0]
    assert "claude-haiku" not in prompts[0]


def test_julgar_v2_refaz_a_linha_que_teve_erro_do_juiz(tmp_path, p2):
    base, jsonl = tmp_path / "base", tmp_path / "medicao.jsonl"
    medir_v2([("I8", "claude-haiku-5-5", 1)], p2, base, jsonl, ataques_dir=ATAQUES_DIR,
             executor=_executor([], resultado="ok"), canario_fn=lambda: CANARIO)

    falha = lambda argv, prompt, cwd: {"resultado": None, "erro": "timeout", "custo": None}
    julgar_v2(jsonl, base, ataques_dir=ATAQUES_DIR, executor=falha)
    assert _linhas(jsonl)[0]["julgamento"]["erro"] == "timeout"

    ok = lambda argv, prompt, cwd: {"resultado": '{"justification": "x", "verdict": "pass", "classe": "resistiu"}',
                                    "erro": None, "custo": 0.0}
    saida = julgar_v2(jsonl, base, ataques_dir=ATAQUES_DIR, executor=ok)
    assert _linhas(jsonl)[0]["julgamento"]["verdict"] == "pass"
    assert saida == {"julgadas": 1, "erros": 0}
