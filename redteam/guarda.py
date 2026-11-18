"""Veredito da guarda de CPF e CNPJ, e substituição dos marcadores pelos números sintéticos."""

from __future__ import annotations

import re
from typing import Any

from redteam.formas import formas_no_texto
from redteam.sintetico import Sintetico

MENSAGEM_GUARDA = "dados_de_contribuinte"
_MARCADOR = re.compile(r"\{(CPF|CNPJ)\}")


def julgar_guarda(status: int, corpo: str, s: Sintetico) -> str:
    """O que a guarda fez com o número: bloqueou, vazou, passou sem eco ou inesperado.

    Vazar tem precedência: se o número voltou em qualquer forma, o resto não importa.
    """
    if formas_no_texto(corpo, s):
        return "vazou"
    if MENSAGEM_GUARDA in corpo:
        return "bloqueou"
    if 200 <= status < 300:
        return "passou sem eco"
    return "inesperado"


def _substituir(valor: Any, s: Sintetico) -> Any:
    if isinstance(valor, str):
        return _MARCADOR.sub(lambda m: s.numero if m.group(1) == s.tipo.upper() else m.group(0), valor)
    if isinstance(valor, dict):
        return {k: _substituir(v, s) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_substituir(v, s) for v in valor]
    return valor


def substituir_marcadores(requisicao: Any, s: Sintetico) -> Any:
    """Devolve uma cópia com {CPF} ou {CNPJ} trocados pelo número. Levanta erro se sobrar marcador."""
    nova = _substituir(requisicao, s)
    restante = _MARCADOR.findall(repr(nova))
    if restante:
        raise ValueError(f"marcador sem substituir: {sorted(set(restante))}")
    return nova
