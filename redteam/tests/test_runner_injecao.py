import json
import sys

import json
from pathlib import Path

import pytest

from redteam.runner_injecao import (
    FERRAMENTAS_P2,
    INSTRUCAO_SISTEMA,
    executar,
    gravar_mcp_config,
    interpretar_saida,
    montar_argv,
    montar_mcp_config,
)

MCP = "/caminho/copia/redteam-mcp.json"


def _argv() -> list[str]:
    return montar_argv("claude-haiku-5-5", 0.5, MCP)


def _valor(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def _stream(eventos: list[dict]) -> str:
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in eventos)


def test_argv_nao_libera_ferramentas_de_rede():
    texto = " ".join(_argv())
    assert "WebFetch" not in texto
    assert "WebSearch" not in texto


def test_argv_libera_so_as_duas_ferramentas_do_p2():
    assert _valor(_argv(), "--allowedTools").split(",") == list(FERRAMENTAS_P2)


def test_argv_usa_so_o_mcp_do_laboratorio():
    argv = _argv()
    assert _valor(argv, "--mcp-config") == MCP
    assert "--strict-mcp-config" in argv


def test_argv_tem_modelo_e_teto_de_custo():
    argv = _argv()
    assert _valor(argv, "--model") == "claude-haiku-5-5"
    assert _valor(argv, "--max-budget-usd") == "0.5"


def test_argv_pede_stream_json_com_verbose():
    argv = _argv()
    assert _valor(argv, "--output-format") == "stream-json"
    assert "--verbose" in argv


def test_argv_nega_permissoes_nao_liberadas_e_nao_guarda_sessao():
    argv = _argv()
    assert _valor(argv, "--permission-prompts") == "none"
    assert "--no-session-persistence" in argv


def test_argv_leva_a_instrucao_de_sistema_fixa_que_manda_consultar_o_corpus():
    assert _valor(_argv(), "--append-system-prompt") == INSTRUCAO_SISTEMA
    assert "corpus" in INSTRUCAO_SISTEMA.lower()


def test_argv_nao_usa_bare_porque_bare_nao_le_a_assinatura():
    assert "--bare" not in _argv()


def test_stream_com_resultado_e_resultado_de_ferramenta():
    eventos = [
        {"type": "system", "subtype": "init"},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": '{"trecho": "Nota"}'}]}},
        {"type": "result", "subtype": "success", "is_error": False,
         "result": "Resposta final", "total_cost_usd": 0.02, "num_turns": 3},
    ]
    assert interpretar_saida(_stream(eventos)) == {
        "resultado": "Resposta final",
        "custo": 0.02,
        "turnos": 3,
        "erro": None,
        "resultados_de_ferramentas": ['{"trecho": "Nota"}'],
        "limite_status": None,
    }


def test_resultado_de_ferramenta_em_blocos_de_texto_vira_uma_string():
    eventos = [
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1",
             "content": [{"type": "text", "text": "parte A"}, {"type": "text", "text": "parte B"}]}]}},
        {"type": "result", "is_error": False, "result": "ok", "total_cost_usd": 0.0, "num_turns": 1},
    ]
    assert interpretar_saida(_stream(eventos))["resultados_de_ferramentas"] == ["parte A\nparte B"]


def test_saida_que_nao_e_json_e_erro():
    r = interpretar_saida("isto não é json\n")
    assert r["erro"] == "saida_invalida"
    assert r["resultado"] is None


def test_sem_linha_de_resultado_e_erro():
    r = interpretar_saida(_stream([{"type": "system", "subtype": "init"}]))
    assert r["erro"] == "sem_resultado"
    assert r["resultado"] is None


def test_linha_de_resultado_sem_campo_result_e_erro():
    r = interpretar_saida(_stream([{"type": "result", "is_error": False, "total_cost_usd": 0.0, "num_turns": 1}]))
    assert r["erro"] == "sem_resultado"


def test_is_error_fica_registrado_e_o_resultado_continua_visivel():
    eventos = [{"type": "result", "subtype": "error_max_budget_usd", "is_error": True,
                "result": "", "total_cost_usd": 0.5, "num_turns": 1}]
    r = interpretar_saida(_stream(eventos))
    assert r["erro"] == "is_error"
    assert r["resultado"] == ""


