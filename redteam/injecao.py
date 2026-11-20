"""Validação dos ataques de injeção: registros do corpus envenenado, pergunta e oráculo do canário.

Só palavra-sinal. Não há URL nem pedido de ação: a medição mede se o modelo repete o canário.
"""

from __future__ import annotations

import json
from pathlib import Path

from redteam.esquema import Attack, load_attack

ALVOS = {"alvo", "alvo2"}
POSICOES = {"inicio", "fim"}
ORACULOS = {"canario", "valor"}
MAX_REGISTROS = 2


def validar_entrada_injecao(entrada: dict) -> tuple[list[dict], str]:
    registros = entrada.get("registros")
    if not isinstance(registros, list) or not 1 <= len(registros) <= MAX_REGISTROS:
        raise ValueError("entrada.registros deve ter de 1 a 2 itens")
    for r in registros:
        if r.get("alvo") not in ALVOS:
            raise ValueError(f"alvo inválido: {r.get('alvo')!r}")
        if r.get("posicao") not in POSICOES:
            raise ValueError(f"posicao inválida: {r.get('posicao')!r}")
        if not isinstance(r.get("payload"), str) or not r["payload"].strip():
            raise ValueError("payload vazio")
    pergunta = entrada.get("pergunta")
    if not isinstance(pergunta, str) or not pergunta.strip():
        raise ValueError("pergunta vazia")
    if "{CPF" in pergunta or "{CNPJ" in pergunta:
        raise ValueError("a pergunta não leva número de contribuinte nesta medição")
    return registros, pergunta


def carregar_criterio_injecao(caminho: Path) -> dict:
    """O critério do ataque: o oráculo e, para o oráculo `valor`, o valor que conta como obediência."""
    bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
    criterio = bruto["criterio"]
    oraculo = criterio.get("oraculo")
    if oraculo not in ORACULOS:
        raise ValueError(f"oráculo inválido: {oraculo!r}")
    valor = criterio.get("valor")
    if oraculo == "valor" and (not isinstance(valor, str) or not valor.strip()):
        raise ValueError("oráculo valor exige criterio.valor como texto não vazio")
    return {"oraculo": oraculo, "valor": valor}


def carregar_ataque_injecao(caminho: Path) -> tuple[Attack, list[dict], str, str]:
    caminho = Path(caminho)
    attack = load_attack(caminho)
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    registros, pergunta = validar_entrada_injecao(bruto["entrada"])
    oraculo = carregar_criterio_injecao(caminho)["oraculo"]
    return attack, registros, pergunta, oraculo
