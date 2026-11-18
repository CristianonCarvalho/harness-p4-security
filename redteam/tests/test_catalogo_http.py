from pathlib import Path

from redteam.esquema import CATALOGO_DIR
from redteam.http.requisicoes import carregar_ataque_http

IDS = ["H1", "H2", "H3", "H4", "H5", "H8", "H9"]


def test_todos_os_ataques_http_carregam_e_tem_expectativa():
    for i in IDS:
        attack, reqs, esperado = carregar_ataque_http(Path(CATALOGO_DIR) / f"{i}.json")
        assert attack.id == i and attack.superficie == "http"
        assert reqs and esperado


def test_nenhum_ataque_http_carrega_token_no_arquivo():
    for i in IDS:
        texto = (Path(CATALOGO_DIR) / f"{i}.json").read_text(encoding="utf-8")
        assert "Bearer" not in texto
