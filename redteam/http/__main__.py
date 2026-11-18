"""Executa a medição na réplica: `REDTEAM_P2_DIR=<caminho do P2> python -m redteam.http`."""

from __future__ import annotations

import os
import secrets
import tempfile
from pathlib import Path

import httpx

from redteam.esquema import CATALOGO_DIR
from redteam.http.medicao import gravar, rodar_ataque
from redteam.http.replica import replica
from redteam.http.requisicoes import carregar_ataque_http
from redteam.workdir import prepare_workdir

IDS = ["H1", "H2", "H3", "H4", "H5", "H8", "H9"]
SAIDA = Path("docs/redteam/medicao-replica.json")


def main() -> int:
    p2 = Path(os.environ["REDTEAM_P2_DIR"])
    token = secrets.token_urlsafe(32)
    registros = []
    with tempfile.TemporaryDirectory() as tmp:
        copia = prepare_workdir(p2, Path(tmp) / "p2")
        with replica(copia, token) as base, httpx.Client() as cliente:
            for i in IDS:
                attack, reqs, esperado = carregar_ataque_http(Path(CATALOGO_DIR) / f"{i}.json")
                registros += rodar_ataque(attack, reqs, esperado, base, token, cliente=cliente)
    gravar(registros, SAIDA, token)
    print(f"{len(registros)} registros em {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
