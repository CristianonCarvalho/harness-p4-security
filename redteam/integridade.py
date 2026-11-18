"""Confere que o P2 ficou como estava: hash do corpus, commit e git status."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


class P2Mudou(Exception):
    """O P2 mudou durante a rodada: ela é inválida."""


def corpus_sha256(base: Path) -> str:
    return hashlib.sha256((Path(base) / "corpus" / "dispositivos.json").read_bytes()).hexdigest()


def _git(p2_dir: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(p2_dir), *args],
                          capture_output=True, text=True, check=True).stdout


def snapshot(p2_dir: Path) -> dict:
    return {
        "corpus_sha256": corpus_sha256(p2_dir),
        "git_head": _git(p2_dir, "rev-parse", "HEAD").strip(),
        "git_status": _git(p2_dir, "status", "--porcelain"),
    }


def conferir(antes: dict, depois: dict) -> None:
    diferentes = [k for k in antes if antes[k] != depois.get(k)]
    if diferentes:
        raise P2Mudou(f"o P2 mudou durante a rodada: {', '.join(diferentes)}")
