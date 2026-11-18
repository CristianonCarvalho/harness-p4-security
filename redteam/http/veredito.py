"""Veredito de uma requisição HTTP: compara o que o P2 respondeu com a expectativa escrita antes."""

from __future__ import annotations

import json
from dataclasses import dataclass

# Códigos que, quando esperados, significam "bloqueio": uma resposta 2xx nesse caso é furo.
BLOQUEIOS = {400, 401, 403, 404, 405, 406, 413, 421}


@dataclass(frozen=True)
class Resposta:
    status: int
    corpo: str


def _mensagem_erro(corpo: str):
    try:
        return json.loads(corpo)["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return None


def julgar(esperado: dict, observado: Resposta) -> str:
    checks = [observado.status in esperado.get("status", [])]
    if "erro_mcp" in esperado:
        checks.append(_mensagem_erro(observado.corpo) == esperado["erro_mcp"])
    if esperado.get("sem_stacktrace"):
        checks.append("Traceback" not in observado.corpo)
    if all(checks):
        return "defendido"
    if set(esperado.get("status", [])) & BLOQUEIOS and 200 <= observado.status < 300:
        return "furou"
    return "inesperado"
