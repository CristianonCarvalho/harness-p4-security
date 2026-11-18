import json

import pytest

from redteam.workdir import MCP_CONFIG_NAME, prepare_workdir


@pytest.fixture
def p2(tmp_path):
    raiz = tmp_path / "p2"
    (raiz / "corpus").mkdir(parents=True)
    (raiz / "corpus" / "dispositivos.json").write_text('{"dispositivos": []}', encoding="utf-8")
    (raiz / ".mcp.json").write_text(json.dumps({"mcpServers": {
        "taxlaw": {"type": "stdio", "command": "uv", "args": ["run"]},
        "eco": {"type": "stdio", "command": "uv", "args": ["run", "echo.py"]},
    }}), encoding="utf-8")
    (raiz / ".venv").mkdir()
    (raiz / ".venv" / "lixo.txt").write_text("x", encoding="utf-8")
    return raiz


def test_copia_ignora_venv_e_grava_so_o_taxlaw(p2, tmp_path):
    dest = prepare_workdir(p2, tmp_path / "wd")
    assert (dest / "corpus" / "dispositivos.json").exists()
    assert not (dest / ".venv").exists()
    cfg = json.loads((dest / MCP_CONFIG_NAME).read_text(encoding="utf-8"))
    assert list(cfg["mcpServers"]) == ["taxlaw"]


def test_destino_existente_e_recusado(p2, tmp_path):
    (tmp_path / "wd").mkdir()
    with pytest.raises(FileExistsError):
        prepare_workdir(p2, tmp_path / "wd")
