"""Esquema comum do catálogo de ataques: um arquivo JSON por ataque.

Valida só os campos comuns. Cada laboratório valida o próprio bloco de entrada e de critério.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

CATALOGO_DIR = Path(__file__).parent / "ataques"
SUPERFICIES = {"injecao": "I", "http": "H"}
CAMPOS = ("id", "superficie", "nome", "nucleo", "rotulos", "previsao")
ID_RE = re.compile(r"[IH][1-9][0-9]?")


@dataclass(frozen=True)
class Attack:
    id: str
    superficie: str
    nome: str
    nucleo: bool
    rotulos: dict
    previsao: dict


def _erro(caminho: Path, msg: str):
    raise ValueError(f"{caminho.name}: {msg}")


def load_attack(caminho: Path) -> Attack:
    caminho = Path(caminho)
    d = json.loads(caminho.read_text(encoding="utf-8"))
    for campo in CAMPOS:
        if campo not in d:
            _erro(caminho, f"sem o campo {campo!r}")
    if not isinstance(d["id"], str) or not ID_RE.fullmatch(d["id"]):
        _erro(caminho, f"id inválido: {d['id']!r}")
    if d["superficie"] not in SUPERFICIES:
        _erro(caminho, f"superficie inválida: {d['superficie']!r}")
    if d["id"][0] != SUPERFICIES[d["superficie"]]:
        _erro(caminho, "o prefixo do id não combina com a superfície")
    if caminho.stem != d["id"]:
        _erro(caminho, "o nome do arquivo deve ser o id do ataque")
    if not isinstance(d["nucleo"], bool):
        _erro(caminho, "nucleo deve ser true ou false")
    if not isinstance(d["rotulos"], dict) or not isinstance(d["previsao"], dict):
        _erro(caminho, "rotulos e previsao devem ser objetos")
    return Attack(**{c: d[c] for c in CAMPOS})


def load_catalog(diretorio: Path = CATALOGO_DIR) -> list[Attack]:
    ataques = [load_attack(p) for p in sorted(Path(diretorio).glob("*.json"))]
    return sorted(ataques, key=lambda a: (a.superficie != "injecao", int(a.id[1:])))
