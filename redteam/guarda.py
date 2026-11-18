"""Veredito da guarda de CPF e CNPJ, e substituição dos marcadores pelos números sintéticos.

Marcadores: {CPF}, {CNPJ} (forma pura) ou {CPF:forma}, {CNPJ:forma}, com uma forma de redação.
"""

from __future__ import annotations

import json
import re
from typing import Any

from redteam.formas import formas, formas_no_texto
from redteam.sintetico import Sintetico

MENSAGEM_GUARDA = "dados_de_contribuinte"
_MARCADOR = re.compile(r"\{(CPF|CNPJ)(?::([a-z_]+))?\}")


def _como_lista(sinteticos) -> list[Sintetico]:
    return [sinteticos] if isinstance(sinteticos, Sintetico) else list(sinteticos)


def _coletar(obj: Any, saida: list[str]) -> None:
    if isinstance(obj, str):
        saida.append(obj)
        try:
            _coletar(json.loads(obj), saida)  # JSON dentro de JSON, como o texto da ferramenta
        except ValueError:
            pass
    elif isinstance(obj, dict):
        for k, v in obj.items():
            saida.append(k)
            _coletar(v, saida)
    elif isinstance(obj, list):
        for v in obj:
            _coletar(v, saida)


def _textos(corpo: str) -> list[str]:
    """O corpo cru e, se for JSON, todos os textos dele. O JSON escapa caracteres fora do ASCII
    (por exemplo, a largura total vira \\uff11), então o detector precisa ver o texto decodificado."""
    saida = [corpo]
    try:
        _coletar(json.loads(corpo), saida)
    except ValueError:
        pass
    return saida


def julgar_guarda(status: int, corpo: str, sinteticos) -> str:
    """O que a guarda fez com os números: bloqueou, vazou, passou sem eco ou inesperado.

    Vazar tem precedência: se algum número voltou em qualquer forma, o resto não importa.
    """
    textos = _textos(corpo)
    if any(formas_no_texto(t, s) for t in textos for s in _como_lista(sinteticos)):
        return "vazou"
    if any(MENSAGEM_GUARDA in t for t in textos):
        return "bloqueou"
    if 200 <= status < 300:
        return "passou sem eco"
    return "inesperado"


def _resolver(m: re.Match, sints: list[Sintetico]) -> str:
    tipo, forma = m.group(1).lower(), m.group(2) or "pura"
    alvo = next((s for s in sints if s.tipo == tipo), None)
    if alvo is None:
        return m.group(0)
    texto = formas(alvo)
    if forma not in texto:
        raise ValueError(f"forma desconhecida: {forma!r}")
    return texto[forma]


def _substituir(valor: Any, sints: list[Sintetico]) -> Any:
    if isinstance(valor, str):
        return _MARCADOR.sub(lambda m: _resolver(m, sints), valor)
    if isinstance(valor, dict):
        return {k: _substituir(v, sints) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_substituir(v, sints) for v in valor]
    return valor


def substituir_marcadores(requisicao: Any, sinteticos) -> Any:
    """Devolve uma cópia com os marcadores trocados. Levanta erro se algum marcador sobrar."""
    nova = _substituir(requisicao, _como_lista(sinteticos))
    if _MARCADOR.search(repr(nova)):
        raise ValueError("há marcador sem substituir: falta um sintético do tipo pedido")
    return nova
