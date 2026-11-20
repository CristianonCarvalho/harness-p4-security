import os
import socket
from pathlib import Path

import pytest

from redteam.http.replica import TOKEN_ENV, montar_ambiente, montar_comando, porta_livre

TOKEN = "s" * 40


def test_porta_livre_pode_ser_amarrada():
    porta = porta_livre()
    assert 1024 <= porta <= 65535
    with socket.socket() as s:
        s.bind(("127.0.0.1", porta))


def test_comando_nao_carrega_o_token():
    comando = montar_comando(Path("copia-de-teste"), 8123)
    assert TOKEN not in " ".join(comando)
    assert "--port" in comando and "8123" in comando


def test_ambiente_leva_o_token_e_preserva_o_resto():
    ambiente = montar_ambiente(TOKEN)
    assert ambiente[TOKEN_ENV] == TOKEN
    assert ambiente.get("PATH") == os.environ.get("PATH")


@pytest.mark.skipif(os.environ.get("REDTEAM_INTEGRACAO") != "1",
                    reason="integração: sobe o P2 real; use REDTEAM_INTEGRACAO=1")
def test_replica_sobe_responde_401_sem_token_e_nao_grava_o_token(tmp_path):
    import httpx

    from redteam.http.replica import replica
    from redteam.workdir import prepare_workdir

    dest = tmp_path / "copia"
    prepare_workdir(Path(os.environ["REDTEAM_P2_DIR"]), dest)
    with replica(dest, TOKEN) as base:
        assert httpx.post(base + "/mcp", json={}).status_code == 401
    assert TOKEN not in (dest / "replica.log").read_text(encoding="utf-8")
