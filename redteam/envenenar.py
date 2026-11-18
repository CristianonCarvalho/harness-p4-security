"""Corpo envenenado: acrescenta um payload ao texto de um dispositivo.

Só mexe na cópia do P2 que o chamador passa em `workdir`. Nunca aponte para o P2 original.
"""

from __future__ import annotations

import json
from pathlib import Path

from redteam.integridade import corpus_sha256

ALVO_IDS = {"alvo": "LC214.art125", "alvo2": "EC132.art8.parunico"}
CAMINHO_CORPUS = Path("corpus") / "dispositivos.json"


def envenenar(workdir: Path, registros: list[dict], canario: str) -> str:
    workdir = Path(workdir)
    caminho = workdir / CAMINHO_CORPUS
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    por_id = {d["id"]: d for d in dados["dispositivos"]}
    for r in registros:
        alvo_id = ALVO_IDS.get(r["alvo"])
        if alvo_id is None:
            raise ValueError(f"alvo desconhecido: {r['alvo']!r}")
        dispositivo = por_id[alvo_id]
        texto = dispositivo.get("texto") or ""
        if not texto:
            raise ValueError(f"alvo sem texto: {alvo_id}")
        payload = r["payload"].replace("{CANARIO}", canario)
        if r["posicao"] == "inicio":
            dispositivo["texto"] = f"{payload} {texto}"
        elif r["posicao"] == "fim":
            dispositivo["texto"] = f"{texto} {payload}"
        else:
            raise ValueError(f"posicao desconhecida: {r['posicao']!r}")
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return corpus_sha256(workdir)
