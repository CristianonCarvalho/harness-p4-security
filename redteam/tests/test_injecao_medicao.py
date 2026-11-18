import json
import re
import subprocess
from pathlib import Path

import pytest

from redteam.injecao_medicao import gravar, medir
from redteam.integridade import P2Mudou
from redteam.varredura import scan_text

ATAQUES_DIR = Path(__file__).resolve().parents[1] / "ataques"
CORPUS = {"fontes": {}, "dispositivos": [{"id": "LC214.art125", "texto": "Texto A."}]}
CANARIO_RE = re.compile(r"CANARIO-[0-9A-F]{8}")


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


def _executor(chamadas, custo=0.1, limites=(), canarios=None, resultado="Alíquota zero."):
    """Executor falso: registra cada chamada e, se pedido, o canário gravado na cópia do corpus."""
    def executor(argv, pergunta, cwd):
        if canarios is not None:
            copia = cwd.parent / "copia"
            achados = sorted(set(CANARIO_RE.findall((copia / "corpus" / "dispositivos.json").read_text(encoding="utf-8"))))
            canarios.append(achados[0])
        n = len(chamadas)
        chamadas.append(argv)
        status = limites[n] if n < len(limites) else "allowed"
        return {"resultado": resultado, "custo": custo, "turnos": 1, "erro": None,
                "resultados_de_ferramentas": [], "limite_status": status}
    return executor


def test_cada_rodada_tem_canario_novo(tmp_path, p2):
    canarios = []
    medir(ATAQUES_DIR, p2, tmp_path / "base", ataques=("I1",), modelos=("claude-haiku-5-5",),
          repeticoes=3, por_execucao=0.5,
          executor=_executor([], canarios=canarios))
    assert len(canarios) == 3
    assert len(set(canarios)) == 3


def test_para_quando_o_custo_passaria_do_teto_total(tmp_path, p2):
    chamadas = []
    saida = medir(ATAQUES_DIR, p2, tmp_path / "base", ataques=("I1",), modelos=("claude-haiku-5-5",),
                  repeticoes=5, total_max=2.0, por_execucao=0.5,
                  executor=_executor(chamadas, custo=1.0))
    rodadas = [r for r in saida["registros"] if r["status"] == "rodada"]
    nao = [r for r in saida["registros"] if r["status"] == "nao_rodada"]
    assert len(rodadas) == 2
    assert len(chamadas) == 2
    assert len(nao) == 3
    assert all(r["motivo"] == "teto de custo do total" for r in nao)
    assert saida["gasto_usd"] == 2.0
    assert saida["parada"] == "teto de custo do total"


def test_para_quando_o_limite_de_uso_deixa_de_estar_liberado(tmp_path, p2):
    chamadas = []
    saida = medir(ATAQUES_DIR, p2, tmp_path / "base", ataques=("I1",), modelos=("claude-haiku-5-5",),
                  repeticoes=4, total_max=10.0, por_execucao=0.5,
                  executor=_executor(chamadas, limites=("allowed", "rejected")))
    assert len(chamadas) == 2
    assert saida["registros"][1]["limite_status"] == "rejected"
    nao = [r for r in saida["registros"] if r["status"] == "nao_rodada"]
    assert len(nao) == 2
    assert all(r["motivo"] == "limite de uso: rejected" for r in nao)
    assert saida["parada"] == "limite de uso: rejected"


def test_rodada_que_nao_rodou_nao_vira_veredito(tmp_path, p2):
    saida = medir(ATAQUES_DIR, p2, tmp_path / "base", ataques=("I1",), modelos=("claude-haiku-5-5",),
                  repeticoes=2, total_max=0.5, por_execucao=0.5,
                  executor=_executor([], custo=0.1))
    nao = [r for r in saida["registros"] if r["status"] == "nao_rodada"]
    assert nao
    assert all(r["veredito"] is None for r in nao)


def test_pasta_de_cada_rodada_e_apagada_depois_de_registrar(tmp_path, p2):
    base = tmp_path / "base"
    medir(ATAQUES_DIR, p2, base, ataques=("I1",), modelos=("claude-haiku-5-5",),
          repeticoes=2, por_execucao=0.5, executor=_executor([]))
    assert list(base.iterdir()) == []


def test_registro_leva_o_trecho_limitado_e_nenhum_cpf(tmp_path, p2):
    saida = medir(ATAQUES_DIR, p2, tmp_path / "base", ataques=("I1",), modelos=("claude-haiku-5-5",),
                  repeticoes=1, por_execucao=0.5,
                  executor=_executor([], resultado="Alíquota zero. " * 100))
    assert all(len(r["resposta_trecho"]) <= 500 for r in saida["registros"])
    assert scan_text(json.dumps(saida, ensure_ascii=False)) == []


def test_p2_que_muda_durante_a_medicao_aborta_tudo(tmp_path, p2):
    def executor(argv, pergunta, cwd):
        (p2 / "corpus" / "dispositivos.json").write_text("{}", encoding="utf-8")
        return {"resultado": "ok", "custo": 0.0, "turnos": 1, "erro": None,
                "resultados_de_ferramentas": [], "limite_status": "allowed"}

    with pytest.raises(P2Mudou):
        medir(ATAQUES_DIR, p2, tmp_path / "base", ataques=("I1",), modelos=("claude-haiku-5-5",),
              repeticoes=2, por_execucao=0.5, executor=executor)


def test_saida_traz_o_p2_antes_e_depois_iguais_e_o_gasto(tmp_path, p2):
    saida = medir(ATAQUES_DIR, p2, tmp_path / "base", ataques=("I1",), modelos=("claude-haiku-5-5",),
                  repeticoes=2, por_execucao=0.5, executor=_executor([], custo=0.25))
    assert saida["p2_antes"] == saida["p2_depois"]
    assert saida["gasto_usd"] == 0.5
    assert saida["parada"] is None


def test_gravar_escreve_o_json_com_os_registros(tmp_path, p2):
    saida = medir(ATAQUES_DIR, p2, tmp_path / "base", ataques=("I1",), modelos=("claude-haiku-5-5",),
                  repeticoes=2, por_execucao=0.5, executor=_executor([]))
    destino = gravar(saida, tmp_path / "docs" / "medicao.json")
    assert json.loads(destino.read_text(encoding="utf-8"))["registros"] == saida["registros"]
