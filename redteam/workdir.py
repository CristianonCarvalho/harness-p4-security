"""Cópia de trabalho do P2: quem mexe aqui é o laboratório, nunca o original."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

MCP_CONFIG_NAME = "redteam-mcp.json"
_IGNORAR = shutil.ignore_patterns(".git", ".venv", "traces", "__pycache__", ".pytest_cache")


def prepare_workdir(p2_dir: Path, dest: Path) -> Path:
    """Copia o checkout do P2 e grava a config MCP só com o server taxlaw.

    O copytree levanta FileExistsError se o destino já existe: uma cópia nunca é reaproveitada.
    """
    cfg = json.loads((Path(p2_dir) / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["taxlaw"]
    shutil.copytree(p2_dir, dest, ignore=_IGNORAR)
    (Path(dest) / MCP_CONFIG_NAME).write_text(
        json.dumps({"mcpServers": {"taxlaw": cfg}}, indent=2), encoding="utf-8")
    return Path(dest)
