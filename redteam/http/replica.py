"""Réplica local: sobe o `taxlaw.http` do P2 numa cópia, com token por variável de ambiente."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import httpx

TOKEN_ENV = "TAXLAW_HTTP_TOKEN"


class ReplicaNaoSobe(Exception):
    """A réplica não respondeu: a causa está no log, nunca no token."""


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def montar_comando(workdir: Path, porta: int) -> list[str]:
    return ["uv", "run", "--quiet", "--project", str(workdir), "python", "-m", "taxlaw.http",
            "--port", str(porta)]


def montar_ambiente(token: str) -> dict:
    return {**os.environ, TOKEN_ENV: token}


@contextmanager
def replica(workdir: Path, token: str, *, timeout_s: float = 90.0):
    porta = porta_livre()
    base = f"http://127.0.0.1:{porta}"
    with open(Path(workdir) / "replica.log", "w", encoding="utf-8") as log:
        proc = subprocess.Popen(montar_comando(workdir, porta), cwd=workdir,
                                env=montar_ambiente(token), stdout=log, stderr=subprocess.STDOUT)
        try:
            limite = time.monotonic() + timeout_s
            while True:
                if proc.poll() is not None:
                    raise ReplicaNaoSobe(f"o processo saiu com código {proc.returncode}; veja replica.log")
                try:
                    httpx.get(base + "/mcp", timeout=2.0)
                    break
                except httpx.TransportError:
                    if time.monotonic() > limite:
                        raise ReplicaNaoSobe("a réplica não respondeu no prazo; veja replica.log")
                    time.sleep(0.5)
            yield base
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
