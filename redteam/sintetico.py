"""Números de contribuinte sintéticos, com dígito verificador válido, gerados em tempo de execução.

O número fica só em memória: o objeto que o guarda não o mostra no repr nem no str.
"""

from __future__ import annotations

import hashlib
import random

from redteam.varredura import CNPJ_P1, CNPJ_P2, CPF_P1, CPF_P2, _dv

ALFABETO_CNPJ = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALFABETO_CPF = "0123456789"


def _base_valida(rng: random.Random, tamanho: int, alfabeto: str) -> list[str]:
    """Sorteia uma base que não seja um único dígito repetido (esse número não é um CPF válido)."""
    while True:
        base = [rng.choice(alfabeto) for _ in range(tamanho)]
        if len(set(base)) > 1:
            return base


def gerar_cpf(rng: random.Random) -> str:
    base = _base_valida(rng, 9, ALFABETO_CPF)
    v = [int(c) for c in base]
    d1 = _dv(v, CPF_P1)
    return "".join(base) + f"{d1}{_dv(v + [d1], CPF_P2)}"


def gerar_cnpj(rng: random.Random, *, alfanumerico: bool = False) -> str:
    alfabeto = ALFABETO_CNPJ if alfanumerico else ALFABETO_CNPJ[:10]
    base = _base_valida(rng, 12, alfabeto)
    v = [ord(c) - 48 for c in base]
    d1 = _dv(v, CNPJ_P1)
    return "".join(base) + f"{d1}{_dv(v + [d1], CNPJ_P2)}"


def fingerprint(numero: str) -> str:
    return hashlib.sha256(numero.encode("utf-8")).hexdigest()[:12]


class Sintetico:
    """Um número sintético. O número é acessível, mas não aparece em repr nem em str."""

    def __init__(self, tipo: str, numero: str):
        self._tipo = tipo
        self._numero = numero

    @property
    def tipo(self) -> str:
        return self._tipo

    @property
    def numero(self) -> str:
        return self._numero

    @property
    def fingerprint(self) -> str:
        return fingerprint(self._numero)

    def __repr__(self) -> str:
        return f"Sintetico(tipo={self._tipo!r}, fingerprint={self.fingerprint!r})"

    def __str__(self) -> str:
        return repr(self)


def novo(tipo: str, rng: random.Random | None = None, *, alfanumerico: bool = False) -> Sintetico:
    """Gera um número novo. Sem `rng`, usa uma fonte criptográfica de aleatoriedade."""
    rng = rng or random.SystemRandom()
    if tipo == "cpf":
        return Sintetico("cpf", gerar_cpf(rng))
    if tipo == "cnpj":
        return Sintetico("cnpj", gerar_cnpj(rng, alfanumerico=alfanumerico))
    raise ValueError(f"tipo desconhecido: {tipo!r}")
