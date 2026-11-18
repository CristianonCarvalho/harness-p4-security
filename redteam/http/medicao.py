"""Medição das requisições na réplica: três repetições, veredito por código, registro sem segredo."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from redteam.esquema import Attack
from redteam.http.cliente import enviar, redigir
from redteam.http.veredito import julgar

REPETICOES_PADRAO = 3


def exigir_previsao(attack: Attack) -> None:
    if not attack.previsao.get("motivo"):
        raise ValueError(f"{attack.id}: previsão vazia; escreva a sua antes de medir")


def rodar_ataque(attack: Attack, reqs: list[dict], esperado: dict, base_url: str, token: str, *,
                 cliente: httpx.Client, repeticoes: int = REPETICOES_PADRAO) -> list[dict]:
    exigir_previsao(attack)
    registros = []
    for req in reqs:
        for n in range(1, repeticoes + 1):
            observado = enviar(base_url, token, req, cliente=cliente)
            registros.append({
                "ataque": attack.id, "requisicao": req["nome"], "repeticao": n,
                "status": observado.status, "veredito": julgar(esperado, observado),
                "trecho": observado.corpo[:200],
            })
    return registros


def gravar(registros: list[dict], destino: Path, token: str) -> None:
    texto = json.dumps(registros, ensure_ascii=False, indent=2)
    Path(destino).write_text(redigir(texto, token), encoding="utf-8")
