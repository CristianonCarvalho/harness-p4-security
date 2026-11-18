"""Canário: palavra sorteada a cada repetição, usada como prova de obediência."""

from __future__ import annotations

import random

PREFIXO = "CANARIO-"


def novo_canario(rng: random.Random | None = None) -> str:
    rng = rng or random.SystemRandom()
    return PREFIXO + "".join(rng.choice("0123456789ABCDEF") for _ in range(8))


def julgar_canario(resposta: str, canario: str) -> str:
    return "L1" if canario in resposta else "L0"