def test_executar_entrega_a_pergunta_pela_entrada_e_le_a_saida(tmp_path):
    script = tmp_path / "falso.py"
    script.write_text(
        "import json, sys\n"
        "pergunta = sys.stdin.read()\n"
        "print(json.dumps({'type': 'result', 'is_error': False, 'result': 'eco: ' + pergunta,"
        " 'total_cost_usd': 0.0, 'num_turns': 1}))\n",
        encoding="utf-8",
    )
    r = executar([sys.executable, str(script)], "Qual é a alíquota?", tmp_path)
    assert r["resultado"] == "eco: Qual é a alíquota?"
    assert r["erro"] is None


def test_codigo_de_saida_diferente_de_zero_e_erro(tmp_path):
    r = executar([sys.executable, "-c", "import sys; sys.exit(3)"], "x", tmp_path)
    assert r["erro"] == "codigo_3"
    assert r["resultado"] is None


def test_tempo_esgotado_e_erro(tmp_path):
    r = executar([sys.executable, "-c", "import time; time.sleep(5)"], "x", tmp_path, timeout=0.5)
    assert r["erro"] == "timeout"
    assert r["resultado"] is None


def test_mcp_config_sobe_so_o_taxlaw_pelo_projeto_da_copia(tmp_path):
    copia = tmp_path / "copia"
    cfg = montar_mcp_config(copia)
    assert set(cfg["mcpServers"]) == {"taxlaw"}
    server = cfg["mcpServers"]["taxlaw"]
    assert server["command"] == "uv"
    assert server["args"][server["args"].index("--project") + 1] == str(copia)
    assert server["args"][-3:] == ["python", "-m", "taxlaw.server"]


def test_mcp_config_nao_depende_do_diretorio_atual(tmp_path):
    args = montar_mcp_config(tmp_path / "copia")["mcpServers"]["taxlaw"]["args"]
    assert Path(args[args.index("--project") + 1]).is_absolute()
    assert "." not in args


def test_mcp_config_recusa_copia_com_caminho_relativo():
    with pytest.raises(ValueError, match="absoluto"):
        montar_mcp_config(Path("copia-relativa"))


def test_gravar_mcp_config_escreve_o_mesmo_conteudo_que_o_montador(tmp_path):
    copia = tmp_path / "copia"
    destino = gravar_mcp_config(copia, tmp_path / "neutro" / "redteam-mcp.json")
    assert destino.exists()
    assert json.loads(destino.read_text(encoding="utf-8")) == montar_mcp_config(copia)


def test_executar_grava_a_saida_bruta_quando_pedido(tmp_path):
    script = tmp_path / "ecoa.py"
    script.write_text(
        "import json\n"
        "print(json.dumps({'type': 'result', 'is_error': False, 'result': 'ok',"
        " 'total_cost_usd': 0.0, 'num_turns': 1}))\n",
        encoding="utf-8",
    )
    bruto = tmp_path / "bruto.jsonl"
    r = executar([sys.executable, str(script)], "x", tmp_path, bruto=bruto)
    assert r["resultado"] == "ok"
    assert '"result": "ok"' in bruto.read_text(encoding="utf-8")


def _evento_de_limite(status: str) -> dict:
    return {"type": "rate_limit_event", "rate_limit_info": {"status": status, "rateLimitType": "five_hour"}}


def test_status_do_limite_de_uso_e_capturado():
    eventos = [
        _evento_de_limite("allowed"),
        {"type": "result", "is_error": False, "result": "ok", "total_cost_usd": 0.0, "num_turns": 1},
    ]
    assert interpretar_saida(_stream(eventos))["limite_status"] == "allowed"


def test_ultimo_status_do_limite_vence():
    eventos = [
        _evento_de_limite("allowed"),
        _evento_de_limite("rejected"),
        {"type": "result", "is_error": True, "result": "", "total_cost_usd": 0.0, "num_turns": 1},
    ]
    assert interpretar_saida(_stream(eventos))["limite_status"] == "rejected"


def test_sem_evento_de_limite_o_status_e_none():
    eventos = [{"type": "result", "is_error": False, "result": "ok", "total_cost_usd": 0.0, "num_turns": 1}]
    assert interpretar_saida(_stream(eventos))["limite_status"] is None
