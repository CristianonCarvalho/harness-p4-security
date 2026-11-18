import random
from pathlib import Path

from redteam.esquema import CATALOGO_DIR
from redteam.guarda import substituir_marcadores
from redteam.http.requisicoes import carregar_ataque_http
from redteam.sintetico import novo


def test_h6_e_h7_carregam_com_quatro_requisicoes_e_marcadores():
    for i in ["H6", "H7"]:
        attack, reqs, esperado = carregar_ataque_http(Path(CATALOGO_DIR) / f"{i}.json")
        assert attack.id == i and len(reqs) == 4
        assert esperado == {"guarda": "bloqueou"}
        assert all("{CPF" in str(r["corpo"]) or "{CNPJ" in str(r["corpo"]) for r in reqs)


def test_todas_as_requisicoes_de_h6_e_h7_ficam_sem_marcador_depois_da_substituicao():
    cpf, cnpj = novo("cpf", random.Random(40)), novo("cnpj", random.Random(41))
    for i in ["H6", "H7"]:
        _, reqs, _ = carregar_ataque_http(Path(CATALOGO_DIR) / f"{i}.json")
        for r in reqs:
            substituir_marcadores(r, [cpf, cnpj])
