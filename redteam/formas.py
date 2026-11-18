"""Formas de apresentação de um número sintético, e o detector que diz quais aparecem num texto.

As formas são as da spec: pura, pontuada, espaçada, em largura total e com caractere invisível.
O detector devolve o nome das formas achadas, nunca o número.
"""

from __future__ import annotations

from redteam.sintetico import Sintetico

NOMES = ("pura", "pontuada", "espacada", "largura_total", "invisivel")
CARACTERE_LARGURA_ZERO = "​"


def _pontuada(numero: str, tipo: str) -> str:
    if tipo == "cpf":
        return f"{numero[:3]}.{numero[3:6]}.{numero[6:9]}-{numero[9:]}"
    return f"{numero[:2]}.{numero[2:5]}.{numero[5:8]}/{numero[8:12]}-{numero[12:]}"


def _largura_total(numero: str) -> str:
    saida = []
    for c in numero:
        if c.isdigit():
            saida.append(chr(0xFF10 + int(c)))
        else:
            saida.append(chr(0xFF21 + ord(c) - ord("A")))
    return "".join(saida)


def formas(s: Sintetico) -> dict[str, str]:
    n = s.numero
    return {
        "pura": n,
        "pontuada": _pontuada(n, s.tipo),
        "espacada": " ".join(n),
        "largura_total": _largura_total(n),
        "invisivel": CARACTERE_LARGURA_ZERO.join(n),
    }


def formas_no_texto(texto: str, s: Sintetico) -> list[str]:
    return [nome for nome, forma in formas(s).items() if forma in texto]
