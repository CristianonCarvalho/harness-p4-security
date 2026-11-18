"""Validação do bloco `entrada` e `criterio` de um ataque HTTP, além dos campos comuns."""

from __future__ import annotations

import json
from pathlib import Path

from redteam.esquema import Attack, load_attack

METODOS = {"GET", "POST", "DELETE"}
ALVOS = {"replica", "vps"}
AUTENTICACOES = {"correta", "ausente", "errada"}
CHAVES_ESPERADO = {"status", "erro_mcp", "sem_stacktrace"}


def validar_requisicoes(entrada: dict) -> list[dict]:
    reqs = entrada.get("requisicoes")
    if not isinstance(reqs, list) or not reqs:
        raise ValueError("entrada.requisicoes não pode ser vazia")
    for r in reqs:
        if not isinstance(r.get("nome"), str) or not r["nome"]:
            raise ValueError("requisição sem nome")
        if r.get("metodo") not in METODOS:
            raise ValueError(f"método inválido: {r.get('metodo')!r}")
        caminho = r.get("caminho")
        if not isinstance(caminho, str) or not caminho.startswith("/") or len(caminho) > 200:
            raise ValueError(f"caminho inválido: {caminho!r}")
        if r.get("autenticacao", "correta") not in AUTENTICACOES:
            raise ValueError(f"autenticacao inválida: {r.get('autenticacao')!r}")
        cabecalhos = r.get("cabecalhos", {})
        if not isinstance(cabecalhos, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in cabecalhos.items()):
            raise ValueError("cabecalhos deve ser um objeto de texto para texto")
        if "authorization" in {k.lower() for k in cabecalhos}:
            raise ValueError("use o campo autenticacao, não o cabeçalho Authorization")
        alvos = r.get("alvos")
        if not isinstance(alvos, list) or not alvos or not set(alvos) <= ALVOS:
            raise ValueError(f"alvos inválidos: {alvos!r}")
    return reqs


def validar_criterio(criterio: dict) -> dict:
    esperado = criterio.get("esperado")
    if not isinstance(esperado, dict) or not esperado or not set(esperado) <= CHAVES_ESPERADO:
        raise ValueError(f"criterio.esperado inválido: {esperado!r}")
    return esperado


def carregar_ataque_http(caminho: Path) -> tuple[Attack, list[dict], dict]:
    caminho = Path(caminho)
    attack = load_attack(caminho)
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    return attack, validar_requisicoes(bruto["entrada"]), validar_criterio(bruto["criterio"])
