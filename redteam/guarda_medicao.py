"""Medição da guarda de CPF e CNPJ na réplica: controle positivo, três repetições, registro sem números.

O registro guarda o status, o veredito, o nome das formas que voltaram e o fingerprint de cada número.
Nenhum número e nenhum corpo de resposta vão para o arquivo.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path

import httpx

from redteam.esquema import Attack, CATALOGO_DIR
from redteam.formas import formas_no_texto
from redteam.guarda import MENSAGEM_GUARDA, _textos, julgar_guarda, substituir_marcadores
from redteam.http.cliente import enviar
from redteam.http.medicao import exigir_previsao
from redteam.http.replica import replica
from redteam.http.requisicoes import carregar_ataque_http
from redteam.sintetico import novo
from redteam.workdir import prepare_workdir

REPETICOES = 3
IDS = ["H6", "H7"]
SAIDA = Path("docs/redteam/medicao-guarda.json")
CONTROLE = {
    "nome": "controle_sem_numero", "metodo": "POST", "caminho": "/mcp", "autenticacao": "correta",
    "cabecalhos": {},
    "corpo": {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "buscar_dispositivos",
                         "arguments": {"consulta": "alíquota zero cesta básica"}}},
    "alvos": ["replica"],
}


class ControleFalhou(Exception):
    """A consulta sem número não devolveu resultado: a rodada não vale."""


def controle_ok(status: int, corpo: str) -> bool:
    textos = _textos(corpo)
    return status == 200 and not any(MENSAGEM_GUARDA in t for t in textos) and any(t == "encontrado" for t in textos)


def formas_achadas(corpo: str, sinteticos) -> list[str]:
    achadas: list[str] = []
    for texto in _textos(corpo):
        for s in sinteticos:
            for nome in formas_no_texto(texto, s):
                marca = f"{s.tipo}:{nome}"
                if marca not in achadas:
                    achadas.append(marca)
    return achadas


def rodar_ataque_guarda(attack: Attack, reqs: list[dict], base_url: str, token: str, *,
                        cliente: httpx.Client, repeticoes: int = REPETICOES) -> list[dict]:
    exigir_previsao(attack)
    registros = []
    for req in reqs:
        for n in range(1, repeticoes + 1):
            sinteticos = [novo("cpf"), novo("cnpj")]
            requisicao = substituir_marcadores(req, sinteticos)
            resposta = enviar(base_url, token, requisicao, cliente=cliente, limite=None)
            registros.append({
                "ataque": attack.id, "requisicao": req["nome"], "repeticao": n,
                "status": resposta.status,
                "veredito": julgar_guarda(resposta.status, resposta.corpo, sinteticos),
                "formas_achadas": formas_achadas(resposta.corpo, sinteticos),
                "fingerprints": {s.tipo: s.fingerprint for s in sinteticos},
            })
    return registros


def main() -> int:
    p2 = Path(os.environ["REDTEAM_P2_DIR"])
    token = secrets.token_urlsafe(32)
    catalogo = []
    for i in IDS:
        attack, reqs, _ = carregar_ataque_http(Path(CATALOGO_DIR) / f"{i}.json")
        catalogo.append((attack, reqs))
    registros = []
    with tempfile.TemporaryDirectory() as tmp:
        copia = prepare_workdir(p2, Path(tmp) / "p2")
        with replica(copia, token) as base, httpx.Client() as cliente:
            controle = enviar(base, token, CONTROLE, cliente=cliente, limite=None)
            if not controle_ok(controle.status, controle.corpo):
                raise ControleFalhou(f"a consulta sem número devolveu {controle.status}; rodada inválida")
            for attack, reqs in catalogo:
                registros += rodar_ataque_guarda(attack, reqs, base, token, cliente=cliente)
    SAIDA.write_text(json.dumps({"controle": {"ok": True}, "registros": registros},
                                ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(registros)} registros em {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
