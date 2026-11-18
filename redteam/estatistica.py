"""Taxas com intervalo de Wilson de 95%: seguro mesmo com poucas execuções e com 0 ou 100%."""

from __future__ import annotations

import math


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n < 0 or k < 0 or k > n:
        raise ValueError(f"k e n inválidos: k={k}, n={n}")
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    z2 = z * z
    centro = (p + z2 / (2 * n)) / (1 + z2 / n)
    meio = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return (max(0.0, centro - meio), min(1.0, centro + meio))


def taxa(k: int, n: int) -> str:
    if n == 0:
        return "0/0 (sem execuções)"
    a, b = wilson(k, n)
    return f"{k}/{n} = {round(100 * k / n)}% (IC 95%: {round(100 * a)}% a {round(100 * b)}%)"
